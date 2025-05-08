# /// script
# dependencies = [
#   "fastmcp",
#   "httpx",
#   "logging",
#   "langchain_mcp_adapters",
#   "langgraph",
#   "langchain_ollama",
#   "rich",
#   "typer"
# ]
# ///

from contextlib import AsyncExitStack
import asyncio
import json
import os
from typing import List, Any

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

# Initialize rich console for better CLI output
console = Console()
app = typer.Typer(help="Interact with MCP tools via LLMs", add_completion=False)

# Default config path
DEFAULT_CONFIG_PATH = "mcp_config.json"



class MCPToolsClient:
    def __init__(self, console: Console, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = os.path.expanduser(config_path)
        self.config = self._load_config()
        self.sessions = {}
        self.tools_by_server = {}
        self.llm = None
        self.agent = None
        self.console = console

        # Single exit stack for all stdio and session contexts
        self._exit_stack = AsyncExitStack()

    def _load_config(self) -> dict:
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            self.console.print(f"[yellow]Config file not found at {self.config_path}[/yellow]")
            self.console.print("[yellow]Creating default config file...[/yellow]")
            default_config = {"mcpServers": {}}
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=2)
            return default_config

    async def get_ollama_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:11434/api/tags")
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except (httpx.ConnectError, httpx.RequestError):
            self.console.print("[bold red]Error: Cannot connect to Ollama API.[/bold red]")
            self.console.print("Make sure Ollama is running on http://localhost:11434")
            return []

    async def initialize_servers(self, server_names: List[str] = None) -> bool:
        if not self.config.get("mcpServers"):
            console.print("[bold red]No MCP servers configured.[/bold red]")
            return False

        servers = self.config["mcpServers"]
        server_names = server_names or list(servers.keys())

        for server_name in server_names:
            if server_name not in servers:
                console.print(f"[bold yellow]Warning: Server '{server_name}' not found in config[/bold yellow]")
                continue

            server_config = servers[server_name]
            command = server_config.get("command")
            args = server_config.get("args", [])

            console.print(f"[bold blue]Initializing {server_name}...[/bold blue]")
            server_params = StdioServerParameters(command=command, args=args)

            try:
                # enter both contexts into the same exit stack
                reader, writer = await self._exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                session = await self._exit_stack.enter_async_context(
                    ClientSession(reader, writer)
                )
                await session.initialize()

                self.sessions[server_name] = session
                tools = await load_mcp_tools(session)
                self.tools_by_server[server_name] = tools

                console.print(f"[bold green]✓ {server_name} initialized with {len(tools)} tools[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Error initializing {server_name}: {e}[/bold red]")

        return len(self.sessions) > 0

    async def initialize_llm(self, model_name: str) -> bool:
        try:
            self.llm = ChatOllama(model=model_name)
            return True
        except Exception as e:
            console.print(f"[bold red]Error initializing LLM: {e}[/bold red]")
            return False

    async def create_agent(self) -> bool:
        if not self.llm:
            console.print("[bold red]LLM not initialized.[/bold red]")
            return False

        all_tools = [tool for tools in self.tools_by_server.values() for tool in tools]
        if not all_tools:
            console.print("[bold red]No tools available.[/bold red]")
            return False

        try:
            self.agent = create_react_agent(self.llm, all_tools)
            console.print(f"[bold green]Agent created with {len(all_tools)} tools.[/bold green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Error creating agent: {e}[/bold red]")
            return False

    async def run_interaction(self, query: str):
        """Run an interaction with the agent (and let it use tools)."""
        if not self.agent:
            console.print("[bold red]Agent not initialized.[/bold red]")
            return

        console.print(
            Panel(f"[bold cyan]Sending query:[/bold cyan] {query}", 
                  title="Query", border_style="cyan")
        )

        try:
            # arun() will automatically select & execute any matching tools
            result = await self.agent.ainvoke({"messages": query})
            
            # extract only the final AI explanation or the last tool output
            msgs = result.get("messages", [])
            useful = None

            # look for the last non‐empty AIMessage
            for m in reversed(msgs):
                if type(m).__name__ == "AIMessage":
                    content = getattr(m, "content", "").strip()
                    if content:
                        useful = content
                        break

            # if no AIMessage, fall back to the last tool call output
            if useful is None:
                for m in reversed(msgs):
                    if type(m).__name__ == "ToolMessage":
                        useful = getattr(m, "content", "").strip()
                        break

            # if we still didn’t find anything, show the raw result
            if not useful:
                useful = json.dumps(result, indent=2)

            console.print(
                Panel(f"[bold green]{useful}[/bold green]",
                    title="Response", border_style="green")
            )

        except Exception as e:
            console.print(f"[bold red]Error during interaction: {e}[/bold red]")
            console.print(f"[yellow]Error details: {type(e).__name__}: {str(e)}[/yellow]")


    async def close(self):
        # gracefully exit all stdio_client and session contexts
        await self._exit_stack.aclose()
        console.print("[blue]All MCP server connections closed[/blue]")




async def interactive_cli(client: MCPToolsClient):
    """Run an interactive CLI session."""
    console.print(Panel.fit(
        "[bold cyan]MCP Tools Interactive CLI[/bold cyan]\n"
        "Type 'exit' to quit, 'help' for commands",
        border_style="cyan"
    ))

    while True:
        try:
            command = Prompt.ask("\n[bold blue]mcp-tools>[/bold blue] ")
            
            if command.lower() in ('exit', 'quit'):
                break
                
            elif command.lower() == 'help':
                help_table = Table(title="Available Commands")
                help_table.add_column("Command", style="cyan")
                help_table.add_column("Description")
                help_table.add_row("help", "Show this help message")
                help_table.add_row("exit/quit", "Exit the application")
                help_table.add_row("servers", "List connected servers")
                help_table.add_row("tools", "List available tools")
                help_table.add_row("models", "List available Ollama models")
                help_table.add_row("ask <query>", "Ask the agent a question")
                console.print(help_table)
                
            elif command.lower() == 'servers':
                servers_table = Table(title="Connected Servers")
                servers_table.add_column("Server Name", style="cyan")
                servers_table.add_column("Status")
                servers_table.add_column("Tools")
                
                for server_name in client.sessions:
                    tools_count = len(client.tools_by_server.get(server_name, []))
                    servers_table.add_row(
                        server_name, 
                        "Connected", 
                        str(tools_count)
                    )
                console.print(servers_table)
                
            elif command.lower() == 'tools':
                for server_name, tools in client.tools_by_server.items():
                    tools_table = Table(title=f"Tools for {server_name}")
                    tools_table.add_column("Tool Name", style="cyan")
                    tools_table.add_column("Description")
                    
                    for tool in tools:
                        tools_table.add_row(
                            tool.name,
                            tool.description[:50] + "..." if tool.description and len(tool.description) > 50 else 
                                (tool.description or "No description")
                        )
                    console.print(tools_table)
            
            elif command.lower() == 'models':
                models = await client.get_ollama_models()
                models_table = Table(title="Available Ollama Models")
                models_table.add_column("Model Name", style="cyan")
                
                if models:
                    for model in models:
                        models_table.add_row(model)
                    console.print(models_table)
                else:
                    console.print("[yellow]No models found. Is Ollama running?[/yellow]")
            
            elif command.lower().startswith('ask '):
                query = command[4:].strip()
                if query:
                    await client.run_interaction(query)
                else:
                    console.print("[yellow]Please provide a query after 'ask'[/yellow]")
            
            else:
                # Treat as a direct query to the agent
                await client.run_interaction(command)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")

    console.print("[blue]Closing connections...[/blue]")
    await client.close()
    console.print("[green]Goodbye![/green]")


@app.command()
def run(
    config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c", help="Path to config file"),
    server: List[str] = typer.Option(None, "--server", "-s", help="Specific servers to initialize (defaults to all)"),
    model: str = typer.Option("llama3", "--model", "-m", help="Ollama model to use"),
    query: str = typer.Option(None, "--query", "-q", help="Single query to run (exits after)")
):
    """Run the MCP Tools client."""
    async def _run():
        client = MCPToolsClient(config_path=config)
        
        # Get available models
        models = await client.get_ollama_models()
        if models:
            console.print("[green]Available Ollama models:[/green]")
            for i, m in enumerate(models, 1):
                console.print(f"  {i}. {m}")
                
            # If model not specified or not in available models, let user select
            if model not in models:
                if len(models) == 1:
                    selected_model = models[0]
                    console.print(f"[blue]Using only available model: {selected_model}[/blue]")
                else:
                    console.print("[yellow]Specified model not found or not specified.[/yellow]")
                    idx = IntPrompt.ask(
                        "Select model by number", 
                        default=1,
                        show_choices=False,
                        show_default=True
                    )
                    selected_model = models[min(idx, len(models)) - 1]
            else:
                selected_model = model
        else:
            console.print("[yellow]No models found. Using default: llama3[/yellow]")
            selected_model = model

        # Initialize LLM
        console.print(f"[blue]Initializing LLM with model: {selected_model}[/blue]")
        await client.initialize_llm(selected_model)
        
        # Initialize MCP servers
        if await client.initialize_servers(server):
            # Create agent
            if await client.create_agent():
                if query:
                    # Run single query and exit
                    await client.run_interaction(query)
                    await client.close()
                else:
                    # Start interactive mode
                    await interactive_cli(client)
            else:
                console.print("[bold red]Failed to create agent.[/bold red]")
                await client.close()
        else:
            console.print("[bold red]Failed to initialize any MCP servers.[/bold red]")

    asyncio.run(_run())


if __name__ == "__main__":
    app()