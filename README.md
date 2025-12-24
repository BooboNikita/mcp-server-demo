# MCP Server Demo

[![Version][version-badge]][repo-url]
[![Python Version][python-badge]][python-url]
[![UV Version][uv-badge]][uv-url]
[![License][license-badge]][license-url]

这是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的示例项目，展示了如何构建一个 MCP 服务器以及如何编写一个能够自动调用工具的智能客户端。

## 项目特点

- **MCP 服务器 (`mcptools.py`)**: 使用 `FastMCP` 构建，包含数学计算、天气查询等工具，以及动态生成的资源和提示词模板。
- **智能客户端 (`client.py`)**: 
  - 集成 Kimi (Moonshot AI) 大模型。
  - **自动工具调用**: 客户端能够自动识别 LLM 的工具调用请求，执行本地工具并将结果返回给 LLM。
  - **交互式对话**: 提供命令行界面，支持连续提问。
- **依赖管理**: 使用 `uv` 进行快速的依赖管理。

## 快速开始

### 1. 安装依赖

确保你已经安装了 Python 3.13+，建议使用 `uv`：

```bash
# 如果使用 uv
uv sync

# 或者使用 pip
pip install mcp[cli] langchain-openai langchain python-dotenv
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件，并配置你的 API 密钥。**注意：请勿将 `.env` 文件提交到版本控制系统。**

```env
KIMI_API_KEY=你的_KIMI_API_KEY
KIMI_API_URL=https://api.moonshot.cn/v1
```

### 3. 运行项目

客户端会自动启动并连接服务器脚本。运行以下命令：

```bash
python client.py mcptools.py
```

连接成功后，你可以在 `Query >` 提示符下进行提问：

- `Query > 帮我计算 123 + 456`
- `Query > 北京现在的天气怎么样？`
- `Query > 退出` (输入 `exit` 或 `quit`)

## 服务器功能

### 可用工具 (Tools)
- `add(a, b)`: 加法计算。
- `subtract(a, b)`: 减法计算。
- `get_weather(city, unit)`: 查询指定城市的模拟天气。

### 可用资源 (Resources)
- `greeting://{name}`: 获取个性化欢迎语。
- `file://documents/{name}`: 读取模拟文档内容。
- `config://settings`: 获取应用配置 JSON。

### 提示词模板 (Prompts)
- `greet_user(name, style)`: 根据风格生成欢迎提示词。

## 项目结构

- `mcptools.py`: MCP 服务器实现。
- `client.py`: 集成 LLM 的 MCP 客户端。
- `database.py`: 数据库操作示例。
- `pyproject.toml`: 项目配置与依赖说明。

## 许可证

MIT

<!-- 引用式链接定义 -->
[version-badge]: https://img.shields.io/badge/version-0.1.0-blue.svg
[python-badge]: https://img.shields.io/badge/python-3.13.3-blue.svg
[uv-badge]: https://img.shields.io/badge/uv-0.9.17-blue.svg
[license-badge]: https://img.shields.io/badge/license-MIT-green.svg
[repo-url]: https://github.com/BooboNikita/mcp-server-demo
[python-url]: https://www.python.org/
[uv-url]: https://github.com/astral-sh/uv
[license-url]: https://opensource.org/licenses/MIT
