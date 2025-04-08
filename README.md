# JADX MCP Server

This repository contains an **MCP (Model Context Protocol) server** that interfaces with a custom fork of [JADX](https://github.com/skylot/jadx) to provide reverse engineering capabilities directly to local LLMs like Claude Desktop.

> ✅ MCP tools let you interact with the decompiled Android app from JADX-GUI using natural language or custom automation.

---

## ✨ Features

- Fetch currently selected class from JADX GUI
- Get selected code snippet
- List classes, methods, and fields
- Fetch smali code of any class
- Designed to integrate with Claude or any other local LLM over MCP

---

## 🧠 Current Tools

The following MCP tools are available:

- `fetch_current_class()` — Get the class name and full source of selected class
- `get_selected_text()` — Get currently selected text
- `get_all_classes()` — List all classes in the project
- `get_class_source(class_name)` — Get full source of a given class
- `get_method_by_name(class_name, method_name)` — Fetch a method’s source
- `search_method_by_name(method_name)` — Search method across classes
- `get_methods_of_class(class_name)` — List methods in a class
- `get_fields_of_class(class_name)` — List fields in a class
- `get_method_code(class_name, method_name)` — Alias for `get_method_by_name`
- `get_smali_of_class(class_name)` — Fetch smali of class

---

## 🚀 Installation

This project uses [`uv`](https://github.com/astral-sh/uv) instead of `pip` for dependency management.

### 1. Install `uv` (if you don't have it yet)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
### 2. Set up the environment
```bash
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```
### 3. Install dependencies
```bash
uv pip install httpx fastmcp
```

### 🔧 Usage

Make sure your modified jadx-gui with the MCP plugin is running locally, which can be downloaded from here: https://github.com/zinja-coder/jadx-ai

Then start the MCP server:
```bash
python mcp_server.py
```

This will expose all tools via MCP so your LLM can call them interactively.

📁 Project Structure
```bash
jadx-mcp-server/
├── mcp_server.py
├── requirements.txt
├── README.md
├── LICENSE
```

📌 Related Projects

    Original JADX: https://github.com/skylot/jadx

    Forked version with plugin support: 

🙏 Credits

Massive credit to @skylot for building and maintaining the original JADX project. This MCP server is made possible by the extensibility of JADX-GUI and the amazing Android reverse engineering community.
📅 Roadmap

Live reverse engineering tools via MCP

Bidirectional sync with jadx-gui

Auto-summarization of class/method logic

Cross-language vulnerability analysis

    UI wrapper for tool configuration

🧪 Version

Beta v0.0.1

Expect breaking changes — contributions and feedback welcome!
