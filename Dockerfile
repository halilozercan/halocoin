FROM ubuntu:17.04

RUN apt-get update --fix-missing -y
RUN apt-get -y install software-properties-common git python3-pip

RUN mkdir /halocoin
WORKDIR /halocoin

ADD requirements.txt .
RUN pip3 install -r requirements.txt

ADD . /halocoin
RUN pip3 install .

VOLUME /data
EXPOSE 7001
EXPOSE 7002

ENTRYPOINT ["/usr/local/bin/coinamid"]
CMD ["start", "--dir", "/data"]