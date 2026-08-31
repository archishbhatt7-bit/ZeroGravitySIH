FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .[api]

EXPOSE 8000

CMD ["uvicorn", "zerogravity.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
