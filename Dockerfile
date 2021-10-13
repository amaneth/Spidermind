FROM python:3.8-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /crawler
WORKDIR /crawler

COPY . /crawler

RUN apt-get update
RUN apt-get -y install gcc
RUN pip install --upgrade pip
RUN pip install -r /crawler/requirements.txt
RUN python -m nltk.downloader punkt
