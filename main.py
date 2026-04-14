"""Entrypoint for container platforms that expect /app/main.py."""

import os
import uvicorn
from zhihuiti.api import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8420))
    uvicorn.run(app, host="0.0.0.0", port=port)
