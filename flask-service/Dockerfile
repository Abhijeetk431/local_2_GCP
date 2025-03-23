# Bitnami Google Cloud SDK image
FROM bitnami/google-cloud-sdk:latest

# Install Python 3.9 and pip
USER root
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
RUN pip3 install --no-cache-dir flask google-cloud-compute

# Work directory
WORKDIR /app
COPY flask_app.py .

ENTRYPOINT []

CMD ["python", "flask_app.py"]