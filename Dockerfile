FROM python:3.6

RUN mkdir -p /usr/srv/scrapy_app
WORKDIR /usr/srv/scrapy_app

RUN apt-get clean \
    && apt-get -y update
RUN apt-get -y install python3-dev \
    && apt-get -y install build-essential
RUN pip install --upgrade pip

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["scrapy", "crawl", "ZhengJi", "-L", "INFO"]