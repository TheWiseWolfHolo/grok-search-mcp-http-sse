import os
import json
from pathlib import Path

class Config:
    _instance = None
    _SETUP_COMMAND = (
        'claude mcp add-json grok-search --scope user '
        '\'{"type":"stdio","command":"uvx","args":["--from",'
        '"git+https://github.com/TheWiseWolfHolo/grok-search-mcp-http-sse","grok-search"],'
        '"env":{"GROK_API_URL":"your-api-url","GROK_API_KEY":"your-api-key"}}\''
    )
    # 模型策略：固定三档，非法输入自动回退默认档
    _DEFAULT_MODEL = "grok-4.1-fast"
    _ALLOWED_MODELS = (
        "grok-4.1-fast",
        "grok-4.1-thinking",
        "grok-4.2-beta",
    )
    _MODEL_ALIASES = {
        # 旧命名兼容
        "grok-4-fast": "grok-4.1-fast",
        "grok-4-thinking": "grok-4.1-thinking",
        # 常见简写兼容
        "fast": "grok-4.1-fast",
        "thinking": "grok-4.1-thinking",
        "research": "grok-4.2-beta",
        "beta": "grok-4.2-beta",
    }
    _RANKING_MODES = ("fast", "balanced", "strict")
    _FETCH_FALLBACK_POLICIES = (
        "prefer_high_quality_then_all",
        "all_only",
        "high_quality_only",
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_file = None
            cls._instance._cached_model = None
        return cls._instance

    @property
    def config_file(self) -> Path:
        if self._config_file is None:
            config_dir = Path.home() / ".config" / "grok-search"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_file = config_dir / "config.json"
        return self._config_file

    def _load_config_file(self) -> dict:
        if not self.config_file.exists():
            return {}
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_config_file(self, config_data: dict) -> None:
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise ValueError(f"无法保存配置文件: {str(e)}")

    @property
    def debug_enabled(self) -> bool:
        return os.getenv("GROK_DEBUG", "false").lower() in ("true", "1", "yes")

    @property
    def search_strip_think_enabled(self) -> bool:
        return os.getenv("GROK_SEARCH_STRIP_THINK", "true").lower() in ("true", "1", "yes")

    @property
    def search_timezone(self) -> str:
        # 默认统一使用 UTC+08:00（北京时间），避免外层模型按自身知识截止时间误判“当前时间”
        return os.getenv("GROK_SEARCH_TIMEZONE", "UTC+08:00").strip() or "UTC+08:00"

    @property
    def search_always_inject_time_context(self) -> bool:
        # 默认每次搜索都注入时间上下文，提升时间敏感查询的稳定性
        return os.getenv("GROK_SEARCH_ALWAYS_INJECT_TIME_CONTEXT", "true").lower() in ("true", "1", "yes")

    @property
    def search_ranking_mode(self) -> str:
        raw = os.getenv("GROK_SEARCH_RANKING_MODE", "balanced").strip().lower()
        if raw in self._RANKING_MODES:
            return raw
        return "balanced"

    @property
    def search_min_score(self) -> float:
        raw = os.getenv("GROK_SEARCH_MIN_SCORE", "0.52")
        try:
            value = float(raw)
        except ValueError:
            return 0.52
        return max(0.0, min(1.0, value))

    @property
    def search_low_quality_quota(self) -> int:
        raw = os.getenv("GROK_SEARCH_LOW_QUALITY_QUOTA", "1")
        try:
            value = int(raw)
        except ValueError:
            return 1
        return max(0, value)

    @property
    def search_debug_score_enabled(self) -> bool:
        return os.getenv("GROK_SEARCH_DEBUG_SCORE", "false").lower() in ("true", "1", "yes")

    @property
    def fetch_fallback_policy(self) -> str:
        raw = os.getenv(
            "GROK_FETCH_FALLBACK_POLICY",
            "prefer_high_quality_then_all",
        ).strip().lower()
        if raw in self._FETCH_FALLBACK_POLICIES:
            return raw
        return "prefer_high_quality_then_all"

    @property
    def retry_max_attempts(self) -> int:
        return int(os.getenv("GROK_RETRY_MAX_ATTEMPTS", "3"))

    @property
    def retry_multiplier(self) -> float:
        return float(os.getenv("GROK_RETRY_MULTIPLIER", "1"))

    @property
    def retry_max_wait(self) -> int:
        return int(os.getenv("GROK_RETRY_MAX_WAIT", "10"))

    @property
    def grok_api_url(self) -> str:
        url = os.getenv("GROK_API_URL")
        if not url:
            raise ValueError(
                f"Grok API URL 未配置！\n"
                f"请使用以下命令配置 MCP 服务器：\n{self._SETUP_COMMAND}"
            )
        return url

    @property
    def grok_api_key(self) -> str:
        key = os.getenv("GROK_API_KEY")
        if not key:
            raise ValueError(
                f"Grok API Key 未配置！\n"
                f"请使用以下命令配置 MCP 服务器：\n{self._SETUP_COMMAND}"
            )
        return key

    @property
    def tavily_enabled(self) -> bool:
        return os.getenv("TAVILY_ENABLED", "false").lower() in ("true", "1", "yes")

    @property
    def tavily_api_key(self) -> str | None:
        return os.getenv("TAVILY_API_KEY")

    @property
    def log_level(self) -> str:
        return os.getenv("GROK_LOG_LEVEL", "INFO").upper()

    @property
    def log_dir(self) -> Path:
        log_dir_str = os.getenv("GROK_LOG_DIR", "logs")
        if Path(log_dir_str).is_absolute():
            return Path(log_dir_str)
        user_log_dir = Path.home() / ".config" / "grok-search" / log_dir_str
        user_log_dir.mkdir(parents=True, exist_ok=True)
        return user_log_dir

    @property
    def grok_model(self) -> str:
        if self._cached_model is not None:
            return self._cached_model

        raw_model = (
            os.getenv("GROK_MODEL")
            or self._load_config_file().get("model")
            or self._DEFAULT_MODEL
        )
        model = self._normalize_model(raw_model, strict=False)
        self._cached_model = model
        return model

    def _normalize_model(self, model: str, strict: bool = False) -> str:
        normalized = (model or "").strip().lower()
        canonical_model = self._MODEL_ALIASES.get(normalized, normalized)

        if canonical_model in self._ALLOWED_MODELS:
            return canonical_model

        if strict:
            allowed = ", ".join(self._ALLOWED_MODELS)
            raise ValueError(
                f"不支持的模型: {model!r}。仅允许以下模型: {allowed}"
            )
        return self._DEFAULT_MODEL

    def resolve_model(self, model: str) -> tuple[str, bool]:
        canonical_model = self._normalize_model(model, strict=False)
        normalized = (model or "").strip().lower()
        mapped_model = self._MODEL_ALIASES.get(normalized, normalized)
        fallback_used = mapped_model not in self._ALLOWED_MODELS
        return canonical_model, fallback_used

    def set_model(self, model: str) -> tuple[str, bool]:
        canonical_model, fallback_used = self.resolve_model(model)
        config_data = self._load_config_file()
        config_data["model"] = canonical_model
        self._save_config_file(config_data)
        self._cached_model = canonical_model
        return canonical_model, fallback_used

    @staticmethod
    def _mask_api_key(key: str) -> str:
        """脱敏显示 API Key，只显示前后各 4 个字符"""
        if not key or len(key) <= 8:
            return "***"
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

    def get_config_info(self) -> dict:
        """获取配置信息（API Key 已脱敏）"""
        try:
            api_url = self.grok_api_url
            api_key_raw = self.grok_api_key
            api_key_masked = self._mask_api_key(api_key_raw)
            config_status = "✅ 配置完整"
        except ValueError as e:
            api_url = "未配置"
            api_key_masked = "未配置"
            config_status = f"❌ 配置错误: {str(e)}"

        return {
            "GROK_API_URL": api_url,
            "GROK_API_KEY": api_key_masked,
            "GROK_MODEL": self.grok_model,
            "ALLOWED_MODELS": list(self._ALLOWED_MODELS),
            "GROK_DEBUG": self.debug_enabled,
            "GROK_SEARCH_STRIP_THINK": self.search_strip_think_enabled,
            "GROK_SEARCH_TIMEZONE": self.search_timezone,
            "GROK_SEARCH_ALWAYS_INJECT_TIME_CONTEXT": self.search_always_inject_time_context,
            "GROK_SEARCH_RANKING_MODE": self.search_ranking_mode,
            "GROK_SEARCH_MIN_SCORE": self.search_min_score,
            "GROK_SEARCH_LOW_QUALITY_QUOTA": self.search_low_quality_quota,
            "GROK_SEARCH_DEBUG_SCORE": self.search_debug_score_enabled,
            "GROK_FETCH_FALLBACK_POLICY": self.fetch_fallback_policy,
            "GROK_LOG_LEVEL": self.log_level,
            "GROK_LOG_DIR": str(self.log_dir),
            "TAVILY_ENABLED": self.tavily_enabled,
            "TAVILY_API_KEY": self._mask_api_key(self.tavily_api_key) if self.tavily_api_key else "未配置",
            "config_status": config_status
        }

    @property
    def allowed_models(self) -> tuple[str, ...]:
        return self._ALLOWED_MODELS

config = Config()
