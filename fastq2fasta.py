#!/usr/bin/env python
desc="""Convert FastQ to FASTA.

Note, reads are reported in arbitrary order due to multiprocessing! 
"""
epilog="""
l.p.pryszcz+git@gmail.com
Barcelona, 10/05/2013
"""
 
import argparse, gzip, os, sys
from datetime import datetime
from multiprocessing import Pool

def init_args(*args):
    global minLen, qualityTh, offset
    minLen, qualityTh, offset = args
                
def worker(read):
    """ """
    global minLen, qualityTh, offset
    id, seq, spacer, quals = read
    #cut @ Ns
    if 'N' in seq:
        iN = seq.index('N')
        if iN < minLen:
            return 0, ''
        seq = seq[:iN]
  	
    #cut @ low quality
    if qualityTh:
        qualsL = []
        for i in range(len(seq)):
            q = quals[i]
            if ord(q)-offset < qualityTh:
                break
            qualsL.append(q)
        #skip if too short	
        if i < minLen:
            return 0, ''
        #trim seq
        seq = seq[:i+1]

    #store fasta "\n".join(seq[i:i+100] for i in range(0,len(seq),100))
    return len(seq), '>%s\n%s\n' % (id[1:], seq)

def fastq2rec(handle):
    """Yield fastq records as tuple"""
    read = []
    for line in handle:
        #skip empty lines
        line = line.strip()
        if not line:
            continue
        #store read info
        read.append(line)
        #report reads
        if len(read)==4:
            yield read
            read = []

def fastq2fasta(handle, output, minLen, qualityTh, offset, bases, nproc=4, verbose=1):
    """ """
    p = Pool(nproc, initializer=init_args, initargs=(minLen, qualityTh, offset))
    #parse fastq
    i = totsize = 0
    for i, (seqlen, fasta) in enumerate(p.imap_unordered(worker, fastq2rec(handle), chunksize=100), 1):
        if not i%1e5:
            sys.stderr.write(' %s \r'%i)
        if not seqlen:
            continue
        # store
        output.write(fasta)
        totsize += seqlen
        # process up to bases
        if totsize > bases:
            p.terminate()
            break
    sys.stderr.write('Reported %s bases from %s reads.\n'%(totsize, i))
    
def main():

    usage   = "%(prog)s [options] -v " 
    parser  = argparse.ArgumentParser(usage=usage, description=desc, epilog=epilog)

    parser.add_argument("-v", action="store_true", dest="verbose", default=False)
    parser.add_argument('--version', action='version', version='1.0')   
    parser.add_argument("-i", "--input",  default=sys.stdin, 
                        help="input file [stdin]")
    parser.add_argument("-o", "--output", default=sys.stdout, 
                        help="output file [stdout]")
    parser.add_argument("-l", "--minLen", default=0, type=int,
                        help="skip reads shorter than [%(default)s]" )
    parser.add_argument("-q", "--qualityTh", default=0, type=int,
                        help="read is clipped @ first base having PHRED quality lower than [%(default)s]" )
    parser.add_argument("--offset", default=33, type=int, 
                        help="quality encoding; PHRED+33 (Sanger) or PHRED+64 (Illumina/Solexa) [%(default)s]")
    parser.add_argument("-b", "--bases", default=float('inf'), type=float,
                        help="process up to b bases [%(default)s]" )
    parser.add_argument("-t", "--threads", default=4, type=int, 
                        help="no. of cores to use [%(default)s]" )

    o = parser.parse_args()

    fastq2fasta(o.input, o.output, o.minLen, o.qualityTh, o.offset, o.bases, o.threads, o.verbose)

if __name__=='__main__': 
    t0=datetime.now()
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write("\nCtrl-C pressed!      \n")
    except IOError as e:
        sys.stderr.write("I/O error({0}): {1}\n".format(e.errno, e.strerror))
    dt=datetime.now()-t0
    sys.stderr.write("#Time elapsed: %s\n" % dt)
