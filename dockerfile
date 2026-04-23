FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install the package, uvicorn and fastapi for hosted mode
RUN pip install . && pip install uvicorn fastapi

# Expose port 8000 for SSE and Registration UI
EXPOSE 8000

# Set Hosted mode for Docker
ENV MCP_MODE=hosted
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# Start the server directly as a module
CMD ["python", "-m", "datatagger_mcp"]
