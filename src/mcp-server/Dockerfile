FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -e src/mcp-server/

ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

WORKDIR /app/src/mcp-server
CMD ["python", "-m", "iron_mark_profile.server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
