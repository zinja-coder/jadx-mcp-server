<div align="center">

# JADX-MCP-SERVER

![GitHub contributors JADX-AI-MCP](https://img.shields.io/github/contributors/zinja-coder/jadx-ai-mcp)
![GitHub contributors JADX-MCP-SERVER](https://img.shields.io/github/contributors/zinja-coder/jadx-mcp-server)
![GitHub all releases](https://img.shields.io/github/downloads/zinja-coder/jadx-ai-mcp/total)
![GitHub release (latest by SemVer)](https://img.shields.io/github/downloads/zinja-coder/jadx-ai-mcp/latest/total)
![Latest release](https://img.shields.io/github/release/zinja-coder/jadx-ai-mcp.svg)
![Java 11+](https://img.shields.io/badge/Java-11%2B-blue)
![Python 3.10+](https://img.shields.io/badge/python-3%2E10%2B-blue)
[![License](http://img.shields.io/:license-apache-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0.html)

</div>
<!-- Still in early stage of development — expect bugs, crashes, and logical errors.-->

<!-- MCP (Model Context Protocol) server that connects to a custom plugin of [JADX](https://github.com/skylot/jadx) called [JADX-AI-MCP](https://github.com/zinja-coder/jadx-ai-mcp) and provides reverse engineering capabilities directly to local LLMs like Claude Desktop.-->

![jadx-mcp-banner](static/image.png)

--- 

# Download now: https://github.com/zinja-coder/jadx-ai-mcp/releases

---

## 🤖 What is JADX-MCP-SERVER?

**JADX MCP Server** is a standalone Python server that interacts with a modified version of `jadx-gui` (see: [jadx-ai-mcp](https://github.com/zinja-coder/jadx-ai-mcp)) via MCP (Model Context Protocol). It lets LLMs communicate with the decompiled Android app context live.


## 🤖 What is JADX-AI-MCP?

**JADX-AI-MCP** is a plugin for the [JADX decompiler](https://github.com/skylot/jadx) that integrates directly with [Model Context Protocol (MCP)](https://github.com/anthropic/mcp) to provide **live reverse engineering support with LLMs like Claude**.

Think: "Decompile → Context-Aware Code Review → AI Recommendations" — all in real time.

Watch the demo!

[![Watch the video](https://img.youtube.com/vi/Od86IOkkaHg/0.jpg)](https://www.youtube.com/watch?v=Od86IOkkaHg&autoplay=1)

It is combination of two tools:
1. [JADX-AI-MCP](https://github.com/zinja-coder/jadx-ai-mcp)
2. JADX MCP SERVER

## Current MCP Tools

The following MCP tools are available:

- `fetch_current_class()` — Get the class name and full source of selected class
- `get_selected_text()` — Get currently selected text
- `get_all_classes()` — List all classes in the project
- `get_class_source(class_name)` — Get full source of a given class
- `get_method_by_name(class_name, method_name)` — Fetch a method’s source
- `search_method_by_name(method_name)` — Search method across classes
- `get_methods_of_class(class_name)` — List methods in a class
- `get_fields_of_class(class_name)` — List fields in a class
- `get_method_code(class_name, method_name)` — Alias for `get_method_by_name` //to be removed
- `get_smali_of_class(class_name)` — Fetch smali of class

---

## 🗒️ Sample Prompts

🔍 Basic Code Understanding

    "Explain what this class does in one paragraph."

    "Summarize the responsibilities of this method."

    "Is there any obfuscation in this class?"

    "List all Android permissions this class might require."

🛡️ Vulnerability Detection

    "Are there any insecure API usages in this method?"

    "Check this class for hardcoded secrets or credentials."

    "Does this method sanitize user input before using it?"

    "What security vulnerabilities might be introduced by this code?"

🛠️ Reverse Engineering Helpers

    "Deobfuscate and rename the classes and methods to something readable."

    "Can you infer the original purpose of this smali method?"

    "What libraries or SDKs does this class appear to be part of?"

📦 Static Analysis

    "List all network-related API calls in this class."

    "Identify file I/O operations and their potential risks."

    "Does this method leak device info or PII?"

🤖 AI Code Modification

    "Refactor this method to improve readability."

    "Add comments to this code explaining each step."

    "Rewrite this Java method in Python for analysis."

📄 Documentation & Metadata

    "Generate Javadoc-style comments for all methods."

    "What package or app component does this class likely belong to?"

    "Can you identify the Android component type (Activity, Service, etc.)?"
---

## 📦 Features (v0.0.1-beta)

- ✅ MCP server baked into JADX-GUI
- ✅ Exposes currently selected class via HTTP
- ✅ Built-in Claude Desktop integration
- ✅ Beta support for real-time code review
- ✅ MCP client interoperability via local loopback

---

## 🛠️ Getting Started

[READ HERE](https://github.com/zinja-coder/jadx-ai-mcp?tab=readme-ov-file#%EF%B8%8F-getting-started)

## 🛣️ Future Roadmap

 - Add Support for apktool

 - Add support for hermes code (ReactNative Application)

 - Add more useful MCP Tools

 - Make LLM be able to modify code on JADX

 - Add prompts templates, give llm access to Android APK Files as Resources

 - **END-GOAL** : Make all android reverse engineering and APK modification tools Connect with single MCP server to make reverse engineering apk files as easy as possible purely from vibes.

## NOTE For Contributors

 - The files related to JADX-AI-MCP can be found [here](https://github.com/zinja-coder/jadx-ai-mcp)

 - The files related to **jadx-mcp-server** can be found in this repository only.


## 🙏 Credits

This project is a plugin for JADX, an amazing open-source Android decompiler created and maintained by [@skylot](https://github.com/skylot). All core decompilation logic belongs to them. I have only extended it to support my MCP server with AI capabilities.

[📎 Original README (JADX)](https://github.com/skylot/jadx)

The original README.md from jadx is included here in this repository for reference and credit.

This MCP server is made possible by the extensibility of JADX-GUI and the amazing Android reverse engineering community.

Also huge thanks to [@aaddrick](https://github.com/aaddrick) for developing Claude desktop for Debian based linux.

And in last thanks to [@anthropics](https://github.com/anthropics) for developing the Model Context Protocol and [@FastMCP](https://github.com/modelcontextprotocol/python-sdk) team


## 📄 License

This plugin inherits the Apache 2.0 License from the original JADX repository.

## ⚖️ Legal Warning

**Disclaimer**

The tools `jadx-ai-mcp` and `jadx_mcp_server` are intended strictly for educational, research, and ethical security assessment purposes. They are provided "as-is" without any warranties, expressed or implied. Users are solely responsible for ensuring that their use of these tools complies with all applicable laws, regulations, and ethical guidelines.

By using `jadx-ai-mcp` or `jadx_mcp_server`, you agree to use them only in environments you are authorized to test, such as applications you own or have explicit permission to analyze. Any misuse of these tools for unauthorized reverse engineering, infringement of intellectual property rights, or malicious activity is strictly prohibited.

The developers of `jadx-ai-mcp` and `jadx_mcp_server` shall not be held liable for any damage, data loss, legal consequences, or other consequences resulting from the use or misuse of these tools. Users assume full responsibility for their actions and any impact caused by their usage.

Use responsibly. Respect intellectual property. Follow ethical hacking practices.

---

Built with ❤️ for the reverse engineering and AI communities.
