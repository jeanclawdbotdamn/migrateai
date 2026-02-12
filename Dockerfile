FROM python:3.11-slim
LABEL maintainer="@jeanclawbotdamn" description="MigrateAI API Server"

WORKDIR /app
COPY . .

EXPOSE 8000
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8000"]
