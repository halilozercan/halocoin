#include <stdio.h>
#include <zlib.h>
#include <stdlib.h>

int main(int argc, char** argv) {
	char* filename = argv[1];
	gzFile f = gzopen(filename, "r");
	if(argc == 3) {
		chdir(argv[2]);
	}
	char json[1000];
	char* buf = gzgets(f, json, 1000);
	FILE* g = fopen("coinami.job.json", "w");
	fprintf(g, "%s", json);
	fclose(g);

	int counter = 0;
	FILE* reads1 = fopen("reads.1.fq", "w");
	FILE* reads2 = fopen("reads.2.fq", "w");

	while((buf = gzgets(f, buf, 150)) != NULL) {
		if(counter < 4) {
			fprintf(reads1, "%s", buf);
		}
		else if(counter < 8) {
			fprintf(reads2, "%s", buf);	
		}
		counter++;
		if(counter == 8) counter = 0;
	}
	fclose(reads1);
	fclose(reads2);

	gzclose(f);
}
