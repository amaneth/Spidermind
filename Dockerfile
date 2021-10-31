FROM python:3.8-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /crawler
WORKDIR /crawler


RUN apt-get update
RUN apt-get -y install gcc
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m nltk.downloader punkt
COPY . /crawler

