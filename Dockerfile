FROM ubuntu:22.04

WORKDIR /usr/src/app
SHELL ["/bin/bash", "-c"]
RUN chmod 777 /usr/src/app

RUN apt-get -qq update && DEBIAN_FRONTEND="noninteractive" \
    apt-get -qq install -y locales python3 python3-pip \
    libmagic-dev p7zip-full p7zip-rar unzip && locale-gen en_US.UTF-8

ENV LANG="en_US.UTF-8" LANGUAGE="en_US:en"

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
