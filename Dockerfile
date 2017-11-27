FROM python:alpine

RUN apk --update add git openssh build-base && \
    rm -rf /var/lib/apt/lists/* && \
	rm /var/cache/apk/*

# RUN git clone https://bitbucket.org/halilozercan/halocoin.git
RUN mkdir /halocoin
WORKDIR /halocoin

ADD requirements.txt /halocoin/requirements.txt
RUN pip install -r requirements.txt

ADD . /halocoin
RUN python setup.py install

VOLUME /data

ENTRYPOINT ["/usr/local/bin/halocoin"]
CMD ["start", "--dir", "/data"]