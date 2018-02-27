FROM coinami/reference

RUN apt-get update -y --fix-missing
RUN apt-get -y install software-properties-common wget \
    zip gcc zlib1g-dev bzip2 libbz2-dev liblzma-dev make python3

# Samtools
RUN wget https://github.com/samtools/samtools/releases/download/1.6/samtools-1.6.tar.bz2 -O /tmp/samtools.tar.bz2 && \
    mkdir /tmp/samtools/ && \
    tar -xvf /tmp/samtools.tar.bz2 -C /tmp/samtools --strip-components=1 && \
    cd /tmp/samtools && \
    ./configure --prefix=/usr/local/samtools --without-curses && \
    make && \
    make install
ENV PATH=/usr/local/samtools/bin:$PATH

# Bwa
RUN wget https://github.com/lh3/bwa/releases/download/v0.7.17/bwa-0.7.17.tar.bz2 -O /tmp/bwa.tar.bz2 && \
    mkdir /usr/local/bwa && \
    tar -xvf /tmp/bwa.tar.bz2 -C /usr/local/bwa --strip-components=1 && \
    cd /usr/local/bwa && \
    make all
ENV PATH=/usr/local/bwa:$PATH

RUN mkdir /coinami
WORKDIR /coinami
ADD executor.sh /coinami/executor.sh
ADD decompressor /coinami/decompressor
RUN gcc -o /usr/bin/decompress decompressor/main.c -lz
RUN chmod a+x executor.sh

VOLUME /input
VOLUME /output

ENTRYPOINT ["sh", "/coinami/executor.sh"]
