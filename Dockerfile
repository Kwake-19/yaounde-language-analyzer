FROM python:3.11-slim

WORKDIR /app
COPY . .

WORKDIR /app/parser
CMD ["python3", "parser.py"]
