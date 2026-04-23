FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install the package and uvicorn for hosted mode
RUN pip install . && pip install uvicorn

# Expose port 8000 for SSE and Registration UI
EXPOSE 8000

# Set Hosted mode for Docker
ENV MCP_MODE=hosted
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# Start the server using the console script
# This will trigger the 'hosted' branch in __main__.py
CMD ["datatagger-mcp"]
