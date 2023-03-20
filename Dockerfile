FROM ubuntu:20.04

WORKDIR /usr/src/app
SHELL ["/bin/bash", "-c"]
RUN chmod 777 /usr/src/app

ARG DEBIAN_FRONTEND=noninteractive

ENV LANGUAGE=en_US:en \
    LC_ALL=C.UTF-8 \
    LANG=en_US.UTF-8

RUN apt-get -qq update && apt-get -qq install -y \
    python3 python3-pip locales libmagic-dev \
    p7zip-full p7zip-rar unzip mediainfo ffmpeg && \
    locale-gen en_US.UTF-8

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
