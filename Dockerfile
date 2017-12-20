FROM halilozercan/coinami:latest

RUN git clone -b coinami --single-branch https://github.com/halilozercan/halocoin.git /halocoin
WORKDIR /halocoin

RUN pip3 install -r requirements.txt
RUN pip3 install .

VOLUME /data
EXPOSE 7001
EXPOSE 7002

ENTRYPOINT ["/usr/local/bin/halocoin"]
CMD ["start", "--dir", "/data"]