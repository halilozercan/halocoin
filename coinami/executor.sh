#!/bin/bash
cd /input

echo "Starting decompressing..."
decompress job.cfq.gz
echo "Finished decompressing..."

num_of_threads=$(python3 -c "import json; a=json.load(open('config.json')); print(a['threads'])")

echo "Starting BWA..."
bwa mem -t $num_of_threads /reference/human_g1k_v37.fasta reads.1.fq reads.2.fq > output.sam
echo "Finished bwa..."\n

echo "Starting Samtools View..."
samtools view -@ $num_of_threads -bS -o output.bam output.sam
echo "Finished Samtools View..."

echo "Starting Samtools Sort..."
samtools sort -@ $num_of_threads output.bam -o output.sorted
echo "Finished Samtools Sort..."

echo "Starting MarkDuplicates..."
java -jar /usr/local/bin/picard.jar MarkDuplicates I=output.sorted O=output.markdup.bam M=duplicate_metrics.txt
echo "Finished MarkDuplicates..."

echo "Starting Samtools Index..."
samtools index -@ $num_of_threads output.markdup.bam
echo "Finished Samtools Index..."

echo "Starting Zip..."
zip result.zip output.markdup.bam output.markdup.bam.bai
echo "Finished Zip..."
