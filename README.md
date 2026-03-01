![这是图片](./images/title.png)
<div align="center">

<!-- # Grok Search MCP -->

[English](./docs/README_EN.md) | 简体中文

**通过 MCP 协议将 Grok 搜索能力集成到任意支持 MCP 的 AI 客户端，增强文档检索与事实核查能力**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0.0+-green.svg)](https://github.com/jlowin/fastmcp)

</div>

---

## 概述

Grok Search MCP 是一个基于 [FastMCP](https://github.com/jlowin/fastmcp) 构建的 MCP（Model Context Protocol）服务器，通过转接你自行配置的上游搜索 Provider，为任意支持 MCP 的 AI 客户端/模型提供实时网络搜索与网页抓取能力。

### 核心价值
- **突破知识截止限制**：让 AI 客户端访问最新网络信息，不再受训练数据时间限制
- **增强事实核查**：实时搜索验证信息的准确性和时效性
- **结构化输出**：返回包含标题、链接、摘要的标准化 JSON，便于 AI 模型理解与引用
- **即插即用**：通过 MCP 协议无缝集成到 Codex、Claude Code、CherryStudio、Kelivo 等客户端


**工作流程**：`AI Client/Model → MCP → Grok API → 搜索/抓取 → 结构化返回`

<details>
<summary><b>💡 更多选择Grok  search 的理由</b></summary>
与其他搜索方案对比：

| 特性 | Grok Search MCP | Google Custom Search API | Bing Search API | SerpAPI |
|------|----------------|-------------------------|-----------------|---------|
| **AI 优化结果** | ✅ 专为 AI 理解优化 | ❌ 通用搜索结果 | ❌ 通用搜索结果 | ❌ 通用搜索结果 |
| **内容摘要质量** | ✅ AI 生成高质量摘要 | ⚠️ 需二次处理 | ⚠️ 需二次处理 | ⚠️ 需二次处理 |
| **实时性** | ✅ 实时网络数据 | ✅ 实时 | ✅ 实时 | ✅ 实时 |
| **集成复杂度** | ✅ MCP 即插即用 | ⚠️ 需自行开发 | ⚠️ 需自行开发 | ⚠️ 需自行开发 |
| **返回格式** | ✅ AI 友好 JSON | ⚠️ 需格式化 | ⚠️ 需格式化 | ⚠️ 需格式化 |

## 功能特性

- ✅ OpenAI 兼容接口，环境变量配置
- ✅ 实时网络搜索 + 网页内容抓取
- ✅ 支持指定搜索平台（Twitter、Reddit、GitHub 等）
- ✅ 配置测试工具（连接测试 + API Key 脱敏）
- ✅ 动态模型切换（支持切换不同 Grok 模型并持久化保存）
- ✅ **工具路由控制（一键禁用官方 WebSearch/WebFetch，强制使用 GrokSearch）**
- ✅ **自动时间注入（搜索时自动获取本地时间，确保时间相关查询的准确性）**
- ✅ 可扩展架构，支持添加其他搜索 Provider
</details>

## 安装教程
### Step 0.前期准备（若已经安装uv则跳过该步骤）

<details>

**Python 环境**：
- Python 3.10 或更高版本
- 已配置任意支持 MCP 的客户端（如 Codex / Claude Code / CherryStudio / Kelivo）

**uv 工具**（推荐的 Python 包管理器）：

请确保您已成功安装 [uv 工具](https://docs.astral.sh/uv/getting-started/installation/)：

#### Windows 安装 uv
在 PowerShell 中运行以下命令：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**💡 重要提示** ：我们 **强烈推荐** Windows 用户在 WSL（Windows Subsystem for Linux）中运行本项目！

#### Linux/macOS 安装 uv

使用 curl 或 wget 下载并安装：

```bash
# 使用 curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 wget
wget -qO- https://astral.sh/uv/install.sh | sh
```

</details>


### Step 1. 安装 Grok Search MCP 

可使用任意支持 MCP 的客户端完成安装与配置。下面给出 `claude mcp add-json` 作为 CLI 示例（CherryStudio、Kelivo、Codex 等图形客户端可直接填入同等 JSON 配置）：
**注意：**  你需要自行准备兼容 OpenAI 格式的 API Endpoint 与 Key，并替换 **GROK_API_URL**、**GROK_API_KEY** 两个字段。

```bash
claude mcp add-json grok-search --scope user '{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/TheWiseWolfHolo/grok-search-mcp-http-sse",
    "grok-search"
  ],
  "env": {
    "GROK_API_URL": "https://your-api-endpoint.com/v1",
    "GROK_API_KEY": "your-api-key-here"
  }
}'
```

### Step 1.5 网络部署（Zeabur / Streamable HTTP / SSE）

如果你希望把 MCP 服务部署到 Zeabur，通过 URL 远程调用（而不是本地 `stdio`），可以使用下面的启动配置。

#### 传输模式

- `MCP_TRANSPORT=streamable-http`（推荐，默认值）
- `MCP_TRANSPORT=sse`（兼容旧客户端）
- `MCP_TRANSPORT=stdio`（本地 CLI）

#### 通用网络参数

- `MCP_HOST`：默认 `0.0.0.0`
- `MCP_PORT`：优先读取；若未设置则回退到平台 `PORT`；再回退 `8000`
- `MCP_PATH`：Streamable HTTP 路径，默认 `/mcp`
- `MCP_SSE_PATH`：SSE 路径，默认 `/sse`
- `MCP_MESSAGE_PATH`：SSE message 路径，默认 `/messages/`

#### Zeabur 推荐环境变量

```env
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PATH=/mcp
MCP_BEARER_TOKEN=替换为高强度随机字符串

# 避免部分终端/客户端在 stderr 读取时出现编码问题
FASTMCP_SHOW_SERVER_BANNER=false
FASTMCP_ENABLE_RICH_LOGGING=false
FASTMCP_LOG_LEVEL=ERROR
GROK_SEARCH_STRIP_THINK=true
GROK_SEARCH_TIMEZONE=UTC+08:00
GROK_SEARCH_ALWAYS_INJECT_TIME_CONTEXT=true
GROK_SEARCH_QUERY_TIME_GUARD=true
GROK_SEARCH_QUERY_TIME_GUARD_MODE=balanced
GROK_SEARCH_QUERY_TIME_GUARD_APPEND_STYLE=suffix
GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_WITH_MODEL=true
GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_MODEL=grok-4.1-fast
GROK_SEARCH_INCLUDE_MODEL_HEADER=true
GROK_SEARCH_INCLUDE_QUERY_DIAGNOSTIC=true
GROK_SEARCH_EMPTY_RESULT_RETRY=true
GROK_SEARCH_EMPTY_RESULT_RETRY_RELAX_MIN_SCORE=0.08
GROK_SEARCH_EMPTY_RESULT_RETRY_EXTRA_LOW_QUALITY_QUOTA=1
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
```

#### 远程 MCP 地址示例

- Streamable HTTP：`https://<你的服务域名>.zeabur.app/mcp`
- SSE Endpoint：`https://<你的服务域名>.zeabur.app/sse`
- SSE Message Endpoint：`https://<你的服务域名>.zeabur.app/messages/`

如果你使用的是当前公开服务，可直接使用：

- `https://grok-tavily-mcp.zeabur.app/mcp`

#### Codex 配置示例（远程 URL）

```toml
[mcp_servers.grok-search]
url = "https://<你的服务域名>.zeabur.app/mcp"
bearer_token_env_var = "MCP_BEARER_TOKEN"
```

> 如果配置了 `MCP_BEARER_TOKEN`，所有 HTTP/SSE MCP 请求都需要携带
> `Authorization: Bearer <token>`。未携带或错误会返回 `401`。

#### 三档模型策略（默认）

- 日常：`grok-4.1-fast`（默认）
- 稍难：`grok-4.1-thinking`
- 研究：`grok-4.2-beta`
- 传入非白名单模型不会失败，会自动回退到 `grok-4.1-fast`

#### 自定义 URL / Key / 模型（可选）

优先级：请求头 > 环境变量 > 默认值

- API URL：`X-Grok-Api-Url` 或 `GROK_API_URL`
- API Key：`X-Grok-Api-Key` 或 `GROK_API_KEY`
- 模型：`X-Grok-Model` / `X-Grok-Model-Tier` 或 `GROK_MODEL`

如果未提供 `GROK_MODEL` 或请求头模型字段，会自动按三档策略走默认模型 `grok-4.1-fast`。

#### Search 回传净化（默认开启）

- `web_search` 允许模型内部思考，但默认会在回传前移除 `<think>...</think>` 块，减少客户端解析干扰。
- 开关：`GROK_SEARCH_STRIP_THINK=true`（默认）
- 如需调试原始模型输出，可设为 `false`。

#### 常见客户端填写（CherryStudio / Kelivo）

统一填写原则：

- URL：`https://<你的服务域名>.zeabur.app/mcp`
- Header Name：`Authorization`
- Header Value：`Bearer <你的 MCP_BEARER_TOKEN>`

CherryStudio（远程 MCP）：

- Type 选 `streamable-http`（推荐）
- URL 填 `/mcp` 完整地址
- Headers 添加 `Authorization: Bearer <token>`

Kelivo（远程 MCP）：

- 类型选 `streamable-http`（不支持时再回退 `sse`）
- URL 填 `/mcp` 完整地址（`sse` 模式填 `/sse`）
- 请求头名称填 `Authorization`
- 请求头值填 `Bearer <token>`

#### 常见报错排查

- 报错：`1 validation error for call[web_search] ... Missing required argument: query`
  - 原因：客户端发起 `web_search` 时没传搜索词。
  - 处理：确保工具参数包含 `query`。
  - 兼容说明：服务端同时接受 `q` / `input` / `prompt` / `question` / `keyword` / `keywords` / `search_query` 作为搜索词别名。
- 报错：`1 validation error for call[web_fetch] ... Missing required argument: url`
  - 原因：旧版本客户端或旧提示词把 `url` 当成强制必填。
  - 处理：优先使用 `web_fetch_from_last_search`（无需 `url` 参数）；若继续用 `web_fetch`，`url` 也可省略，服务端会先从高质量缓存回退，找不到再回退普通缓存（可用 `result_index` 指定第 N 条）。
- 现象：`web_search` 返回中夹杂 `<think>`，影响后续 URL 提取或工具链传参
  - 处理：保持 `GROK_SEARCH_STRIP_THINK=true`，默认会自动净化回传文本。

### Step 1.6 Docker 镜像与自动构建（GitHub Actions + GHCR）

仓库已内置：

- `Dockerfile`
- `.dockerignore`
- `.github/workflows/docker-image.yml`

#### 自动构建触发规则

- 推送到 `main` 或 `grok-with-tavily` 分支：自动构建并推送镜像到 GHCR
- 推送 `v*` tag：自动构建并推送 tag 镜像
- Pull Request 到 `main`：仅构建校验，不推送

#### 镜像命名规则

默认推送到：

`ghcr.io/<owner>/<repo>`

例如本仓库为：

`ghcr.io/thewisewolfholo/grok-search-mcp-http-sse`

常用 tag：

- `latest`（默认分支）
- 分支名（如 `main`、`grok-with-tavily`）
- `sha-<commit>`
- `v*`（当你 push tag）

#### 稳定性联调验收快照（2026-03-01）

- 验收目标：真实交互链路 `外层模型 -> MCP -> Grok API` 稳定性
- 外层驱动模型：通用大模型客户端（仅用于触发工具调用）
- MCP 内部模型：固定三档白名单 `grok-4.1-fast` / `grok-4.1-thinking` / `grok-4.2-beta`
- 联调轮次：`20` 轮，覆盖 `search`、`search->fetch(显式 URL)`、`search->fetch(回退 URL)`、别名参数、错误输入
- 通过结果：`20/20`（`100%`），高于门槛 `>=95%`
- 频率约束：对 `web_search` / `web_fetch` 执行节流（最小间隔 `7s`，理论峰值约 `8.57 RPM`，满足 `<10 RPM`）
- 验收基线提交：`b0c4039`（`fix: make web_fetch url optional with search-url fallback`）

#### 发布后快速核验

- 检查构建流水线：
  - `gh run list --repo TheWiseWolfHolo/grok-search-mcp-http-sse --limit 5`
- 查看指定 run：
  - `gh run view <run_id> --repo TheWiseWolfHolo/grok-search-mcp-http-sse`
- 校验 GHCR 镜像：
  - `docker manifest inspect ghcr.io/thewisewolfholo/grok-search-mcp-http-sse:latest`

#### 本地手动构建

```bash
docker build -t grok-search-mcp-http-sse:local .
```

#### 本地运行（Streamable HTTP）

```bash
docker run --rm -p 8000:8000 \
  -e GROK_API_URL="https://your-api-endpoint.com/v1" \
  -e GROK_API_KEY="your-api-key" \
  -e TAVILY_API_KEY="your-tavily-key" \
  -e TAVILY_API_URL="https://tavilyload.zeabur.app/api/tavily" \
  -e MCP_TRANSPORT="streamable-http" \
  -e MCP_HOST="0.0.0.0" \
  -e MCP_PATH="/mcp" \
  -e GROK_SEARCH_STRIP_THINK="true" \
  grok-search-mcp-http-sse:local
```

#### Zeabur 使用镜像部署

在 Zeabur 新建服务时选择 Docker Image，填写：

- Image：`ghcr.io/thewisewolfholo/grok-search-mcp-http-sse:latest`

并配置环境变量（至少）：

- `GROK_API_URL`
- `GROK_API_KEY`
- `TAVILY_API_KEY`
- `TAVILY_API_URL`
- `MCP_TRANSPORT=streamable-http`
- `MCP_HOST=0.0.0.0`
- `MCP_PATH=/mcp`
- `GROK_SEARCH_STRIP_THINK=true`
- `GROK_SEARCH_TIMEZONE=UTC+08:00`
- `GROK_SEARCH_ALWAYS_INJECT_TIME_CONTEXT=true`
- `GROK_SEARCH_QUERY_TIME_GUARD=true`
- `GROK_SEARCH_QUERY_TIME_GUARD_MODE=balanced`
- `GROK_SEARCH_QUERY_TIME_GUARD_APPEND_STYLE=suffix`
- `GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_WITH_MODEL=true`
- `GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_MODEL=grok-4.1-fast`

推荐增加（信源质量与回退策略）：

- `GROK_SEARCH_RANKING_MODE=balanced`（可选：`fast` / `balanced` / `strict`）
- `GROK_SEARCH_MIN_SCORE=0.52`
- `GROK_SEARCH_LOW_QUALITY_QUOTA=1`
- `GROK_SEARCH_INCLUDE_MODEL_HEADER=true`
- `GROK_SEARCH_INCLUDE_QUERY_DIAGNOSTIC=true`
- `GROK_SEARCH_EMPTY_RESULT_RETRY=true`
- `GROK_SEARCH_EMPTY_RESULT_RETRY_RELAX_MIN_SCORE=0.08`
- `GROK_SEARCH_EMPTY_RESULT_RETRY_EXTRA_LOW_QUALITY_QUOTA=1`
- `GROK_FETCH_FALLBACK_POLICY=prefer_high_quality_then_all`（可选：`all_only` / `high_quality_only`）
- `GROK_SEARCH_DEBUG_SCORE=false`

时间基准说明：

- 默认时区基准为 `UTC+08:00`（北京时间，可通过 `GROK_SEARCH_TIMEZONE` 调整）
- 默认每次 `web_search` 都会注入当前绝对时间上下文（`GROK_SEARCH_ALWAYS_INJECT_TIME_CONTEXT=true`）
- 目标是避免模型按知识截止时间误判“今天/最新/最近”
- 默认启用 query 时间护栏（`GROK_SEARCH_QUERY_TIME_GUARD=true`），会在命中时间语义时追加时间基准约束
- 护栏模式默认 `balanced`，可选：`strict`（更强纠偏）/`audit`（仅记录不改写）
- 护栏拼接位置默认 `suffix`，可选 `prefix`
- 对“含旧年份但时间语义不明确”的 query，默认启用模型判定（`GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_WITH_MODEL=true`），减少纯关键词匹配依赖

默认质量策略（`balanced`）：

- `web_search` 先按“问题相关性 + 信源可信度”重排，再返回结果
- 不会为了凑 `max_results` 强行塞低质来源；必要时会少返回
- `web_fetch` 未传 `url` 时，先用高质量缓存，再回退普通缓存
- `web_fetch_from_last_search` 可直接按 `result_index` 从最近搜索缓存取 URL（不依赖客户端传 `url`）
- `web_search` 默认会在返回首行加入模型信息（`search_model/judge_model/retry/temporal_verdict/correction`），便于排障
- `web_search` 默认还会输出 `incoming_query` 与 `effective_query` 诊断行（`GROK_SEARCH_INCLUDE_QUERY_DIAGNOSTIC=true`）

部署完成后 MCP URL：

`https://<你的-zeabur-域名>/mcp`


### Step 2. 验证安装 & 检查MCP配置

若你使用 Claude Code CLI，可运行：

```bash
claude mcp list
```

应能看到 `grok-search` 服务器已注册。

配置完成后，**强烈建议**在任意 MCP 客户端对话中运行配置测试，以确保一切正常：

在客户端对话中输入：
```
请测试 Grok Search 的配置
```

或直接说：
```
显示 grok-search 配置信息
```

工具会自动执行以下检查：
- ✅ 验证环境变量是否正确加载
- ✅ 测试 API 连接（向 `/models` 端点发送请求）
- ✅ 显示响应时间和可用模型数量
- ✅ 识别并报告任何配置错误


如果看到 `❌ 连接失败` 或 `⚠️ 连接异常`，请检查：
- API URL 是否正确
- API Key 是否有效
- 网络连接是否正常

### Step 3. 配置系统提示词
为了更稳定地使用 Grok Search，可以在你的 AI 客户端系统提示词中追加工具路由约束。下方给出通用模板；若你使用 Claude Code，可编辑 `~/.claude/CLAUDE.md` 直接应用。

**💡 提示**：现在可以使用 `toggle_builtin_tools` 工具一键禁用官方 WebSearch/WebFetch，强制路由到 GrokSearch！

#### 精简版提示词
```markdown
# Grok Search 提示词 精简版
## 激活与路由
**触发**：网络搜索/网页抓取/最新信息查询时自动激活
**替换**：尽可能使用 Grok-search的工具替换官方原生search以及fetch功能

## 工具矩阵

| Tool | Parameters | Output | Use Case |
|------|------------|--------|----------|
| `web_search` | `query`(推荐)；兼容 `q/input/prompt/question/keyword/keywords/search_query`；`platform`/`min_results`/`max_results`(可选) | `[{title,url,content}]` | 多源聚合/事实核查/最新资讯 |
| `web_fetch` | `url`(推荐)；兼容 `q/input/prompt/question/link/webpage`；`result_index`(可选，默认 1，先从高质量缓存选第 N 条，缺失再回退普通缓存) | Structured Markdown | 完整内容获取/深度分析 |
| `web_fetch_from_last_search` | `result_index`(可选，默认 1；无需 `url`) | Structured Markdown | 直接复用最近 `web_search` 缓存 URL，避免客户端 `url` 必填校验问题 |
| `get_config_info` | 无 | `{api_url,status,test}` | 连接诊断 |
| `switch_model` | `model`(必填，仅允许 `grok-4.1-fast`/`grok-4.1-thinking`/`grok-4.2-beta`) | `{status,previous_model,current_model}` | 固定三档模型切换 |
| `toggle_builtin_tools` | `action`(可选: on/off/status) | `{blocked,deny_list,file}` | 禁用/启用官方工具 |

## 执行策略
**查询构建**：广度用 `web_search`，深度用 `web_fetch`，特定平台设 `platform` 参数
**搜索执行**：优先摘要 → 关键 URL 补充完整内容 → 结果不足调整查询重试（禁止放弃）
**结果整合**：交叉验证 + **强制标注来源** `[标题](URL)` + 时间敏感信息注明日期

## 错误恢复

连接失败 → `get_config_info` 检查 | 无结果 → 放宽查询条件 | 超时 → 搜索替代源


## 核心约束

✅ 强制 GrokSearch 工具 + 输出必含来源引用 + 失败必重试 + 关键信息必验证
❌ 禁止无来源输出 + 禁止单次放弃 + 禁止未验证假设
```

#### 详细版提示词
<details>
<summary><b>💡 Grok Search Enhance 系统提示词（详细版）</b>（点击展开）</summary>

````markdown

  # Grok Search Enhance 系统提示词（详细版）

  ## 0. Module Activation
  **触发条件**：当需要执行以下操作时，自动激活本模块：
  - 网络搜索 / 信息检索 / 事实核查
  - 获取网页内容 / URL 解析 / 文档抓取
  - 查询最新信息 / 突破知识截止限制

  ## 1. Tool Routing Policy

  ### 强制替换规则
  | 需求场景 | ❌ 禁用 (Built-in) | ✅ 强制使用 (GrokSearch) |
  | :--- | :--- | :--- |
  | 网络搜索 | `WebSearch` | `mcp__grok-search__web_search` |
  | 网页抓取 | `WebFetch` | `mcp__grok-search__web_fetch` |
  | 配置诊断 | N/A | `mcp__grok-search__get_config_info` |

  ### 工具能力矩阵

| Tool | Parameters | Output | Use Case |
|------|------------|--------|----------|
| `web_search` | `query`(推荐)；兼容 `q/input/prompt/question/keyword/keywords/search_query`；`platform`/`min_results`/`max_results`(可选) | `[{title,url,content}]` | 多源聚合/事实核查/最新资讯 |
| `web_fetch` | `url`(推荐)；兼容 `q/input/prompt/question/link/webpage`；`result_index`(可选，默认 1，先从高质量缓存选第 N 条，缺失再回退普通缓存) | Structured Markdown | 完整内容获取/深度分析 |
| `web_fetch_from_last_search` | `result_index`(可选，默认 1；无需 `url`) | Structured Markdown | 直接复用最近 `web_search` 缓存 URL，避免客户端 `url` 必填校验问题 |
| `get_config_info` | 无 | `{api_url,status,test}` | 连接诊断 |
| `switch_model` | `model`(必填，仅允许 `grok-4.1-fast`/`grok-4.1-thinking`/`grok-4.2-beta`) | `{status,previous_model,current_model}` | 固定三档模型切换 |
| `toggle_builtin_tools` | `action`(可选: on/off/status) | `{blocked,deny_list,file}` | 禁用/启用官方工具 |


  ## 2. Search Workflow

  ### Phase 1: 查询构建 (Query Construction)
  1.  **意图识别**：分析用户需求，确定搜索类型：
      - **广度搜索**：多源信息聚合 → 使用 `web_search`
      - **深度获取**：单一 URL 完整内容 → 使用 `web_fetch`
  2.  **参数优化**：
      - 若需聚焦特定平台，设置 `platform` 参数
      - 根据需求复杂度调整 `min_results` / `max_results`

  ### Phase 2: 搜索执行 (Search Execution)
  1.  **首选策略**：优先使用 `web_search` 获取结构化摘要
  2.  **深度补充**：若摘要不足以回答问题，对关键 URL 调用 `web_fetch` 获取完整内容
  3.  **迭代检索**：若首轮结果不满足需求，**调整查询词**后重新搜索（禁止直接放弃）

  ### Phase 3: 结果整合 (Result Synthesis)
  1.  **信息验证**：交叉比对多源结果，识别矛盾信息
  2.  **时效标注**：对时间敏感信息，**必须**标注信息来源与时间
  3.  **引用规范**：输出中**强制包含**来源 URL，格式：`[标题](URL)`

  ## 3. Error Handling

  | 错误类型 | 诊断方法 | 恢复策略 |
  | :--- | :--- | :--- |
  | 连接失败 | 调用 `get_config_info` 检查配置 | 提示用户检查 API URL / Key |
  | 无搜索结果 | 检查 query 是否过于具体 | 放宽搜索词，移除限定条件 |
  | 网页抓取超时 | 检查 URL 可访问性 | 尝试搜索替代来源 |
  | 内容被截断 | 检查目标页面结构 | 分段抓取或提示用户直接访问 |

  ## 4. Anti-Patterns

  | ❌ 禁止行为 | ✅ 正确做法 |
  | :--- | :--- |
  | 搜索后不标注来源 | 输出**必须**包含 `[来源](URL)` 引用 |
  | 单次搜索失败即放弃 | 调整参数后至少重试 1 次 |
  | 假设网页内容而不抓取 | 对关键信息**必须**调用 `web_fetch` 验证 |
  | 忽略搜索结果的时效性 | 时间敏感信息**必须**标注日期 |

  ---
  模块说明：
  - 强制替换：明确禁用内置工具，强制路由到 GrokSearch
  - 四工具覆盖：web_search + web_fetch + web_fetch_from_last_search + get_config_info
  - 错误处理：包含配置诊断的恢复策略
  - 引用规范：强制标注来源，符合信息可追溯性要求
````

</details>

### 详细项目介绍

#### MCP 工具说明

本项目提供五个 MCP 工具：

##### `web_search` - 网络搜索

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | 推荐 | `""` | 搜索查询语句（兼容 `q/input/prompt/question/keyword/keywords/search_query`） |
| `platform` | string | ❌ | `""` | 聚焦搜索平台（如 `"Twitter"`, `"GitHub, Reddit"`） |
| `min_results` | int | ❌ | `3` | 最少返回结果数 |
| `max_results` | int | ❌ | `10` | 最多返回结果数 |

**返回**：包含 `title`、`url`、`content` 的 JSON 数组


<details>
<summary><b>返回示例</b>（点击展开）</summary>

```json
[
  {
    "title": "Model Context Protocol (MCP) 官方文档",
    "url": "https://modelcontextprotocol.io/docs",
    "description": "MCP 协议官方文档，定义了 AI 模型与外部工具的标准化通信接口"
  },
  {
    "title": "GitHub - FastMCP: Build MCP Servers Quickly",
    "url": "https://github.com/jlowin/fastmcp",
    "description": "用于快速构建 MCP Server 的 Python 框架，支持异步处理与简化工具注册"
  },
  {
    ...
  }
]
```
</details>

##### `web_fetch` - 网页内容抓取

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 推荐 | 目标网页 URL（支持 `http/https` 或域名） |
| `q` / `input` / `prompt` / `question` / `link` / `webpage` | string | ❌ | `url` 的兼容别名字段 |
| `result_index` | int | ❌ | 当未传 `url` 时，按 1-based 索引先从高质量缓存 URL 选取；无命中时再回退到普通缓存（默认 `1`） |

**功能**：获取完整网页内容并转换为结构化 Markdown，保留标题层级、列表、表格、代码块等元素

##### `web_fetch_from_last_search` - 从最近搜索结果直接抓取

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `result_index` | int | ❌ | 1-based 索引，默认 `1`；无需 `url` 参数，直接从最近一次 `web_search` 缓存中选取 URL |

**功能**：适配部分客户端对 `web_fetch.url` 的强校验场景，避免因缺少 `url` 参数导致调用前拦截失败

<details>
<summary><b>返回示例</b>（点击展开）</summary>

```markdown
---
source: https://modelcontextprotocol.io/docs/concepts/architecture
title: MCP 架构设计文档
fetched_at: 2024-01-15T10:30:00Z
---

# MCP 架构设计文档

## 目录
- [核心概念](#核心概念)
- [协议层次](#协议层次)
- [通信模式](#通信模式)

## 核心概念

Model Context Protocol (MCP) 是一个标准化的通信协议，用于连接 AI 模型与外部工具和数据源。
...

更多信息请访问 [官方文档](https://modelcontextprotocol.io)
```
</details>


##### `get_config_info` - 配置信息查询

**无需参数**。显示配置状态、测试 API 连接、返回响应时间和可用模型数量（API Key 自动脱敏）

<details>
<summary><b>返回示例</b>（点击展开）</summary>

```json
{
  "api_url": "https://YOUR-API-URL/grok/v1",
  "api_key": "sk-a*****************xyz",
  "config_status": "✅ 配置完整",
  "connection_test": {
    "status": "✅ 连接成功",
    "message": "成功获取模型列表 (HTTP 200)，共 x 个模型",
    "response_time_ms": 234.56
  }
}
```

</details>

##### `switch_model` - 模型切换

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | ✅ | 仅允许：`"grok-4.1-fast"`、`"grok-4.1-thinking"`、`"grok-4.2-beta"` |

**功能**：
- 切换用于搜索和抓取操作的默认 Grok 模型（固定三档）
- 配置自动持久化到 `~/.config/grok-search/config.json`
- 支持跨会话保持设置
- 非白名单模型输入不会失败，会自动回退到 `grok-4.1-fast`

<details>
<summary><b>返回示例</b>（点击展开）</summary>

```json
{
  "status": "✅ 成功",
  "previous_model": "grok-4.1-fast",
  "current_model": "grok-4.1-thinking",
  "requested_model": "grok-4.1-thinking",
  "resolved_model": "grok-4.1-thinking",
  "fallback_to_default": false,
  "message": "模型已从 grok-4.1-fast 切换到 grok-4.1-thinking",
  "config_file": "/home/user/.config/grok-search/config.json",
  "allowed_models": [
    "grok-4.1-fast",
    "grok-4.1-thinking",
    "grok-4.2-beta"
  ]
}
```

**使用示例**：

在客户端对话中输入：
```
请将 Grok 模型切换到 grok-4.1-thinking
```

或直接说：
```
切换模型到 grok-4.2-beta
```

</details>

##### `toggle_builtin_tools` - 工具路由控制

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | ❌ | `"status"` | 操作类型：`"on"`/`"enable"`(禁用官方工具)、`"off"`/`"disable"`(启用官方工具)、`"status"`/`"check"`(查看状态) |

**功能**：
- 控制项目级 `.claude/settings.json` 的 `permissions.deny` 配置（该工具目前面向 Claude Code 客户端）
- 禁用/启用 Claude Code 内置的 `WebSearch` 和 `WebFetch` 工具
- 强制路由到 GrokSearch MCP 工具
- 自动定位项目根目录（查找 `.git`）
- 保留其他配置项

<details>
<summary><b>返回示例</b>（点击展开）</summary>

```json
{
  "blocked": true,
  "deny_list": ["WebFetch", "WebSearch"],
  "file": "/path/to/project/.claude/settings.json",
  "message": "官方工具已禁用"
}
```

**使用示例**：

```
# 禁用官方工具（推荐）
禁用官方的 search 和 fetch 工具

# 启用官方工具
启用官方的 search 和 fetch 工具

# 检查当前状态
显示官方工具的禁用状态
```

</details>

---

<details>
<summary><h2>项目架构</h2>（点击展开）</summary>

```
src/grok_search/
├── config.py          # 配置管理（环境变量）
├── server.py          # MCP 服务入口（注册工具）
├── logger.py          # 日志系统
├── utils.py           # 格式化工具
└── providers/
    ├── base.py        # SearchProvider 基类
    └── grok.py        # Grok API 实现
```

</details>

## 常见问题

**Q: 如何准备 API 配置？**
A: 自行准备兼容 OpenAI 格式的 API Endpoint 和 Key，然后在任意 MCP 客户端中完成 `grok-search` 配置

**Q: 配置后如何验证？**
A: 在客户端对话中说“显示 grok-search 配置信息”，查看连接测试结果

## 许可证

本项目采用 [MIT License](LICENSE) 开源。

---
