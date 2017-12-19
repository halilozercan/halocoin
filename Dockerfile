FROM halilozercan/coinami:latest

RUN git clone -b coinami --single-branch https://github.com/halilozercan/halocoin.git /halocoin
WORKDIR /halocoin

RUN pip3 install -r requirements.txt
RUN python3 setup.py install

VOLUME /data

# ENTRYPOINT ["/usr/local/bin/halocoin"]
# CMD ["start", "--dir", "/data"]