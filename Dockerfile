FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml setup.py ./
COPY zhihuiti/ zhihuiti/
COPY main.py .

RUN pip install --no-cache-dir -e .

VOLUME /app/data
ENV ZHIHUITI_DB=/app/data/zhihuiti.db
ENV PORT=8080

EXPOSE 8080

CMD ["python", "main.py"]
