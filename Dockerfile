FROM python:3.12-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*


# Set up Chrome, Selenium and other Python libraries
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app code
COPY src /app
WORKDIR /app

# Keep the container running
CMD ["tail", "-f", "/dev/null"]
