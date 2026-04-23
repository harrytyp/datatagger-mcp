FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install the package and mcp-proxy
RUN pip install . && pip install mcp-proxy

# Expose port 8000 for the proxy
EXPOSE 8000

# Start mcp-proxy to expose the local stdio server as SSE
# --sse-host 0.0.0.0 is now handled correctly by the proxy
CMD ["mcp-proxy", "--sse-host", "0.0.0.0", "--sse-port", "8000", "--", "datatagger-mcp", "--transport", "stdio"]
