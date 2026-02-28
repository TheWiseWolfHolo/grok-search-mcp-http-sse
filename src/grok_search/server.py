import sys
from pathlib import Path
import os
import secrets

# 支持直接运行：添加 src 目录到 Python 路径
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import fastmcp
from fastmcp import FastMCP, Context
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
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

@mcp.tool(
    name="web_search",
    description="""
    Performs a third-party web search based on the given query and returns the results
    as a JSON string.

    The `query` should be a clear, self-contained natural-language search query.
    For compatibility, aliases such as `q`, `input`, `prompt`, `question`,
    `keyword`, `keywords`, and `search_query` are also accepted.
    When helpful, include constraints such as topic, time range, language, or domain.

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
    results = await grok_provider.search(final_query, platform, min_results, max_results, ctx)
    await log_info(ctx, "Search Finished!", config.debug_enabled)
    return results


@mcp.tool(
    name="web_fetch",
    description="""
    Fetches and extracts the complete content from a specified URL and returns it
    as a structured Markdown document.
    The `url` should be a valid HTTP/HTTPS web address pointing to the target page.
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
async def web_fetch(url: str, ctx: Context = None) -> str:
    try:
        api_url, api_key = _resolve_runtime_api_credentials(ctx)
        model, requested_model, fallback_used = _resolve_runtime_model(ctx)
    except ValueError as e:
        error_msg = str(e)
        if ctx:
            await ctx.report_progress(error_msg)
        return f"配置错误: {error_msg}"
    await log_info(ctx, f"Begin Fetch: {url}", config.debug_enabled)

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
    results = await grok_provider.fetch(url, ctx)
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


class BearerTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str):
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

        if token and secrets.compare_digest(token, self._token):
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "unauthorized",
                    "type": "authentication_error",
                }
            },
        )


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
