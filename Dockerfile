FROM python:3.11-slim

# Print output immediately (no buffering) so it shows up in docker compose logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY . .

# Run from the project root; parser.py finds lexer/ and data/ via its own path
CMD ["python3", "parser/parser.py"]
