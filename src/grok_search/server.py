import sys
from pathlib import Path
import os
import secrets
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

# 支持直接运行：添加 src 目录到 Python 路径
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import fastmcp
from fastmcp import FastMCP, Context
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.responses import JSONResponse

# 尝试使用绝对导入（支持 mcp run）
try:
    from grok_search.providers.grok import GrokSearchProvider
    from grok_search.utils import format_search_results
    from grok_search.logger import log_info
    from grok_search.config import config
except ImportError:
    # 降级到相对导入（pip install -e . 后）
    from .providers.grok import GrokSearchProvider
    from .utils import format_search_results
    from .logger import log_info
    from .config import config

import asyncio

mcp = FastMCP("grok-search")

_HIGH_TRUST_DOMAINS = {
    "modelcontextprotocol.io",
    "openai.com",
    "anthropic.com",
    "python.org",
    "docs.python.org",
    "developer.mozilla.org",
    "github.com",
    "gitlab.com",
    "pypi.org",
    "npmjs.com",
    "ietf.org",
    "w3.org",
    "arxiv.org",
    "wikipedia.org",
}

_MEDIUM_TRUST_DOMAINS = {
    "stackoverflow.com",
    "reddit.com",
    "microsoft.com",
    "aws.amazon.com",
    "cloudflare.com",
}

_LOW_TRUST_DOMAINS = {
    "blogspot.com",
    "wordpress.com",
    "medium.com",
    "cnblogs.com",
    "csdn.net",
    "juejin.cn",
}

_NOISE_HINTS = (
    "utm_",
    "affiliate",
    "coupon",
    "discount",
    "sponsored",
    "adclick",
    "tracking",
)

_FRESHNESS_HINTS = (
    "latest",
    "recent",
    "updated",
    "release",
    "发布",
    "更新",
    "最新",
)

_TIME_INTENT_CN_KEYWORDS = (
    "当前",
    "现在",
    "今天",
    "明天",
    "昨天",
    "本周",
    "上周",
    "下周",
    "本月",
    "上月",
    "下月",
    "今年",
    "去年",
    "明年",
    "最新",
    "最近",
    "近期",
    "实时",
    "即时",
)

_TIME_INTENT_EN_KEYWORDS = (
    "current",
    "now",
    "today",
    "tomorrow",
    "yesterday",
    "this week",
    "last week",
    "next week",
    "this month",
    "last month",
    "next month",
    "this year",
    "last year",
    "next year",
    "latest",
    "recent",
    "recently",
    "real-time",
    "realtime",
    "up-to-date",
)

_HISTORY_CN_KEYWORDS = ("历史", "回顾", "沿革", "演进", "里程碑", "时间线")
_HISTORY_EN_KEYWORDS = ("history", "historical", "timeline", "retrospective", "milestone")
_TIME_GUARD_MARKERS = ("时间基准", "time baseline", "current time context - authoritative")
_STATUS_CHECK_CN_KEYWORDS = (
    "是不是",
    "是否",
    "还在",
    "还活着",
    "死了",
    "去世",
    "死亡",
    "遇刺",
    "下台",
    "辞职",
    "当选",
    "被罢免",
)
_STATUS_CHECK_EN_KEYWORDS = (
    "is",
    "still",
    "alive",
    "dead",
    "died",
    "death",
    "assassinated",
    "resigned",
    "stepped down",
    "elected",
    "impeached",
)


def _extract_json_candidate(result_text: str) -> str:
    if not result_text:
        return ""

    text = result_text.strip()
    if text.startswith("[") and text.endswith("]"):
        return text
    if text.startswith("{") and text.endswith("}"):
        return text

    # 兼容数组型结果被额外文本包裹
    left = text.find("[")
    right = text.rfind("]")
    if left != -1 and right != -1 and right > left:
        return text[left : right + 1]

    # 兼容对象型结果被额外文本包裹
    left = text.find("{")
    right = text.rfind("}")
    if left != -1 and right != -1 and right > left:
        return text[left : right + 1]

    return ""


def _parse_search_items(result_text: str) -> list[dict]:
    candidate = _extract_json_candidate(result_text)
    if not candidate:
        return []

    try:
        parsed = json.loads(candidate)
    except Exception:
        return []

    if isinstance(parsed, dict):
        maybe_results = parsed.get("results")
        if isinstance(maybe_results, list):
            parsed = maybe_results
        else:
            return []

    if not isinstance(parsed, list):
        return []

    normalized_items = []
    seen = set()
    for item in parsed:
        if not isinstance(item, dict):
            continue

        raw_url = str(item.get("url", "")).strip()
        url = _pick_first_url(raw_url)
        if not url or url in seen:
            continue

        title = str(item.get("title", "")).strip()
        description = (
            str(item.get("description", "")).strip()
            or str(item.get("summary", "")).strip()
            or str(item.get("snippet", "")).strip()
            or str(item.get("content", "")).strip()
        )

        normalized_items.append(
            {
                "title": title or url,
                "url": url,
                "description": description,
            }
        )
        seen.add(url)

    return normalized_items


def _normalize_domain(url: str) -> str:
    try:
        domain = (urlparse(url).netloc or "").lower().strip()
    except Exception:
        return ""

    if not domain:
        return ""

    domain = domain.split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _tokenize(text: str) -> list[str]:
    if not text:
        return []

    parts = re.findall(r"[a-z0-9][a-z0-9._-]{1,}|[\u4e00-\u9fff]{2,}", text.lower())
    tokens = []
    seen = set()
    for token in parts:
        token = token.strip("._-")
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _score_source_quality(url: str) -> float:
    domain = _normalize_domain(url)
    if not domain:
        return 0.1

    if domain in _HIGH_TRUST_DOMAINS:
        return 0.95

    if domain in _MEDIUM_TRUST_DOMAINS:
        return 0.75

    if domain in _LOW_TRUST_DOMAINS:
        return 0.42

    if domain.endswith((".gov", ".edu", ".ac.cn")):
        return 0.92

    if domain.startswith(("docs.", "developer.", "api.")):
        return 0.85

    if any(domain.endswith(f".{root}") for root in _HIGH_TRUST_DOMAINS):
        return 0.82

    if "wikipedia.org" in domain:
        return 0.8

    return 0.6


def _score_relevance(query: str, item: dict) -> float:
    query_text = (query or "").strip().lower()
    title = str(item.get("title", "")).lower()
    description = str(item.get("description", "")).lower()
    url = str(item.get("url", "")).lower()
    body = "\n".join((title, description, url))

    if not query_text:
        return 0.5

    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return 0.45 if query_text in body else 0.2

    body_hits = sum(1 for token in query_tokens if token in body)
    title_hits = sum(1 for token in query_tokens if token in title)

    token_ratio = body_hits / len(query_tokens)
    title_ratio = title_hits / len(query_tokens)

    phrase_boost = 0.0
    if query_text in title:
        phrase_boost = 0.35
    elif query_text in description:
        phrase_boost = 0.22
    elif query_text in body:
        phrase_boost = 0.1

    score = 0.55 * token_ratio + 0.3 * title_ratio + phrase_boost

    # 兜底：至少命中一个核心 token 时，避免因为多语言描述导致分数被压得过低。
    if body_hits >= 1:
        score = max(score, 0.35)
    if title_hits >= 1 and body_hits >= 1:
        score = max(score, 0.5)

    if body_hits == 0:
        score *= 0.2
    return max(0.0, min(1.0, score))


def _score_freshness_hint(item: dict) -> float:
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    current_year = datetime.now().year

    score = 0.0
    if str(current_year) in text:
        score += 0.7
    elif str(current_year - 1) in text:
        score += 0.35

    if any(keyword in text for keyword in _FRESHNESS_HINTS):
        score += 0.3

    return max(0.0, min(1.0, score))


def _contains_noise(item: dict) -> bool:
    blob = f"{item.get('title', '')} {item.get('description', '')} {item.get('url', '')}".lower()
    return any(hint in blob for hint in _NOISE_HINTS)


def _ranking_weights(mode: str) -> tuple[float, float, float]:
    if mode == "fast":
        return 0.72, 0.22, 0.06
    if mode == "strict":
        return 0.52, 0.43, 0.05
    return 0.6, 0.35, 0.05


def _effective_min_score(base_threshold: float, mode: str) -> float:
    if mode == "fast":
        return max(0.0, base_threshold - 0.05)
    if mode == "strict":
        return min(1.0, base_threshold + 0.06)
    return base_threshold


def _effective_low_quality_quota(base_quota: int, mode: str) -> int:
    if mode == "strict":
        return 0
    if mode == "fast":
        return base_quota + 1
    return base_quota


def _rank_search_results(query: str, result_text: str, max_results: int) -> tuple[str, list[str], list[str], dict]:
    items = _parse_search_items(result_text)
    if not items:
        return result_text, [], [], {"applied": False, "reason": "unparseable"}

    mode = config.search_ranking_mode
    weight_rel, weight_src, weight_fresh = _ranking_weights(mode)
    min_score = _effective_min_score(config.search_min_score, mode)
    low_quality_quota = _effective_low_quality_quota(config.search_low_quality_quota, mode)

    scored_items = []
    for item in items:
        relevance = _score_relevance(query, item)
        source = _score_source_quality(item["url"])
        freshness = _score_freshness_hint(item)
        noise = _contains_noise(item)

        final_score = relevance * weight_rel + source * weight_src + freshness * weight_fresh
        if noise:
            final_score -= 0.12
        final_score = max(0.0, min(1.0, final_score))

        low_quality = (relevance < 0.35) or (source < 0.5) or noise
        scored_items.append(
            {
                **item,
                "_relevance_score": relevance,
                "_source_score": source,
                "_freshness_hint": freshness,
                "_final_score": final_score,
                "_low_quality": low_quality,
            }
        )

    scored_items.sort(key=lambda x: x["_final_score"], reverse=True)

    selected_items = []
    low_quality_used = 0
    for item in scored_items:
        if item["_final_score"] < min_score:
            continue

        if item["_low_quality"]:
            if low_quality_used >= low_quality_quota:
                continue
            low_quality_used += 1

        selected_items.append(item)
        if max_results > 0 and len(selected_items) >= max_results:
            break

    # 若过滤过严导致为空，保留最相关且不过低可信的首条，避免完全不可用。
    if not selected_items and scored_items:
        top = scored_items[0]
        if top["_relevance_score"] >= 0.45 and top["_source_score"] >= 0.45:
            selected_items = [top]

    ranked_results = []
    high_quality_urls = []
    all_urls = []
    for item in selected_items:
        output_item = {
            "title": item["title"],
            "url": item["url"],
            "description": item["description"],
        }

        if config.search_debug_score_enabled:
            output_item["quality_score"] = round(item["_final_score"], 4)
            output_item["relevance_score"] = round(item["_relevance_score"], 4)
            output_item["source_score"] = round(item["_source_score"], 4)
            output_item["source_tier"] = (
                "high"
                if item["_source_score"] >= 0.75
                else "normal"
                if item["_source_score"] >= 0.55
                else "low"
            )

        ranked_results.append(output_item)
        all_urls.append(item["url"])
        if item["_source_score"] >= 0.75 and item["_relevance_score"] >= 0.45:
            high_quality_urls.append(item["url"])

    result_json = json.dumps(ranked_results, ensure_ascii=False, indent=2)
    meta = {
        "applied": True,
        "mode": mode,
        "min_score": round(min_score, 4),
        "input_count": len(items),
        "output_count": len(ranked_results),
        "high_quality_count": len(high_quality_urls),
    }
    return result_json, all_urls, high_quality_urls, meta


def _read_request_header(ctx: Context | None, header_name: str) -> str | None:
    """安全读取 HTTP MCP 请求头；stdio 下返回 None。"""
    if ctx is None or ctx.request_context is None:
        return None
    request = getattr(ctx.request_context, "request", None)
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    if headers is None:
        return None
    value = headers.get(header_name)
    if not value:
        return None
    value = value.strip()
    return value or None


def _resolve_runtime_api_credentials(ctx: Context | None) -> tuple[str, str]:
    """优先级：请求头 > 环境变量 > 抛错。"""
    api_url = (
        _read_request_header(ctx, "X-Grok-Api-Url")
        or os.getenv("GROK_API_URL")
    )
    api_key = (
        _read_request_header(ctx, "X-Grok-Api-Key")
        or os.getenv("GROK_API_KEY")
    )

    if not api_url:
        raise ValueError("Grok API URL 未配置（可通过 GROK_API_URL 或 X-Grok-Api-Url 提供）")
    if not api_key:
        raise ValueError("Grok API Key 未配置（可通过 GROK_API_KEY 或 X-Grok-Api-Key 提供）")
    return api_url, api_key


def _resolve_runtime_model(ctx: Context | None) -> tuple[str, str | None, bool]:
    """
    模型优先级：请求头 > 环境变量 > 配置文件/默认值。
    仅允许三档模型；非法输入自动回退到默认档。
    """
    requested_model = (
        _read_request_header(ctx, "X-Grok-Model")
        or _read_request_header(ctx, "X-Grok-Model-Tier")
        or os.getenv("GROK_MODEL")
    )

    if requested_model:
        resolved_model, fallback_used = config.resolve_model(requested_model)
        return resolved_model, requested_model, fallback_used

    return config.grok_model, None, False


def _extract_urls_from_text(text: str) -> list[str]:
    if not text:
        return []
    raw_urls = re.findall(r"https?://[^\s\"'<>]+", text)
    urls = []
    seen = set()
    for item in raw_urls:
        clean = item.rstrip(".,);]")
        if clean and clean not in seen:
            seen.add(clean)
            urls.append(clean)
    return urls


def _extract_urls_from_search_result(result_text: str) -> list[str]:
    if not result_text:
        return []

    urls: list[str] = []

    # 尝试把输出当作 JSON 数组解析（包含纯 JSON 返回场景）
    parsed = None
    try:
        parsed = json.loads(result_text)
    except Exception:
        parsed = None

    # 部分模型会在 JSON 前后加文本，尝试裁剪出首个数组
    if parsed is None:
        left = result_text.find("[")
        right = result_text.rfind("]")
        if left != -1 and right != -1 and right > left:
            maybe_json = result_text[left : right + 1]
            try:
                parsed = json.loads(maybe_json)
            except Exception:
                parsed = None

    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                url = item.get("url")
                if isinstance(url, str) and url.strip():
                    urls.append(url.strip())

    # JSON 提取不到时，降级为正则提取
    if not urls:
        urls = _extract_urls_from_text(result_text)

    # 去重保序
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


def _strip_think_blocks(text: str) -> str:
    """移除模型回传中的 <think>...</think> 思考内容，保留最终可用输出。"""
    if not text:
        return text
    stripped = re.sub(r"(?is)<think>.*?</think>", "", text)
    # 清理可能残留的多余空白行，避免污染 JSON 起始位置
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()
    return stripped


def _pick_first_url(raw_value: str) -> str:
    if not raw_value:
        return ""

    value = raw_value.strip()
    if not value:
        return ""

    urls = _extract_urls_from_text(value)
    if urls:
        return urls[0]

    # 兼容无 scheme 的常见输入（如 example.com/path 或 www.example.com）
    if " " not in value and "." in value and not value.startswith(("/", "#")):
        candidate = value
        if value.startswith("www."):
            candidate = f"https://{value}"
        elif not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
            candidate = f"https://{value}"

        if re.match(r"^https?://", candidate):
            return candidate

    return ""


async def _get_cached_search_urls(
    ctx: Context | None,
    state_key: str = "last_search_urls",
) -> list[str]:
    if ctx is None:
        return []
    try:
        urls = await ctx.get_state(state_key)
    except Exception:
        return []

    if not isinstance(urls, list):
        return []

    cleaned_urls = []
    seen = set()
    for item in urls:
        if isinstance(item, str):
            url = _pick_first_url(item)
            if url and url not in seen:
                seen.add(url)
                cleaned_urls.append(url)
    return cleaned_urls


def _pick_url_by_index(urls: list[str], result_index: int) -> tuple[str, int]:
    if not urls:
        return "", 0
    safe_index = max(result_index, 1) - 1
    safe_index = min(safe_index, len(urls) - 1)
    return urls[safe_index], safe_index + 1


def _contains_time_intent(query: str) -> bool:
    if not query:
        return False
    query_lower = query.lower()
    if any(keyword in query for keyword in _TIME_INTENT_CN_KEYWORDS):
        return True
    return any(keyword in query_lower for keyword in _TIME_INTENT_EN_KEYWORDS)


def _contains_history_intent(query: str) -> bool:
    if not query:
        return False
    query_lower = query.lower()
    if any(keyword in query for keyword in _HISTORY_CN_KEYWORDS):
        return True
    return any(keyword in query_lower for keyword in _HISTORY_EN_KEYWORDS)


def _contains_status_check_intent(query: str) -> bool:
    if not query:
        return False
    query_lower = query.lower()
    if any(keyword in query for keyword in _STATUS_CHECK_CN_KEYWORDS):
        return True
    return any(keyword in query_lower for keyword in _STATUS_CHECK_EN_KEYWORDS)


def _extract_year_tokens(query: str) -> list[int]:
    if not query:
        return []
    years = {int(item) for item in re.findall(r"(?:19|20|21)\d{2}", query)}
    return sorted(years)


def _format_utc_offset(offset: timedelta) -> str:
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _resolve_query_guard_now(tz_spec: str) -> tuple[datetime, str]:
    fallback_tz = timezone(timedelta(hours=8))
    fallback_label = "UTC+08:00"

    spec = (tz_spec or "").strip()
    if spec:
        utc_match = re.match(r"^UTC\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$", spec, re.IGNORECASE)
        if utc_match:
            sign = 1 if utc_match.group(1) == "+" else -1
            hours = int(utc_match.group(2))
            minutes = int(utc_match.group(3) or "0")
            if hours <= 23 and minutes <= 59:
                delta = timedelta(hours=hours, minutes=minutes) * sign
                return datetime.now(timezone(delta)), _format_utc_offset(delta)
        try:
            tz = ZoneInfo(spec)
            now = datetime.now(tz)
            offset = now.utcoffset() or timedelta(0)
            return now, _format_utc_offset(offset)
        except Exception:
            pass

    return datetime.now(fallback_tz), fallback_label


def _looks_like_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _build_query_time_guard_clause(query: str, timezone_label: str, current_date: str, history_intent: bool) -> str:
    if _looks_like_chinese(query):
        if history_intent:
            return (
                f"（时间基准：{timezone_label}，当前日期：{current_date}；"
                f"若涉及相对时间，请以该时间基准为准）"
            )
        return (
            f"（时间基准：{timezone_label}，当前日期：{current_date}；"
            f"优先检索近30天内信息，若日期冲突以该时间基准为准）"
        )

    if history_intent:
        return (
            f"(Time baseline: {timezone_label}; current date: {current_date}; "
            f"for relative time expressions, use this baseline.)"
        )
    return (
        f"(Time baseline: {timezone_label}; current date: {current_date}; "
        f"prioritize sources from the last 30 days; if date signals conflict, use this baseline.)"
    )


def _has_time_guard_marker(query: str) -> bool:
    query_lower = (query or "").lower()
    return any(marker in query_lower for marker in _TIME_GUARD_MARKERS)


def _remove_stale_year_tokens(query: str, stale_years: list[int]) -> str:
    stripped = query
    for year in stale_years:
        stripped = re.sub(rf"(?<!\d){year}(?!\d)\s*年?", " ", stripped)
    stripped = re.sub(r"\s{2,}", " ", stripped).strip()
    return stripped


def _normalize_query_for_time_intent(query: str) -> tuple[str, dict]:
    normalized_query = (query or "").strip()
    mode = config.search_query_time_guard_mode
    append_style = config.search_query_time_guard_append_style
    enabled = config.search_query_time_guard_enabled

    meta = {
        "enabled": enabled,
        "mode": mode,
        "append_style": append_style,
        "applied": False,
        "action": "none",
        "time_intent": False,
        "status_intent": False,
        "history_intent": False,
        "suspected_stale_year": False,
        "stale_years": [],
    }

    if not normalized_query or not enabled:
        return normalized_query, meta

    time_intent = _contains_time_intent(normalized_query)
    status_intent = _contains_status_check_intent(normalized_query)
    history_intent = _contains_history_intent(normalized_query)
    years = _extract_year_tokens(normalized_query)
    now, timezone_label = _resolve_query_guard_now(config.search_timezone)
    current_date = now.strftime("%Y-%m-%d")
    stale_years = [year for year in years if year <= now.year - 2]
    stale_year_guard_hit = bool(stale_years and not history_intent and (time_intent or status_intent))
    suspected_stale_year = stale_year_guard_hit

    meta.update(
        {
            "time_intent": time_intent,
            "status_intent": status_intent,
            "history_intent": history_intent,
            "suspected_stale_year": suspected_stale_year,
            "stale_years": stale_years,
            "timezone": timezone_label,
            "current_date": current_date,
        }
    )

    should_apply_guard = time_intent or stale_year_guard_hit
    if not should_apply_guard:
        return normalized_query, meta

    if mode == "audit":
        meta["action"] = "audit_only"
        return normalized_query, meta

    guarded_query = normalized_query
    if mode == "strict" and suspected_stale_year:
        removed_year_query = _remove_stale_year_tokens(guarded_query, stale_years)
        if removed_year_query:
            guarded_query = removed_year_query
            meta["action"] = "strict_remove_year"

    if _has_time_guard_marker(guarded_query):
        if meta["action"] == "none":
            meta["action"] = "already_guarded"
        return guarded_query, meta

    guard_clause = _build_query_time_guard_clause(
        guarded_query,
        timezone_label,
        current_date,
        history_intent,
    )
    if not guard_clause:
        return guarded_query, meta

    if append_style == "prefix":
        effective_query = f"{guard_clause} {guarded_query}".strip()
    else:
        effective_query = f"{guarded_query} {guard_clause}".strip()

    if effective_query != normalized_query:
        meta["applied"] = True
        if meta["action"] == "none":
            meta["action"] = "append_time_guard"
    return effective_query, meta

@mcp.tool(
    name="web_search",
    description="""
    Performs a third-party web search based on the given query and returns the results
    as a JSON string.

    The `query` should be a clear, self-contained natural-language search query.
    For compatibility, aliases such as `q`, `input`, `prompt`, `question`,
    `keyword`, `keywords`, and `search_query` are also accepted.
    When helpful, include constraints such as topic, time range, language, or domain.
    For time-sensitive intents (latest/today/current), server may append timezone-aware constraints automatically.

    The `platform` should be the platforms which you should focus on searching, such as "Twitter", "GitHub", "Reddit", etc.

    The `min_results` and `max_results` should be the minimum and maximum number of results to return.

    Returns
    -------
    str
        A JSON-encoded string representing a list of search results. Each result
        includes at least:
        - `url`: the link to the result
        - `title`: a short title
        - `summary`: a brief description or snippet of the page content.
    """
)
async def web_search(
    query: str = "",
    platform: str = "",
    min_results: int = 3,
    max_results: int = 10,
    q: str = "",
    input: str = "",
    prompt: str = "",
    question: str = "",
    keyword: str = "",
    keywords: str = "",
    search_query: str = "",
    ctx: Context = None
) -> str:
    # 兼容部分客户端对搜索词使用的非标准字段名，避免直接触发参数校验错误。
    query_candidates = [query, q, input, prompt, question, keyword, keywords, search_query]
    final_query = next(
        (item.strip() for item in query_candidates if isinstance(item, str) and item.strip()),
        "",
    )

    if not final_query:
        return (
            "参数缺失：未提供搜索词。请至少传入 `query`，"
            "或使用兼容字段 `q`/`input`/`prompt`/`question`/`keyword`/`keywords`/`search_query`。"
        )

    effective_query, query_guard_meta = _normalize_query_for_time_intent(final_query)
    if query_guard_meta.get("applied"):
        await log_info(
            ctx,
            f"query_time_guard 已应用: {final_query} => {effective_query}",
            config.debug_enabled,
        )
    elif query_guard_meta.get("action") == "audit_only":
        await log_info(
            ctx,
            "query_time_guard 审计模式命中：仅记录不改写 query",
            config.debug_enabled,
        )
    if config.debug_enabled:
        await log_info(
            ctx,
            f"query_time_guard_meta: {json.dumps(query_guard_meta, ensure_ascii=False)}",
            config.debug_enabled,
        )

    try:
        api_url, api_key = _resolve_runtime_api_credentials(ctx)
        model, requested_model, fallback_used = _resolve_runtime_model(ctx)
    except ValueError as e:
        error_msg = str(e)
        if ctx:
            await ctx.report_progress(error_msg)
        return f"配置错误: {error_msg}"

    grok_provider = GrokSearchProvider(api_url, api_key, model)

    if requested_model:
        if fallback_used:
            await log_info(
                ctx,
                f"模型请求 {requested_model!r} 不在白名单，自动回退到 {model}",
                config.debug_enabled,
            )
        else:
            await log_info(
                ctx,
                f"使用请求模型: {model}",
                config.debug_enabled,
            )

    await log_info(ctx, f"Begin Search: {final_query}", config.debug_enabled)
    raw_results = await grok_provider.search(effective_query, platform, min_results, max_results, ctx)
    if config.search_strip_think_enabled:
        results = _strip_think_blocks(raw_results)
        if results != raw_results:
            await log_info(ctx, "web_search 输出已移除 <think> 块", config.debug_enabled)
    else:
        results = raw_results

    ranked_urls: list[str] = []
    high_quality_urls: list[str] = []

    # 基于“问题匹配度 + 信源质量”做轻量重排，避免为了可 fetch 强行回传低质量 URL。
    try:
        ranked_results, ranked_urls, high_quality_urls, rank_meta = _rank_search_results(
            final_query,
            results,
            max_results,
        )
        if rank_meta.get("applied"):
            results = ranked_results
            await log_info(
                ctx,
                (
                    f"web_search 重排完成: mode={rank_meta.get('mode')} "
                    f"input={rank_meta.get('input_count')} output={rank_meta.get('output_count')} "
                    f"high_quality={rank_meta.get('high_quality_count')}"
                ),
                config.debug_enabled,
            )
    except Exception as e:
        await log_info(
            ctx,
            f"web_search 重排阶段异常，已回退原始结果: {e}",
            config.debug_enabled,
        )

    # 将本次搜索结果中的 URL 写入会话状态，供后续工具调用链复用。
    if ctx:
        try:
            if not ranked_urls:
                ranked_urls = _extract_urls_from_search_result(results)

            await ctx.set_state("last_search_urls", ranked_urls)
            await ctx.set_state("last_search_urls_high_quality", high_quality_urls)

            if ranked_urls:
                await log_info(
                    ctx,
                    f"已缓存 {len(ranked_urls)} 个搜索结果 URL 供 web_fetch 回退使用",
                    config.debug_enabled,
                )
            if high_quality_urls:
                await log_info(
                    ctx,
                    f"已缓存 {len(high_quality_urls)} 个高质量 URL 供 web_fetch 优先回退使用",
                    config.debug_enabled,
                )
        except Exception:
            # URL 缓存失败不影响主流程
            pass

    await log_info(ctx, "Search Finished!", config.debug_enabled)
    return results


@mcp.tool(
    name="web_fetch",
    description="""
    Fetches and extracts the complete content from a specified URL and returns it
    as a structured Markdown document.
    Prefer passing `url` directly; compatible aliases `q`, `input`, `prompt`,
    `question`, `link`, and `webpage` are also accepted.
    If URL is omitted, the tool will try to reuse cached URLs from the latest
    `web_search` call: high-quality cache first, then general cache, and pick one
    by `result_index` (1-based, default 1).
    The final URL should be a valid HTTP/HTTPS web address pointing to the target page.
    Ensure the URL is complete and accessible (not behind authentication or paywalls).
    The function will:
    - Retrieve the full HTML content from the URL
    - Parse and extract all meaningful content (text, images, links, tables, code blocks)
    - Convert the HTML structure to well-formatted Markdown
    - Preserve the original content hierarchy and formatting
    - Remove scripts, styles, and other non-content elements
    Returns
    -------
    str
        A Markdown-formatted string containing:
        - Metadata header (source URL, title, fetch timestamp)
        - Table of Contents (if applicable)
        - Complete page content with preserved structure
        - All text, links, images, tables, and code blocks from the original page
        
        The output maintains 100% content fidelity with the source page and is
        ready for documentation, analysis, or further processing.
    Notes
    -----
    - Does NOT summarize or modify content - returns complete original text
    - Handles special characters, encoding (UTF-8), and nested structures
    - May not capture dynamically loaded content requiring JavaScript execution
    - Respects the original language without translation
    """
)
async def web_fetch(
    url: str = "",
    result_index: int = 1,
    q: str = "",
    input: str = "",
    prompt: str = "",
    question: str = "",
    link: str = "",
    webpage: str = "",
    ctx: Context = None,
) -> str:
    final_url = ""
    url_candidates = [url, q, input, prompt, question, link, webpage]
    for candidate in url_candidates:
        if isinstance(candidate, str):
            picked = _pick_first_url(candidate)
            if picked:
                final_url = picked
                break

    if not final_url:
        fallback_policy = config.fetch_fallback_policy
        all_urls = await _get_cached_search_urls(ctx, "last_search_urls")
        high_quality_urls = await _get_cached_search_urls(ctx, "last_search_urls_high_quality")

        chosen_source = ""
        chosen_index = 0

        if fallback_policy == "high_quality_only":
            final_url, chosen_index = _pick_url_by_index(high_quality_urls, result_index)
            chosen_source = "high_quality"
        elif fallback_policy == "all_only":
            final_url, chosen_index = _pick_url_by_index(all_urls, result_index)
            chosen_source = "all"
        else:
            # prefer_high_quality_then_all
            if high_quality_urls and result_index <= len(high_quality_urls):
                final_url, chosen_index = _pick_url_by_index(high_quality_urls, result_index)
                chosen_source = "high_quality"
            else:
                final_url, chosen_index = _pick_url_by_index(all_urls, result_index)
                chosen_source = "all"

        if final_url:
            await log_info(
                ctx,
                (
                    "web_fetch 未收到 url，自动回退为最近一次 web_search 的 "
                    f"{chosen_source} URL[{chosen_index}]: {final_url}"
                ),
                config.debug_enabled,
            )

    if not final_url:
        return (
            "参数缺失：未提供有效 `url`。请直接传入 `url`（支持 http/https 或域名），"
            "或先调用 `web_search` 让服务器缓存结果 URL 后再调用 `web_fetch`。"
        )

    try:
        api_url, api_key = _resolve_runtime_api_credentials(ctx)
        model, requested_model, fallback_used = _resolve_runtime_model(ctx)
    except ValueError as e:
        error_msg = str(e)
        if ctx:
            await ctx.report_progress(error_msg)
        return f"配置错误: {error_msg}"
    await log_info(ctx, f"Begin Fetch: {final_url}", config.debug_enabled)

    if requested_model:
        if fallback_used:
            await log_info(
                ctx,
                f"模型请求 {requested_model!r} 不在白名单，自动回退到 {model}",
                config.debug_enabled,
            )
        else:
            await log_info(
                ctx,
                f"使用请求模型: {model}",
                config.debug_enabled,
            )

    grok_provider = GrokSearchProvider(api_url, api_key, model)
    results = await grok_provider.fetch(final_url, ctx)
    await log_info(ctx, "Fetch Finished!", config.debug_enabled)
    return results


@mcp.tool(
    name="get_config_info",
    description="""
    Returns the current Grok Search MCP server configuration information and tests the connection.

    This tool is useful for:
    - Verifying that environment variables are correctly configured
    - Testing API connectivity by sending a request to /models endpoint
    - Debugging configuration issues
    - Checking the current API endpoint and settings

    Returns
    -------
    str
        A JSON-encoded string containing configuration details:
        - `api_url`: The configured Grok API endpoint
        - `api_key`: The API key (masked for security, showing only first and last 4 characters)
        - `model`: The currently selected model for search and fetch operations
        - `debug_enabled`: Whether debug mode is enabled
        - `log_level`: Current logging level
        - `log_dir`: Directory where logs are stored
        - `config_status`: Overall configuration status (✅ complete or ❌ error)
        - `connection_test`: Result of testing API connectivity to /models endpoint
          - `status`: Connection status
          - `message`: Status message with model count
          - `response_time_ms`: API response time in milliseconds
          - `available_models`: List of available model IDs (only present on successful connection)

    Notes
    -----
    - API keys are automatically masked for security
    - This tool does not require any parameters
    - Useful for troubleshooting before making actual search requests
    - Automatically tests API connectivity during execution
    """
)
async def get_config_info() -> str:
    import json
    import httpx

    config_info = config.get_config_info()

    # 添加连接测试
    test_result = {
        "status": "未测试",
        "message": "",
        "response_time_ms": 0
    }

    try:
        api_url = config.grok_api_url
        api_key = config.grok_api_key

        # 构建 /models 端点 URL
        models_url = f"{api_url.rstrip('/')}/models"

        # 发送测试请求
        import time
        start_time = time.time()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                models_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )

            response_time = (time.time() - start_time) * 1000  # 转换为毫秒

            if response.status_code == 200:
                test_result["status"] = "✅ 连接成功"
                test_result["message"] = f"成功获取模型列表 (HTTP {response.status_code})"
                test_result["response_time_ms"] = round(response_time, 2)

                # 尝试解析返回的模型列表
                try:
                    models_data = response.json()
                    if "data" in models_data and isinstance(models_data["data"], list):
                        model_count = len(models_data["data"])
                        test_result["message"] += f"，共 {model_count} 个模型"

                        # 提取所有模型的 ID/名称
                        model_names = []
                        for model in models_data["data"]:
                            if isinstance(model, dict) and "id" in model:
                                model_names.append(model["id"])

                        if model_names:
                            test_result["available_models"] = model_names
                except:
                    pass
            else:
                test_result["status"] = "⚠️ 连接异常"
                test_result["message"] = f"HTTP {response.status_code}: {response.text[:100]}"
                test_result["response_time_ms"] = round(response_time, 2)

    except httpx.TimeoutException:
        test_result["status"] = "❌ 连接超时"
        test_result["message"] = "请求超时（10秒），请检查网络连接或 API URL"
    except httpx.RequestError as e:
        test_result["status"] = "❌ 连接失败"
        test_result["message"] = f"网络错误: {str(e)}"
    except ValueError as e:
        test_result["status"] = "❌ 配置错误"
        test_result["message"] = str(e)
    except Exception as e:
        test_result["status"] = "❌ 测试失败"
        test_result["message"] = f"未知错误: {str(e)}"

    config_info["connection_test"] = test_result

    return json.dumps(config_info, ensure_ascii=False, indent=2)


@mcp.tool(
    name="switch_model",
    description="""
    Switches the default Grok model used for search and fetch operations, and persists the setting.

    This tool is useful for:
    - Changing the AI model used for web search and content fetching
    - Testing different models for performance or quality comparison
    - Persisting model preference across sessions

    Parameters
    ----------
    model : str
        Allowed values only:
        - "grok-4.1-fast" (default, daily use)
        - "grok-4.1-thinking" (harder reasoning)
        - "grok-4.2-beta" (research-heavy tasks)

    Returns
    -------
    str
        A JSON-encoded string containing:
        - `status`: Success or error status
        - `previous_model`: The model that was being used before
        - `current_model`: The newly selected model
        - `message`: Status message
        - `config_file`: Path where the model preference is saved

    Notes
    -----
    - The model setting is persisted to ~/.config/grok-search/config.json
    - This setting will be used for all future search and fetch operations
    - You can verify available models using the get_config_info tool
    """
)
async def switch_model(model: str) -> str:
    import json

    try:
        previous_model = config.grok_model
        canonical_model, fallback_used = config.set_model(model)
        current_model = config.grok_model

        if fallback_used:
            message = (
                f"请求模型 {model!r} 不在白名单，已自动切换到默认模型 {current_model}。"
            )
        else:
            message = f"模型已从 {previous_model} 切换到 {current_model}"

        result = {
            "status": "✅ 成功",
            "previous_model": previous_model,
            "current_model": current_model,
            "requested_model": model,
            "resolved_model": canonical_model,
            "fallback_to_default": fallback_used,
            "message": message,
            "config_file": str(config.config_file),
            "allowed_models": list(config.allowed_models),
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        result = {
            "status": "❌ 失败",
            "message": f"未知错误: {str(e)}"
        }
        return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(
    name="toggle_builtin_tools",
    description="""
    Toggle Claude Code's built-in WebSearch and WebFetch tools on/off.

    Parameters: action - "on" (block built-in), "off" (allow built-in), "status" (check)
    Returns: JSON with current status and deny list
    """
)
async def toggle_builtin_tools(action: str = "status") -> str:
    import json

    # Locate project root
    root = Path.cwd()
    while root != root.parent and not (root / ".git").exists():
        root = root.parent

    settings_path = root / ".claude" / "settings.json"
    tools = ["WebFetch", "WebSearch"]

    # Load or initialize
    if settings_path.exists():
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    else:
        settings = {"permissions": {"deny": []}}

    deny = settings.setdefault("permissions", {}).setdefault("deny", [])
    blocked = all(t in deny for t in tools)

    # Execute action
    if action in ["on", "enable"]:
        for t in tools:
            if t not in deny:
                deny.append(t)
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        msg = "官方工具已禁用"
        blocked = True
    elif action in ["off", "disable"]:
        deny[:] = [t for t in deny if t not in tools]
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        msg = "官方工具已启用"
        blocked = False
    else:
        msg = f"官方工具当前{'已禁用' if blocked else '已启用'}"

    return json.dumps({
        "blocked": blocked,
        "deny_list": deny,
        "file": str(settings_path),
        "message": msg
    }, ensure_ascii=False, indent=2)


def _resolve_transport() -> str:
    raw_transport = os.getenv("MCP_TRANSPORT", "streamable-http").strip().lower()
    transport_aliases = {
        "stdio": "stdio",
        "http": "http",
        "sse": "sse",
        "streamable-http": "streamable-http",
        "streamable_http": "streamable-http",
        "streamable": "streamable-http",
    }
    transport = transport_aliases.get(raw_transport)
    if transport:
        return transport
    supported = ", ".join(sorted(transport_aliases.keys()))
    raise ValueError(
        f"MCP_TRANSPORT 不支持: {raw_transport!r}，可选值: {supported}"
    )


def _resolve_port() -> int:
    raw_port = os.getenv("MCP_PORT") or os.getenv("PORT") or "8000"
    try:
        return int(raw_port)
    except ValueError as exc:
        raise ValueError(f"MCP_PORT/PORT 不是有效整数: {raw_port!r}") from exc


def _resolve_network_options() -> tuple[str, int, str, str, str]:
    host = os.getenv("MCP_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = _resolve_port()
    path = os.getenv("MCP_PATH", "/mcp").strip() or "/mcp"
    sse_path = os.getenv("MCP_SSE_PATH", "/sse").strip() or "/sse"
    message_path = os.getenv("MCP_MESSAGE_PATH", "/messages/").strip() or "/messages/"
    return host, port, path, sse_path, message_path


def _resolve_bearer_token() -> str | None:
    token = os.getenv("MCP_BEARER_TOKEN", "").strip()
    return token or None


class BearerTokenMiddleware:
    def __init__(self, app, token: str):
        self.app = app
        self._token = token

    @staticmethod
    def _read_auth_header(scope) -> str:
        raw_headers = scope.get("headers") or []
        for key_bytes, value_bytes in raw_headers:
            if key_bytes.decode("latin-1").lower() == "authorization":
                return value_bytes.decode("latin-1")
        return ""

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        auth_header = self._read_auth_header(scope)
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

        if token and secrets.compare_digest(token, self._token):
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "unauthorized",
                    "type": "authentication_error",
                }
            },
        )
        await response(scope, receive, send)


def _build_http_middleware(token: str | None) -> list[StarletteMiddleware] | None:
    if not token:
        return None
    return [StarletteMiddleware(BearerTokenMiddleware, token=token)]


def main():
    import signal
    import threading

    # 信号处理（仅主线程）
    if threading.current_thread() is threading.main_thread():
        def handle_shutdown(signum, frame):
            os._exit(0)
        signal.signal(signal.SIGINT, handle_shutdown)
        if sys.platform != 'win32':
            signal.signal(signal.SIGTERM, handle_shutdown)

    # Windows 父进程监控
    if sys.platform == 'win32':
        import time
        import ctypes
        parent_pid = os.getppid()

        def is_parent_alive(pid):
            """Windows 下检查进程是否存活"""
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return True
            exit_code = ctypes.c_ulong()
            result = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            return result and exit_code.value == STILL_ACTIVE

        def monitor_parent():
            while True:
                if not is_parent_alive(parent_pid):
                    os._exit(0)
                time.sleep(2)

        threading.Thread(target=monitor_parent, daemon=True).start()

    try:
        transport = _resolve_transport()
        host, port, path, sse_path, message_path = _resolve_network_options()
        bearer_token = _resolve_bearer_token()
        middleware = _build_http_middleware(bearer_token)

        if transport == "stdio":
            mcp.run(transport="stdio")
        elif transport in {"http", "streamable-http"}:
            mcp.run(
                transport=transport,
                host=host,
                port=port,
                path=path,
                middleware=middleware,
            )
        elif transport == "sse":
            # FastMCP 的 message_path 来自 settings；这里直接覆盖确保可配置。
            fastmcp.settings.message_path = message_path
            mcp.run(
                transport="sse",
                host=host,
                port=port,
                path=sse_path,
                middleware=middleware,
            )
        else:
            raise ValueError(f"未知 transport: {transport}")
    except KeyboardInterrupt:
        pass
    except ValueError as e:
        print(f"启动失败: {e}", file=sys.stderr)
        os._exit(1)
    finally:
        os._exit(0)


if __name__ == "__main__":
    main()
