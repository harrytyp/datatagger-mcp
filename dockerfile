FROM python:3.11-slim

WORKDIR /app

RUN pip install .

COPY . .

# MCP Server über STDIO starten
CMD ["datatagger-mcp"]
