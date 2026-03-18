FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/generated \
    --grpc_python_out=./src/generated \
    ./proto/flight.proto

CMD ["python", "-m", "src.main"]
