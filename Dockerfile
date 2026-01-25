FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cargo \
    cmake \
    curl \
    git \
    libffi-dev \
    libgomp1 \
    libssl-dev \
    ninja-build \
    pkg-config \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    rustc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/Sphere-aae
COPY . .

RUN chmod +x scripts/docker_verify.sh

CMD ["./scripts/docker_verify.sh"]
