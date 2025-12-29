
### print banner

def jadx_mcp_server_banner() -> str:
    """
    Generate ASCII art banner for server startup.

    Returns:
        str: Multi-line ASCII art banner with project information

    Note:
        Displayed on server startup if terminal supports Unicode characters
    """
    return """
                ░█████    ░███    ░███████   ░██    ░██       ░███    ░██████   ░███     ░███   ░██████  ░█████████  
                  ░██    ░██░██   ░██   ░██   ░██  ░██       ░██░██     ░██     ░████   ░████  ░██   ░██ ░██     ░██ 
                  ░██   ░██  ░██  ░██    ░██   ░██░██       ░██  ░██    ░██     ░██░██ ░██░██ ░██        ░██     ░██ 
                  ░██  ░█████████ ░██    ░██    ░███       ░█████████   ░██     ░██ ░████ ░██ ░██        ░█████████  
            ░██   ░██  ░██    ░██ ░██    ░██   ░██░██      ░██    ░██   ░██     ░██  ░██  ░██ ░██        ░██         
            ░██   ░██  ░██    ░██ ░██   ░██   ░██  ░██     ░██    ░██   ░██     ░██       ░██  ░██   ░██ ░██         
             ░██████   ░██    ░██ ░███████   ░██    ░██    ░██    ░██ ░██████   ░██       ░██   ░██████  ░██         
            
            
            
            Author         -> Jafar Pathan (zinja-coder@github)
            For Issues     -> https://github.com/zinja-coder/jadx-mcp-server
            Server Version -> v6.0.0
            
          """
