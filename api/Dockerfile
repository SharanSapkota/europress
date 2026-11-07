FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Rahti runs containers as a random non-root user: make the app dir group-writable
RUN chgrp -R 0 /app && chmod -R g=u /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
