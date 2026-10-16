#!/usr/bin/env python3
"""Start AgentBrain's RAG MCP server for this workspace (the "agentbrain-rag" entry in .mcp.json).

Claude Code starts it over stdio. It finds AgentBrain at AGENTBRAIN_PATH or ~/.agentbrain
and runs scripts/rag/mcp_server.py from the workspace root, so documents it ingests are
tagged with this workspace and rag_ingest may read only folders inside it.
"""
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parent.parent)
    brain = Path(os.environ.get("AGENTBRAIN_PATH") or Path.home() / ".agentbrain")
    server = brain / "scripts" / "rag" / "mcp_server.py"
    if not server.exists():
        print(f"rag_server: no AgentBrain RAG server at {server}. Clone "
              "https://github.com/KxHartl/AgentBrain there (2.6.0 or later) or set AGENTBRAIN_PATH.",
              file=sys.stderr)
        return 1
    return subprocess.call([sys.executable, str(server)], cwd=root)


if __name__ == "__main__":
    sys.exit(main())
