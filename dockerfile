FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install dependencies and force update mcp to ensure host/port support
RUN pip install . && pip install --upgrade mcp

# Expose port 8000 for SSE transport
EXPOSE 8000

# Start MCP Server in SSE mode by default in Docker using the official CLI
# This is the most reliable way to bind to 0.0.0.0
CMD ["mcp", "run", "src/datatagger_mcp/api.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
