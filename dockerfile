FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install .

# MCP Server über STDIO starten
CMD ["datatagger-mcp"]
