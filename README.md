<div align="center">

# JADX-MCP-SERVER (Part of Zin's Reverse Engineering MCP Suite)

⚡ Fully automated MCP server built to communicate with JADX-AI-MCP Plugin to analyze Android APKs using LLMs like Claude — uncover vulnerabilities, parse manifests, and reverse engineer effortlessly.

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


<div align="center">
    <img alt="banner" height="480px" widht="620px" src="static/image.png">
</div>

<!-- ![jadx-mcp-banner](static/image.png) -->

--- 

#### Download now: https://github.com/zinja-coder/jadx-ai-mcp/releases

---

## 🤖 What is JADX-MCP-SERVER?

**JADX MCP Server** is a standalone Python server that interacts with a modified version of `jadx-gui` (see: [jadx-ai-mcp](https://github.com/zinja-coder/jadx-ai-mcp)) via MCP (Model Context Protocol). It lets LLMs communicate with the decompiled Android app context live.


## 🤖 What is JADX-AI-MCP?

**JADX-AI-MCP** is a plugin for the [JADX decompiler](https://github.com/skylot/jadx) that integrates directly with [Model Context Protocol (MCP)](https://github.com/anthropic/mcp) to provide **live reverse engineering support with LLMs like Claude**.

Think: "Decompile → Context-Aware Code Review → AI Recommendations" — all in real time.

Watch the demos!

- **Perform quick analysis**
  
https://github.com/user-attachments/assets/b65c3041-fde3-4803-8d99-45ca77dbe30a

- **Quickly find vulnerabilities**

https://github.com/user-attachments/assets/c184afae-3713-4bc0-a1d0-546c1f4eb57f

- **Multiple AI Agents Support**

https://github.com/user-attachments/assets/6342ea0f-fa8f-44e6-9b3a-4ceb8919a5b0

- **Analyze The APK Resources**

https://github.com/user-attachments/assets/f42d8072-0e3e-4f03-93ea-121af4e66eb1

It is combination of two tools:
1. [JADX-AI-MCP](https://github.com/zinja-coder/jadx-ai-mcp)
2. JADX MCP SERVER

---

# Zin MCP Suie
 - **[APKTool-MCP-Server](https://github.com/zinja-coder/apktool-mcp-server)**
 - **[JAD-AI-MCP-Plugin](https://github.com/zinja-coder/jadx-ai-mcp)**
 - **[ZIN-MCP-Client](https://github.com/zinja-coder/zin-mcp-client)**

## Current MCP Tools

The following MCP tools are available:

- `fetch_current_class()` — Get the class name and full source of selected class
- `get_selected_text()` — Get currently selected text
- `get_all_classes()` — List all classes in the project
- `get_class_source()` — Get full source of a given class
- `get_method_by_name()` — Fetch a method’s source
- `search_method_by_name()` — Search method across classes
- `get_methods_of_class()` — List methods in a class
- `get_fields_of_class()` — List fields in a class
- `get_smali_of_class()` — Fetch smali of class
- `get_main_activity_class()` — Fetch main activity from jadx mentioned in AndroidManifest.xml file. 
- `get_main_application_classes_code()` — Fetch all the main application classes' code based on the package name defined in the AndroidManifest.xml.
- `get_main_application_classes_names()` — Fetch all the main application classes' names based on the package name defined in the AndroidManifest.xml.
- `get_android_manifest()` — Retrieve and return the AndroidManifest.xml content.
- `get_strings()` : Fetches the strings.xml file
- `get_all_resource_file_names()` : Retrieve all resource files names that exists in application
- `get_resource_file()` : Retrieve resource file content  

---

#### Note: Tested on Claude Desktop. Support for other LLMs might be tested in future.

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

## 🛠️ Getting Started

[READ HERE](https://github.com/zinja-coder/jadx-ai-mcp?tab=readme-ov-file#%EF%B8%8F-getting-started)

## Running on Local LLM Using Ollama and Zin MCP Client - Recommended

<div align="center">
    <a href="https://github.com/zinja-coder/zin-mcp-client">
    <img alt="zin-mcp-client" height="360px" widht="480px" src="https://github.com/user-attachments/assets/0e8e0ecd-0520-422e-a007-03dc62c4118e">
    </a>
</div>

⚡ Lightweight, Fast, Simple, CLI-Based MCP Client for STDIO MCP Servers, to fill the gap and provide bridge between your local LLMs running Ollama and MCP Servers.

Check Now: https://github.com/zinja-coder/zin-mcp-client

Demo: **Perform Code Review to Find Vulnerabilities locally**

https://github.com/user-attachments/assets/4cd26715-b5e6-4b4b-95e4-054de6789f42

## 🛣️ Future Roadmap

- [x] Add Support for apktool

 - [ ] Add support for hermes code (ReactNative Application)

 - [ ] Add more useful MCP Tools

 - [ ] Make LLM be able to modify code on JADX

 - [ ] Add prompts templates, give llm access to Android APK Files as Resources

 - [ ] Build MCP Client to support Local LLM

 - [ ] **END-GOAL** : Make all android reverse engineering and APK modification tools Connect with single MCP server to make reverse engineering apk files as easy as possible purely from vibes.

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

And all opensource maintainers and contributors that makes libraries and dependencies which allows project like this possible.

## Audited and Received Assessment Badge

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/zinja-coder-jadx-mcp-server-badge.png)](https://mseep.ai/app/zinja-coder-jadx-mcp-server)

Thank you Mseep.net for auditing and providing Assessment Badge.

## 📄 License

This plugin inherits the Apache 2.0 License from the original JADX repository.

## ⚖️ Legal Warning

**Disclaimer**

The tools `jadx-ai-mcp` and `jadx_mcp_server` are intended strictly for educational, research, and ethical security assessment purposes. They are provided "as-is" without any warranties, expressed or implied. Users are solely responsible for ensuring that their use of these tools complies with all applicable laws, regulations, and ethical guidelines.

By using `jadx-ai-mcp` or `jadx_mcp_server`, you agree to use them only in environments you are authorized to test, such as applications you own or have explicit permission to analyze. Any misuse of these tools for unauthorized reverse engineering, infringement of intellectual property rights, or malicious activity is strictly prohibited.

The developers of `jadx-ai-mcp` and `jadx_mcp_server` shall not be held liable for any damage, data loss, legal consequences, or other consequences resulting from the use or misuse of these tools. Users assume full responsibility for their actions and any impact caused by their usage.

Use responsibly. Respect intellectual property. Follow ethical hacking practices.

---

## 🙌 Contribute or Support

- Found it useful? Give it a ⭐️
- Got ideas? Open an [issue](https://github.com/zinja-coder/jadx-mcp-server/issues) or submit a PR
- Built something on top? DM me or mention me — I’ll add it to the README!

---

Built with ❤️ for the reverse engineering and AI communities.
