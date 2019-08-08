# centroFlye

### Version 0.8 (initial release)
## Overview
centroFlye is an algorithm for centromere assembly using long error-prone reads.
Here we show how to apply it for assembling the human X centromere.



## Dependencies

+ C++ 14
+ Python 3.6

### Python packages (preferably latest versions):
+ [Biopython](https://pypi.org/project/biopython/)
+ [Edlib](https://pypi.org/project/edlib/)
+ [Networkx](https://pypi.org/project/networkx/)
+ [Numpy](https://pypi.org/project/numpy/)
+ [Regex](https://pypi.org/project/regex/)

### External software
+ [Flye](https://github.com/fenderglass/Flye) (*v2.5*, tested on commit: `315122d2ff58025aa4c38227239f431490b557ac`)
+ [Noise Cancelling Repeat Finder (NCRF)](https://github.com/makovalab-psu/NoiseCancellingRepeatFinder) (Tested on commit : `758206f1689ad1338cf7a841482dbf12548c337a`)

Please note that all external software by default has to be in your `PATH`.

### Data
+ `<path_to_CHM13>` — path where the T2T ONT reads are located (rel2, Guppy flip-flop 2.3.1, can be downloaded from [here](https://s3.amazonaws.com/nanopore-human-wgs/chm13/nanopore/rel2/rel2.fastq.gz), also see [github](https://github.com/nanopore-wgs-consortium/CHM13)).

## Availability
Final assembly and all intermediate results of the pipeline described below are published at ZENODO. TODO

## Quick start guide

If you want to run the whole centroFlye pipeline with one command, please run
```
./run_all.sh <path_to_CHM13> results 50
```
You can customize the output directory and the number of threads:
```
./run_all.sh <path_to_CHM13> <output directory> <number of threads>
```
All intermediate and final results will then be placed in `<output directory>` (`results` by default).
If you want to start from scratch you can simply remove this directory.

**Required resources**:
+ Storage space: ~150GB (mostly from the first step)
+ Clock time: ~9 hours (mostly recruitment of unique k-mers)
+ RAM: peak usage up to 800GB



## Pipeline
In this manual we go step-by-step demonstrating centroFlye algorithm.
The detailed information about the algorithm can be found in the paper.

Please, run all commands from the root of the repository.
Results of all steps will be stored at `results` directory.

### 1. Recruitment of centromeric reads

We use 50x ultra-long Oxford Nanopore dataset generated by [Telomere2Telomere Consorsium](https://github.com/nanopore-wgs-consortium/CHM13). 
This step is run directly on the reads at the [link](https://s3.amazonaws.com/nanopore-human-wgs/chm13/nanopore/rel2/rel2.fastq.gz).
The following bash script splits the input file in 50 files and runs DXZ1-based recruitment in 50 threads.
DXZ1 is supplied in the current repo at ``supplementary_data/DXZ1_rc.fasta``.
The result of this step is a fasta file with centromeric reads that is stored at `results/centromeric_reads/centromeric_reads.fasta`

From the root of the project run 
```
make -C scripts/read_recruitment
```
and start recruitment (`<path_to_CHM13>` is where the ONT reads are located, see section `Dependencies/Data`):
```
bash scripts/read_recruitment/run_read_recruitment.sh \
       <path_to_CHM13>/rel2.fastq.gz \
       results/centromeric_reads 50 11100000
```
**Required resources**:
+ Storage space: 150GB
+ Clock time: 1 hour
+ RAM: < 50 MB

### 2. Partitioning centromeric reads into units, where each unit represents a HOR copy
At this step we are utilizing centromeric reads from step 1 and run NCRF on them.
The result of this step is the NCRF report on all centromeric reads that is stored at `results/NCRF_rc/report.ncrf`.
The following command uses 50 threads.

If NCRF binary is not in your `PATH` please specify `--ncrf-bin <path_to_NCRF>`.
```
python scripts/run_ncrf_parallel.py \
            --reads results/centromeric_reads/centromeric_reads.fasta \
            -t 50 \
            --outdir results/NCRF_rc \
            --repeat supplementary_data/DXZ1_rc.fasta
```
**Required resources**:
+ Storage space: 1GB
+ Clock time: 10 mins
+ RAM: 20GB

### 3. Recruitment of unique k-mers
At this step we first recruit rare 19-mers and then use distance graph to filter out non-unique 19-mers (details are in the paper).
The following command uses NCRF reports from step 2 and reports unique kmers to `results/recruited_unique_kmers/unique_kmers_min_edge_cov_4.txt`.

```
python scripts/distance_based_kmer_recruitment.py \
        --ncrf results/NCRF_rc/report.ncrf \
        --coverage 32 \
        --min-coverage 4 \
        --outdir results/recruited_unique_kmers
```
**Required resources**:
+ Storage space: 400MB
+ Clock time: 7 hours
+ RAM: **800GB**

### 4. DXZ1 array resolution
At this step we use partitioning of reads into units provided by NCRF at step 2 and unique 19-mer recruited at step 3.
Note, that this step only reports the "placement" of centromeric reads in the (yet unknown) sequence of centromere X (details can be found in the paper).
The resulting placement will be stored at ``results/tr_resolution/read_positions.csv``.

```
python scripts/read_placer.py \
              --ncrf results/NCRF_rc/report.ncrf \
              --genomic-kmers results/recruited_unique_kmers/unique_kmers_min_edge_cov_4.txt \
              --outdir results/tr_resolution
```
**Required resources**:
+ Storage space: < 1MB
+ Clock time: 2 mins
+ RAM: 2GB

### 5. Obtaining a polished version of DXZ1 (DXZ1* in the paper) supported by centromeric reads.
The result of this step is stored at  `results/DXZ1_star/DXZ1_rc_star.fasta`.

```
python scripts/better_consensus_unit_reconstruction.py \
              --reads-ncrf results/NCRF_rc/report.ncrf \
              --unit supplementary_data/DXZ1_rc.fasta \
              --output results/DXZ1_star/DXZ1_rc_star.fasta
```
**Required resources**:
+ Storage space: < 1MB
+ Clock time: 5 mins
+ RAM: 10 GB

### 6. Polishing
At this step we finally polish the constructed cenX sequence.
The result of this step is stored at `results/polishing/final_sequence_4.fasta`.

If Flye binary is not in your `PATH` please specify `--flye-bin <path_to_Flye>`.
```
python scripts/eltr_polisher.py \
              --read-placement results/tr_resolution/read_positions.csv \
              --outdir results/polishing \
              --ncrf results/NCRF_rc/report.ncrf \
              --output-progress \
              --error-mode nano \
              --num-iters 4 \
              --num-threads 50 \
              --unit results/DXZ1_star/DXZ1_rc_star.fasta
```


## Publications
Bzikadze A., Pevzner P.A. centroFlye: Assembling Centromeres with Long Error-Prone Reads, 2019, *bioRxiv* TODO add DOI

## Contacts
Please report any problems to the [issue tracker](https://github.com/seryrzu/centroFlye/issues).
Alternatively, you can write directly to [abzikadze@ucsd.edu](mailto:abzikadze@ucsd.edu).
