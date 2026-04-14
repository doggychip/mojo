FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml setup.py ./
COPY zhihuiti/ zhihuiti/

RUN pip install --no-cache-dir -e .

VOLUME /app/data
ENV ZHIHUITI_DB=/app/data/zhihuiti.db

EXPOSE 8420

CMD ["python", "-m", "zhihuiti.cli", "dashboard", "--host", "0.0.0.0"]
