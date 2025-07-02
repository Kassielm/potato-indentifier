FROM python:3.10-slim
WORKDIR /usr/src/app
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    procps \
    usbutils \
    libusb-1.0-0 \
    udev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pylon-*_setup.tar.gz .

RUN yes | ( \
    mkdir -p /opt/pylon && \
    mkdir ./pylon_setup && \
    tar -C ./pylon_setup -xzf ./pylon-*_setup.tar.gz && \
    cd ./pylon_setup && \
    tar -C /opt/pylon -xzf ./pylon-*.tar.gz && \
    cd /usr/src/app && \
    rm -rf ./pylon_setup ./pylon-*_setup.tar.gz && \
    chmod 755 /opt/pylon && \
    /opt/pylon/share/pylon/setup-usb.sh || true \
  )

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/

CMD ["python", "src/main.py"]