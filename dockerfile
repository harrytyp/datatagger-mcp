FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install .

# Expose port 8000 for SSE transport
EXPOSE 8000

# Start MCP Server in SSE mode by default in Docker
CMD ["datatagger-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
