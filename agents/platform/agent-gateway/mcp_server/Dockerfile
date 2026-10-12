FROM python:3.11-slim

WORKDIR /app

# Install uv for deterministic, high-speed dependency installation
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

# Copy project manifest and install dependencies
COPY requirements.txt pyproject.toml ./
RUN uv pip install --system --no-cache -r requirements.txt

# Copy package source code into container package path
COPY . /app/mcp_server/

# Cloud Run injects $PORT (defaults to 8080)
ENV PORT=8080
ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["python", "-m", "mcp_server.server", "--host", "0.0.0.0"]
