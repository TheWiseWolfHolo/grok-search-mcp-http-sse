![Image](../pic/image.png)
<div align="center">

# Grok Search MCP

English | [简体中文](../README.md)

**Integrate Grok search capabilities into any MCP-compatible AI client to enhance retrieval, grounding, and fact-checking workflows**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0.0+-green.svg)](https://github.com/jlowin/fastmcp)

</div>

---

## Overview

Grok Search MCP is an MCP (Model Context Protocol) server built on [FastMCP](https://github.com/jlowin/fastmcp). It provides real-time web search and webpage fetching for any MCP-compatible client/model by routing requests to your configured upstream search provider.

### Core Value
- **Break Knowledge Cutoff Limits**: Give AI clients access to up-to-date web information
- **Enhanced Fact-Checking**: Real-time search to verify information accuracy and timeliness
- **Structured Output**: Returns standardized JSON with title, link, and summary
- **Plug and Play**: Seamlessly integrates via MCP protocol


**Workflow**: `AI Client/Model → MCP → Grok API → Search/Fetch → Structured Return`

## Why Choose Grok?

Comparison with other search solutions:

| Feature | Grok Search MCP | Google Custom Search API | Bing Search API | SerpAPI |
|---------|----------------|-------------------------|-----------------|---------|
| **AI-Optimized Results** | ✅ Optimized for AI understanding | ❌ General search results | ❌ General search results | ❌ General search results |
| **Content Summary Quality** | ✅ AI-generated high-quality summaries | ⚠️ Requires post-processing | ⚠️ Requires post-processing | ⚠️ Requires post-processing |
| **Real-time** | ✅ Real-time web data | ✅ Real-time | ✅ Real-time | ✅ Real-time |
| **Integration Complexity** | ✅ MCP plug and play | ⚠️ Requires development | ⚠️ Requires development | ⚠️ Requires development |
| **Return Format** | ✅ AI-friendly JSON | ⚠️ Requires formatting | ⚠️ Requires formatting | ⚠️ Requires formatting |

## Features

- ✅ OpenAI-compatible interface, environment variable configuration
- ✅ Real-time web search + webpage content fetching
- ✅ Support for platform-specific searches (Twitter, Reddit, GitHub, etc.)
- ✅ Configuration testing tool (connection test + API Key masking)
- ✅ Dynamic model switching (switch between Grok models with persistent settings)
- ✅ **Tool routing control (one-click disable built-in WebSearch/WebFetch, force use GrokSearch)**
- ✅ **Automatic time injection (automatically gets local time during search for accurate time-sensitive queries)**
- ✅ Extensible architecture for additional search providers

## Quick Start


**Python Environment**:
- Python 3.10 or higher
- Any MCP-compatible client configured (for example: Codex, Claude Code, CherryStudio, Kelivo)

**uv tool** (Recommended Python package manager):

Please ensure you have successfully installed the [uv tool](https://docs.astral.sh/uv/getting-started/installation/):

<details>
<summary><b>Windows Installation</b></summary>

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

</details>

<details>
<summary><b>Linux/macOS Installation</b></summary>

Download and install using curl or wget:

```bash
# Using curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using wget
wget -qO- https://astral.sh/uv/install.sh | sh
```

</details>

> **💡 Important Note**: We **strongly recommend** Windows users run this project in WSL (Windows Subsystem for Linux)!
### 1. Installation & Configuration

Use any MCP-compatible client for setup. Below is a `claude mcp add-json` CLI example (GUI clients can paste the same JSON config directly):

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

Note: prepare your own OpenAI-compatible API endpoint and API key, then replace `GROK_API_URL` and `GROK_API_KEY`.

### 1.5 Deploy to Zeabur (Streamable HTTP / SSE)

If you want to deploy MCP as a remote service (instead of local `stdio`), use the following runtime options.

#### Transport modes

- `MCP_TRANSPORT=streamable-http` (recommended, default)
- `MCP_TRANSPORT=sse` (legacy compatibility)
- `MCP_TRANSPORT=stdio` (local CLI)

#### Network options

- `MCP_HOST`: default `0.0.0.0`
- `MCP_PORT`: uses `MCP_PORT` first, then platform `PORT`, fallback `8000`
- `MCP_PATH`: Streamable HTTP path, default `/mcp`
- `MCP_SSE_PATH`: SSE path, default `/sse`
- `MCP_MESSAGE_PATH`: SSE message path, default `/messages/`

#### Recommended Zeabur env

```env
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PATH=/mcp
MCP_BEARER_TOKEN=replace_with_a_strong_random_secret

# Avoid encoding issues when clients read stderr
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
GROK_SEARCH_EMPTY_RESULT_RETRY=true
GROK_SEARCH_EMPTY_RESULT_RETRY_RELAX_MIN_SCORE=0.08
GROK_SEARCH_EMPTY_RESULT_RETRY_EXTRA_LOW_QUALITY_QUOTA=1
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
```

#### Remote endpoint examples

- Streamable HTTP: `https://<your-service>.zeabur.app/mcp`
- SSE Endpoint: `https://<your-service>.zeabur.app/sse`
- SSE Message Endpoint: `https://<your-service>.zeabur.app/messages/`

If you are using the current public deployment, you can directly use:

- `https://grok-tavily-mcp.zeabur.app/mcp`

#### Codex remote config example

```toml
[mcp_servers.grok-search]
url = "https://<your-service>.zeabur.app/mcp"
bearer_token_env_var = "MCP_BEARER_TOKEN"
```

> If `MCP_BEARER_TOKEN` is configured, all HTTP/SSE MCP requests must include
> `Authorization: Bearer <token>`. Missing/invalid tokens will return `401`.

#### 3-Tier Model Policy (Default)

- Everyday: `grok-4.1-fast` (default)
- Harder reasoning: `grok-4.1-thinking`
- Research-heavy: `grok-4.2-beta`
- Non-whitelisted model inputs do not fail; they automatically fall back to `grok-4.1-fast`

#### Custom URL / Key / Model (Optional)

Priority: request header > environment variable > defaults

- API URL: `X-Grok-Api-Url` or `GROK_API_URL`
- API Key: `X-Grok-Api-Key` or `GROK_API_KEY`
- Model: `X-Grok-Model` / `X-Grok-Model-Tier` or `GROK_MODEL`

If neither model headers nor `GROK_MODEL` are provided, the server defaults to `grok-4.1-fast` under the 3-tier policy.

#### Search response sanitization (enabled by default)

- `web_search` may use internal reasoning, but by default the final response strips `<think>...</think>` blocks to keep downstream parsing stable.
- Toggle: `GROK_SEARCH_STRIP_THINK=true` (default)
- Set to `false` only when you explicitly need raw model output for debugging.

#### Common client setup (CherryStudio / Kelivo)

Use the same core values:

- URL: `https://<your-service>.zeabur.app/mcp`
- Header Name: `Authorization`
- Header Value: `Bearer <your MCP_BEARER_TOKEN>`

CherryStudio (remote MCP):

- Choose `streamable-http` (recommended)
- Set URL to full `/mcp` endpoint
- Add header `Authorization: Bearer <token>`

Kelivo (remote MCP):

- Choose `streamable-http` (fallback to `sse` only if needed)
- URL uses `/mcp` (`/sse` in SSE mode)
- Header Name: `Authorization`
- Header Value: `Bearer <token>`

#### Common error troubleshooting

- Error: `1 validation error for call[web_search] ... Missing required argument: query`
  - Cause: client called `web_search` without a search term.
  - Fix: include `query` in tool arguments.
  - Compatibility: server also accepts `q`, `input`, `prompt`, `question`, `keyword`, `keywords`, and `search_query` as aliases.
- Error: `1 validation error for call[web_fetch] ... Missing required argument: url`
  - Cause: old clients/prompts treated `url` as strictly required.
  - Fix: in current versions, `url` is optional; if omitted, server first uses high-quality cached URLs, then falls back to the general cache (use `result_index` to choose Nth result).
- Symptom: `web_search` output includes `<think>` blocks and breaks URL extraction/tool chaining.
  - Fix: keep `GROK_SEARCH_STRIP_THINK=true` so responses are sanitized before being returned.

### 1.6 Docker Image and Auto Build (GitHub Actions + GHCR)

The repository now includes:

- `Dockerfile`
- `.dockerignore`
- `.github/workflows/docker-image.yml`

#### Auto build triggers

- Push to `main` or `grok-with-tavily`: build and push image to GHCR
- Push `v*` tags: build and push versioned images
- Pull Request to `main`: build-only validation (no push)

#### Image naming

Default target:

`ghcr.io/<owner>/<repo>`

For this repo:

`ghcr.io/thewisewolfholo/grok-search-mcp-http-sse`

Common tags:

- `latest` (default branch)
- branch tags (for example `main`, `grok-with-tavily`)
- `sha-<commit>`
- `v*` (when you push tags)

#### Stability Validation Snapshot (2026-03-01)

- Validation target: real interaction path `outer model -> MCP -> Grok API`
- Outer driver model: generic client-driven LLM flow (used only for tool-trigger simulation)
- MCP internal model policy: fixed 3-tier allowlist `grok-4.1-fast` / `grok-4.1-thinking` / `grok-4.2-beta`
- Validation rounds: `20` total, covering `search`, `search->fetch (explicit URL)`, `search->fetch (fallback URL)`, alias parameters, and error inputs
- Result: `20/20` passed (`100%`), above acceptance threshold `>=95%`
- Rate limit policy: throttled `web_search` / `web_fetch` calls (minimum interval `7s`, theoretical peak `~8.57 RPM`, satisfying `<10 RPM`)
- Baseline commit: `b0c4039` (`fix: make web_fetch url optional with search-url fallback`)

#### Post-release Quick Checks

- Check workflow runs:
  - `gh run list --repo TheWiseWolfHolo/grok-search-mcp-http-sse --limit 5`
- Inspect a specific run:
  - `gh run view <run_id> --repo TheWiseWolfHolo/grok-search-mcp-http-sse`
- Validate GHCR image:
  - `docker manifest inspect ghcr.io/thewisewolfholo/grok-search-mcp-http-sse:latest`

#### Build locally

```bash
docker build -t grok-search-mcp-http-sse:local .
```

#### Run locally (Streamable HTTP)

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

#### Deploy on Zeabur using image

Create a new service in Zeabur with Docker Image:

- Image: `ghcr.io/thewisewolfholo/grok-search-mcp-http-sse:latest`

Minimum environment variables:

- `GROK_API_URL`
- `GROK_API_KEY`
- `TAVILY_API_KEY`
- `TAVILY_API_URL`
- `MCP_TRANSPORT=streamable-http`
- `MCP_HOST=0.0.0.0`
- `MCP_PATH=/mcp`
- `GROK_SEARCH_STRIP_THINK=true`

Recommended additions (source quality + fallback policy):

- `GROK_SEARCH_RANKING_MODE=balanced` (options: `fast` / `balanced` / `strict`)
- `GROK_SEARCH_MIN_SCORE=0.52`
- `GROK_SEARCH_LOW_QUALITY_QUOTA=1`
- `GROK_SEARCH_INCLUDE_MODEL_HEADER=true`
- `GROK_SEARCH_EMPTY_RESULT_RETRY=true`
- `GROK_SEARCH_EMPTY_RESULT_RETRY_RELAX_MIN_SCORE=0.08`
- `GROK_SEARCH_EMPTY_RESULT_RETRY_EXTRA_LOW_QUALITY_QUOTA=1`
- `GROK_FETCH_FALLBACK_POLICY=prefer_high_quality_then_all` (options: `all_only` / `high_quality_only`)
- `GROK_SEARCH_DEBUG_SCORE=false`

Default quality strategy (`balanced`):

- `web_search` re-ranks by query relevance + source trust before returning
- It will not force-fill low-quality links just to hit `max_results`
- When `web_fetch` omits `url`, it uses high-quality cache first, then general cache

MCP URL after deploy:

`https://<your-zeabur-domain>/mcp`

#### Configuration Guide

Configuration is done through **environment variables**, set directly in the `env` field during installation:

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `GROK_API_URL` | ✅ | - | Grok API endpoint (OpenAI-compatible format) |
| `GROK_API_KEY` | ✅ | - | Your API Key |
| `GROK_SEARCH_STRIP_THINK` | ❌ | `true` | Strip `<think>...</think>` blocks from `web_search` responses |
| `GROK_SEARCH_TIMEZONE` | ❌ | `UTC+08:00` | Authoritative search time baseline (supports `UTC±HH[:MM]` or IANA zone names) |
| `GROK_SEARCH_ALWAYS_INJECT_TIME_CONTEXT` | ❌ | `true` | Always inject absolute time context into `web_search` prompts |
| `GROK_SEARCH_QUERY_TIME_GUARD` | ❌ | `true` | Enable query-time guard for time-sensitive intents |
| `GROK_SEARCH_QUERY_TIME_GUARD_MODE` | ❌ | `balanced` | Guard mode: `balanced` / `strict` / `audit` |
| `GROK_SEARCH_QUERY_TIME_GUARD_APPEND_STYLE` | ❌ | `suffix` | Constraint append style: `suffix` / `prefix` |
| `GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_WITH_MODEL` | ❌ | `true` | Use model-based judgment for stale-year ambiguous queries |
| `GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_MODEL` | ❌ | `grok-4.1-fast` | Model used only for time-guard ambiguity judgment |
| `GROK_SEARCH_RANKING_MODE` | ❌ | `balanced` | Result ranking mode: `fast` / `balanced` / `strict` |
| `GROK_SEARCH_MIN_SCORE` | ❌ | `0.52` | Minimum quality score threshold for returning search results |
| `GROK_SEARCH_LOW_QUALITY_QUOTA` | ❌ | `1` | Max allowed low-quality results kept after ranking |
| `GROK_SEARCH_INCLUDE_MODEL_HEADER` | ❌ | `true` | Prefix `web_search` output with a one-line model info header |
| `GROK_SEARCH_EMPTY_RESULT_RETRY` | ❌ | `true` | Retry once when first `web_search` output is an empty array |
| `GROK_SEARCH_EMPTY_RESULT_RETRY_RELAX_MIN_SCORE` | ❌ | `0.08` | Min-score relaxation applied during empty-result retry |
| `GROK_SEARCH_EMPTY_RESULT_RETRY_EXTRA_LOW_QUALITY_QUOTA` | ❌ | `1` | Extra low-quality quota allowed during empty-result retry |
| `GROK_FETCH_FALLBACK_POLICY` | ❌ | `prefer_high_quality_then_all` | `web_fetch` fallback strategy when `url` is omitted |
| `GROK_SEARCH_DEBUG_SCORE` | ❌ | `false` | Include ranking score fields in `web_search` output (debug only) |
| `GROK_DEBUG` | ❌ | `false` | Enable debug mode (`true`/`false`) |
| `GROK_LOG_LEVEL` | ❌ | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `GROK_LOG_DIR` | ❌ | `logs` | Log file storage directory |

⚠️ **Security Notes**:
- API Keys are stored in your MCP client configuration file (for example, Claude Code: `~/.config/claude/mcp.json`), please protect this file
- Do not share configurations containing real API Keys or commit them to version control

Time-baseline notes:
- Default baseline timezone is `UTC+08:00` (Beijing time, override with `GROK_SEARCH_TIMEZONE`)
- `web_search` injects absolute current-time context by default (`GROK_SEARCH_ALWAYS_INJECT_TIME_CONTEXT=true`)
- This helps prevent models from relying on stale knowledge-cutoff assumptions for “today/latest/recent” queries
- Query time guard is enabled by default (`GROK_SEARCH_QUERY_TIME_GUARD=true`) and appends explicit baseline constraints for time-sensitive queries
- Default guard mode is `balanced`; choose `strict` for stronger correction or `audit` for observe-only behavior
- Append style defaults to `suffix` and can be switched to `prefix`
- For stale-year but ambiguous intent queries, model-based guard judgment is enabled by default (`GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_WITH_MODEL=true`)
- The ambiguity-judgment model defaults to `grok-4.1-fast` (`GROK_SEARCH_QUERY_TIME_GUARD_JUDGE_MODEL`) and does not change your primary search model policy
- If the first `web_search` output is empty, the server retries once with relaxed ranking thresholds by default
- `web_search` prefixes output with a model info line (`search_model/judge_model/retry`) by default for easier debugging

### 2. Verify Installation

If you are using Claude Code CLI, you can run:

```bash
claude mcp list
```

You should see the `grok-search` server registered.

### 3. Test Configuration

After configuration, it is **strongly recommended** to run a configuration test in your MCP client conversation to ensure everything is working properly:

In your client conversation, type:
```
Please test the Grok Search configuration
```

Or simply say:
```
Show grok-search configuration info
```

The tool will automatically perform the following checks:
- ✅ Verify environment variables are loaded correctly
- ✅ Test API connection (send request to `/models` endpoint)
- ✅ Display response time and available model count
- ✅ Identify and report any configuration errors

**Successful Output Example**:
```json
{
  "GROK_API_URL": "https://YOUR-API-URL/grok/v1",
  "GROK_API_KEY": "sk-a*****************xyz",
  "GROK_DEBUG": false,
  "GROK_LOG_LEVEL": "INFO",
  "GROK_LOG_DIR": "/home/user/.config/grok-search/logs",
  "config_status": "✅ Configuration Complete",
  "connection_test": {
    "status": "✅ Connection Successful",
    "message": "Successfully retrieved model list (HTTP 200), 5 models available",
    "response_time_ms": 234.56
  }
}
```

If you see `❌ Connection failed` or `⚠️ Connection warning`, please check:
- API URL is correct
- API Key is valid
- Network connection is working

###  4. Advanced Configuration (Optional)
To improve tool routing stability, you can add a system prompt policy in your AI client. The following template is generic; if you use Claude Code, add it in `~/.claude/CLAUDE.md`.
<details>
<summary><b>💡 Grok Search Enhance System Prompt</b> (Click to expand)</summary>

# Grok Search Enhance System Prompt

## 0. Module Activation
**Trigger Condition**: Automatically activate this module and **forcibly replace** built-in tools when performing:
- Web search / Information retrieval / Fact-checking
- Get webpage content / URL parsing / Document fetching
- Query latest information / Break through knowledge cutoff limits

## 1. Tool Routing Policy

### Forced Replacement Rules
| Use Case | ❌ Disabled (Built-in) | ✅ Mandatory (GrokSearch) |
| :--- | :--- | :--- |
| Web Search | `WebSearch` | `mcp__grok-search__web_search` |
| Web Fetch | `WebFetch` | `mcp__grok-search__web_fetch` |
| Config Diagnosis | N/A | `mcp__grok-search__get_config_info` |

### Tool Capability Matrix

| Tool | Function | Key Parameters | Output Format | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **web_search** | Real-time web search | `query` (recommended)<br>Aliases: `q` / `input` / `prompt` / `question` / `keyword` / `keywords` / `search_query`<br>`platform` (optional: Twitter/GitHub/Reddit)<br>`min_results` / `max_results` | JSON Array<br>`{title, url, content}` | • Fact-checking<br>• Latest news<br>• Technical docs retrieval |
| **web_fetch** | Webpage content fetching | `url` (recommended)<br>Aliases: `q` / `input` / `prompt` / `question` / `link` / `webpage`<br>`result_index` (optional, default 1, picks Nth URL from high-quality cache first, then general cache) | Structured Markdown<br>(with metadata header) | • Complete document retrieval<br>• In-depth content analysis<br>• Link content verification |
| **get_config_info** | Configuration status detection | No parameters | JSON<br>`{api_url, status, connection_test}` | • Connection troubleshooting<br>• First-time use validation |
| **switch_model** | Model switching | `model` (required, only `grok-4.1-fast` / `grok-4.1-thinking` / `grok-4.2-beta`) | JSON<br>`{status, previous_model, current_model, config_file}` | • Fixed 3-tier model policy<br>• Cross-session persistence |
| **toggle_builtin_tools** | Tool routing control | `action` (optional: on/off/status) | JSON<br>`{blocked, deny_list, file}` | • Disable built-in tools<br>• Force route to GrokSearch<br>• Project-level config management |

## 2. Search Workflow

### Phase 1: Query Construction
1.  **Intent Recognition**: Analyze user needs, determine search type:
    - **Broad Search**: Multi-source information aggregation → Use `web_search`
    - **Deep Retrieval**: Complete content from single URL → Use `web_fetch`
2.  **Parameter Optimization**:
    - Set `platform` parameter if focusing on specific platforms
    - Adjust `min_results` / `max_results` based on complexity

### Phase 2: Search Execution
1.  **Primary Strategy**: Prioritize `web_search` for structured summaries
2.  **Deep Supplementation**: If summaries are insufficient, call `web_fetch` on key URLs for complete content
3.  **Iterative Retrieval**: If first-round results don't meet needs, **adjust query terms** and search again (don't give up)

### Phase 3: Result Synthesis
1.  **Information Verification**: Cross-compare multi-source results, identify contradictions
2.  **Timeliness Notation**: For time-sensitive information, **must** annotate source and timestamp
3.  **Citation Standard**: Output **must include** source URL in format: `[Title](URL)`

## 3. Error Handling

| Error Type | Diagnosis Method | Recovery Strategy |
| :--- | :--- | :--- |
| Connection failure | Call `get_config_info` to check configuration | Prompt user to check API URL / Key |
| No search results | Check if query is too specific | Broaden search terms, remove constraints |
| Web fetch timeout | Check URL accessibility | Try searching alternative sources |
| Content truncated | Check target page structure | Fetch in segments or prompt user to visit directly |

## 4. Anti-Patterns

| ❌ Prohibited Behavior | ✅ Correct Approach |
| :--- | :--- |
| Using built-in `WebSearch` / `WebFetch` | **Must** use GrokSearch corresponding tools |
| No source citation after search | Output **must** include `[Source](URL)` references |
| Give up after single search failure | Adjust parameters and retry at least once |
| Assume webpage content without fetching | **Must** call `web_fetch` to verify key information |
| Ignore search result timeliness | Time-sensitive information **must** be date-labeled |

---
Module Description:
- Forced Replacement: Explicitly disable built-in tools, force routing to GrokSearch
- Three-tool Coverage: web_search + web_fetch + get_config_info
- Error Handling: Includes configuration diagnosis recovery strategy
- Citation Standard: Mandatory source labeling, meets information traceability requirements

</details>

### 5. Project Details

#### MCP Tools

This project provides five MCP tools:

##### `web_search` - Web Search

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Recommended | `""` | Search query string (aliases: `q`, `input`, `prompt`, `question`, `keyword`, `keywords`, `search_query`) |
| `platform` | string | ❌ | `""` | Focus on specific platforms (e.g., `"Twitter"`, `"GitHub, Reddit"`) |
| `min_results` | int | ❌ | `3` | Minimum number of results |
| `max_results` | int | ❌ | `10` | Maximum number of results |

**Returns**: JSON array containing `title`, `url`, `content`

<details>
<summary><b>Return Example</b> (Click to expand)</summary>

```json
[
  {
    "title": "Model Context Protocol (MCP) Technical Specification",
    "url": "https://modelcontextprotocol.io/docs",
    "description": "Official MCP documentation defining standardized communication interfaces between AI models and external tools"
  },
  {
    "title": "GitHub - FastMCP: Build MCP Servers Quickly",
    "url": "https://github.com/jlowin/fastmcp",
    "description": "Python framework for building MCP servers with simpler tool registration and async workflows"
  },
  {
    "title": "MCP Architecture Concepts",
    "url": "https://modelcontextprotocol.io/docs/concepts/architecture",
    "description": "Architecture-level documentation for MCP transport, protocol shape, and tool invocation flow"
  }
]
```
</details>

##### `web_fetch` - Web Content Fetching

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Recommended | Target webpage URL (`http/https` or domain) |
| `q` / `input` / `prompt` / `question` / `link` / `webpage` | string | ❌ | Compatibility aliases for `url` |
| `result_index` | int | ❌ | When `url` is omitted, pick URL by 1-based index from high-quality cache first; if unavailable, fall back to general cache (default `1`) |

**Features**: Retrieves complete webpage content and converts to structured Markdown, preserving headings, lists, tables, code blocks, etc.

<details>
<summary><b>Return Example</b> (Click to expand)</summary>

```markdown
---
source: https://modelcontextprotocol.io/docs/concepts/architecture
title: MCP Architecture Documentation
fetched_at: 2024-01-15T10:30:00Z
---

# MCP Architecture Documentation

## Table of Contents
- [Core Concepts](#core-concepts)
- [Protocol Layers](#protocol-layers)
- [Communication Patterns](#communication-patterns)

## Core Concepts

Model Context Protocol (MCP) is a standardized communication protocol for connecting AI models with external tools and data sources.

### Design Goals
- **Standardization**: Provide unified interface specifications
- **Extensibility**: Support custom tool registration
- **Efficiency**: Optimize data transmission and processing

## Protocol Layers

MCP adopts a three-layer architecture design:

| Layer | Function | Implementation |
|-------|----------|----------------|
| Transport | Data transmission | stdio, HTTP, WebSocket |
| Protocol | Message format | JSON-RPC 2.0 |
| Application | Tool definition | Tool Schema + Handlers |

## Communication Patterns

MCP supports the following communication patterns:

1. **Request-Response**: Synchronous tool invocation
2. **Streaming**: Process large datasets
3. **Event Notification**: Asynchronous status updates

```python
# Example: Register MCP tool
@mcp.tool(name="search")
async def search_tool(query: str) -> str:
    results = await perform_search(query)
    return json.dumps(results)
```

For more information, visit [Official Documentation](https://modelcontextprotocol.io)
```
</details>

##### `get_config_info` - Configuration Info Query

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| None | - | - | This tool requires no parameters |

**Features**: Display configuration status, test API connection, return response time and available model count (API Key automatically masked)

<details>
<summary><b>Return Example</b> (Click to expand)</summary>

```json
{
  "GROK_API_URL": "https://YOUR-API-URL/grok/v1",
  "GROK_API_KEY": "sk-a*****************xyz",
  "GROK_DEBUG": false,
  "GROK_LOG_LEVEL": "INFO",
  "GROK_LOG_DIR": "/home/user/.config/grok-search/logs",
  "config_status": "✅ Configuration Complete",
  "connection_test": {
    "status": "✅ Connection Successful",
    "message": "Successfully retrieved model list (HTTP 200), 5 models available",
    "response_time_ms": 234.56
  }
}
```

</details>

##### `switch_model` - Model Switching

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | ✅ | Only allowed: `"grok-4.1-fast"`, `"grok-4.1-thinking"`, `"grok-4.2-beta"` |

**Features**:
- Switch the default Grok model used for search and fetch operations (fixed 3-tier policy)
- Configuration automatically persisted to `~/.config/grok-search/config.json`
- Cross-session settings retention
- Non-whitelisted model inputs do not fail and automatically fall back to `grok-4.1-fast`

<details>
<summary><b>Return Example</b> (Click to expand)</summary>

```json
{
  "status": "✅ success",
  "previous_model": "grok-4.1-fast",
  "current_model": "grok-4.1-thinking",
  "requested_model": "grok-4.1-thinking",
  "resolved_model": "grok-4.1-thinking",
  "fallback_to_default": false,
  "message": "model switched from grok-4.1-fast to grok-4.1-thinking",
  "config_file": "/home/user/.config/grok-search/config.json",
  "allowed_models": [
    "grok-4.1-fast",
    "grok-4.1-thinking",
    "grok-4.2-beta"
  ]
}
```

**Usage Example**:

In your client conversation, type:
```
Please switch the Grok model to grok-4.1-thinking
```

Or simply say:
```
Switch model to grok-4.2-beta
```

</details>

##### `toggle_builtin_tools` - Tool Routing Control

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | ❌ | `"status"` | Action type: `"on"`/`"enable"`(disable built-in tools), `"off"`/`"disable"`(enable built-in tools), `"status"`/`"check"`(view status) |

**Features**:
- Control project-level `.claude/settings.json` `permissions.deny` configuration (currently targeted at Claude Code projects)
- Disable/enable Claude Code built-in `WebSearch` and `WebFetch`
- Force routing to GrokSearch MCP tools
- Auto-locate project root (find `.git`)
- Preserve other configuration items

<details>
<summary><b>Return Example</b> (Click to expand)</summary>

```json
{
  "blocked": true,
  "deny_list": ["WebFetch", "WebSearch"],
  "file": "/path/to/project/.claude/settings.json",
  "message": "built-in tools disabled"
}
```

**Usage Example**:

```
# Disable built-in tools (recommended)
Disable built-in search and fetch tools

# Enable built-in tools
Enable built-in search and fetch tools

# Check current status
Show status of built-in tools
```

</details>

---

<details>
<summary><h2>Project Architecture</h2> (Click to expand)</summary>

```
src/grok_search/
├── config.py          # Configuration management (environment variables)
├── server.py          # MCP service entry (tool registration)
├── logger.py          # Logging system
├── utils.py           # Formatting utilities
└── providers/
    ├── base.py        # SearchProvider base class
    └── grok.py        # Grok API implementation
```

</details>

## FAQ

**Q: How do I prepare API access?**
A: Prepare your own OpenAI-compatible API Endpoint and Key, then configure `grok-search` in your MCP client

**Q: How to verify configuration after setup?**
A: Say "Show grok-search configuration info" in your client conversation to check connection test results

## License

This project is open source under the [MIT License](LICENSE).

---
