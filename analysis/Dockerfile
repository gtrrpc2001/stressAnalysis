FROM python:3.11-alpine

# RUN apt update'
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    make \
    g++
RUN pip install --upgrade pip
RUN pip install pymysql aiomysql pytz python-socketio[asyncio_client] numpy neurokit2 scipy
COPY . /app/analysis/
WORKDIR /app/analysis/
ENTRYPOINT ["sh", "-c", "python -u main.py 2>&1 | tee -a ./logFile.txt"]