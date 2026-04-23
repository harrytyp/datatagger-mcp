FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install dependencies and force update mcp to ensure host/port support
RUN pip install . && pip install --upgrade mcp

# Expose port 8000 for SSE transport
EXPOSE 8000

# Start MCP Server in SSE mode by default in Docker using the official CLI
# Using run-sse which is the dedicated command for SSE transport
CMD ["mcp", "run-sse", "src/datatagger_mcp/api.py", "--host", "0.0.0.0", "--port", "8000"]
