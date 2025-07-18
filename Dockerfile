FROM python:3.9-slim
WORKDIR /usr/src/app
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    procps \
    usbutils \
    libgles2 \
    libusb-1.0-0 \
    libglib2.0-0 \
    libxext6 \
    libxrender1 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    udev \
    qtwayland5 \
    libgl1-mesa-glx \
    libegl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* && \
    ldconfig && \
    usermod -aG video root

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