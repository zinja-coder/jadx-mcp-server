# /// script
# dependencies = [
#   "fastmcp",
#   "httpx",
#   "logging",
#   "langchain_mcp_adapters",
#   "laggraph",
#   "langchain_ollama",
#   "rich",
#   "types"
# ]
# ///

import asyncio
import json
import os
import httpx
import typer

from typing import List
from rich.console import Console
from rich.panel import Panel 
from rich.prompt import Prompt, IntPrompt 
from rich.table import Table 

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

# Initializing rich console for pretty cli
console = Console() # creating console object
app = typer.Typer(help="Zin MCP Client, Bridge between local LLM and MCP Servers", add_completion=False)

# Default path for for mcp server configurations
DEFAULT_CONFIG_PATH = "mcp_config.json"

# Implementing MCP Tools Client to handler tool invokation and all 
class MCPToolsClient:
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = os.path.expanduser(config_path)
