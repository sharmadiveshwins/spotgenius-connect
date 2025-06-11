# Stage 1: Build dependencies
FROM ubuntu:20.04 as builder

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy your Python application code
COPY ./app /workspace/app
COPY requirements.txt /workspace/app/requirements.txt
# Stage 2: Final runtime image
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

# Copy the built dependencies from the builder stage
COPY --from=builder /workspace /workspace
WORKDIR /workspace
RUN pip install --no-cache-dir -r app/requirements.txt

COPY ./app/scripts/run_huey.sh /workspace/app/scripts/run_huey.sh
RUN chmod +x /workspace/app/scripts/run_huey.sh

EXPOSE 8001
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "3"]
