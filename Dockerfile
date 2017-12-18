FROM ubuntu:17.04

RUN apt-get update -y
RUN apt-get -y install software-properties-common wget default-jre \
    vim less zip gcc zlib1g-dev libbz2-dev liblzma-dev make git

# Rabix Install
RUN mkdir /usr/local/rabix
RUN wget https://github.com/rabix/bunny/releases/download/v1.0.3/rabix-1.0.3.tar.gz -O /tmp/rabix-1.0.3.tar.gz && \
	tar -xvf /tmp/rabix-1.0.3.tar.gz -C /usr/local/rabix --strip-components=1
ENV PATH=$PATH:/usr/local/rabix

RUN wget https://github.com/samtools/samtools/releases/download/1.6/samtools-1.6.tar.bz2 -O /tmp/samtools.tar.bz2 && \
    mkdir /tmp/samtools/ && \
    tar -xvf /tmp/samtools.tar.bz2 -C /tmp/samtools --strip-components=1 && \
    cd /tmp/samtools && \
    ./configure --prefix=/usr/local/samtools --without-curses && \
    make && \
    make install

RUN wget https://github.com/lh3/bwa/releases/download/v0.7.17/bwa-0.7.17.tar.bz2 -O /tmp/bwa.tar.bz2 && \
    mkdir /usr/local/bwa && \
    tar -xvf /tmp/bwa.tar.bz2 -C /usr/local/bwa --strip-components=1 && \
    cd /usr/local/bwa && \
    make all

RUN wget https://github.com/broadinstitute/picard/releases/download/2.16.0/picard.jar -O /usr/local/bin/picard.jar

ENV PATH=/usr/local/samtools/bin:/usr/local/bwa:$PATH

RUN git clone https://github.com/halilozercan/coinami-workflow.git /coinami-workflow

RUN mkdir /halocoin
WORKDIR /halocoin

ADD requirements.txt /halocoin/requirements.txt
RUN apt-get install python3-pip -y
RUN pip3 install -r requirements.txt

ADD . /halocoin
RUN python3 setup.py install

ENTRYPOINT ["/usr/local/bin/halocoin"]
CMD ["start", "--dir", "/data"]