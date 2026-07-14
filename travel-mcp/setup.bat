@echo off
echo Creating virtual environment...
python -m venv .venv
echo Installing dependencies...
.venv\Scripts\pip install -r requirements.txt
echo.
echo Setup complete! MCP server is ready.
echo The .mcp.json in the project root points to this venv automatically.
