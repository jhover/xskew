import datetime as dt
import logging
import shutil
import subprocess
import sys

class NonZeroReturnException(Exception):
    """
    Thrown when a command has non-zero return code. 
    """

def setup_logging(level):
    """ 
    Setup logging 

    """
    FORMAT='%(asctime)s (UTC) [ %(levelname)s ] %(name)s %(filename)s:%(lineno)d %(funcName)s(): %(message)s'
    logging.basicConfig()
    logger = logging.getLogger()
    streamHandler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(FORMAT)
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.setLevel(level)


def run_command(cmd):
    """
    cmd should be standard list of tokens...  ['cmd','arg1','arg2'] with cmd on shell PATH.
    
    """
    cmdstr = " ".join(cmd)
    logging.info(f"running command: {cmdstr} ")
    start = dt.datetime.now()
    cp = subprocess.run(cmd, 
                    text=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT)
    end = dt.datetime.now()
    elapsed =  end - start
    logging.debug(f"ran cmd='{cmdstr}' return={cp.returncode} {elapsed.seconds} seconds.")
    
    if cp.stderr is not None:
        logging.debug(f"got stderr: {cp.stderr}")
    if cp.stdout is not None:
        logging.debug(f"got stdout: {cp.stdout}")
    
    if str(cp.returncode) == '0':
        logging.info(f'successfully ran {cmdstr}')
        return(cp.stderr, cp.stdout,cp.returncode)
    else:
        logging.warn(f'non-zero return code for cmd {cmdstr}')

        
def fasterq_dump(infile, outdir, nthreads, tempdir ):
    
    cmd = ['fasterq-dump', 
    '--split-files',
    '--include-technical',
    '--force', 
    '--threads', nthreads,
    '--outdir', outdir,
    '-t', tempdir,
    '--log-level', 'debug', 
    infile]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))


def star_nowasp(end1, end2, outprefix, outtemp, nthreads, genomedir):
            
    cmd = ['STAR',
       '--readFilesIn', end1, end2, 
       '--outFileNamePrefix', outprefix,
       '--outTmpDir', outtemp, 
       '--runThreadN', nthreads,
       '--genomeDir', genomedir, 
       '--twopassMode Basic',
       '--twopass1readsN -1',
       '--outSAMtype BAM Unsorted', 
       '--quantMode GeneCounts'
       ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {end1}/{end2} input files.')
        logging.error(traceback.format_exc(None))
    finally:
        shutil.rmtree(f'{outprefix}_STARgenome')
        shutil.rmtree(f'{outprefix}_STARpass1')    


def samtools_sort(infile, outfile, memory, nthreads):
    cmd = ['samtools',
           'sort',
           '-m', f'{memory}M',
           '-o', outfile, 
           '-O', 'bam', 
           '-@', f'{nthreads}',
           infile
       ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))


def samtools_index(infile, nthreads):
    cmd = ['samtools',
           'index',
           '-@', f'{nthreads}',
           infile,
       ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))

def samtools_view_region(infile, outfile, region):
    cmd = ['samtools',
           'view',
           '-b', infile,
           '-o', outfile,
           region
       ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))    
    
    
def samtools_view_quality(infile, outfile, quality):
    cmd = ['samtools',
           'view',
           '-q', quality, 
           '-b', infile,
           '-o', outfile,
       ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))        

def gatk_arrg(infile, outfile):
    " gatk AddOrReplaceReadGroups -I={input.xfiltbam} -O={params.chrom}.rg.bam -SO=coordinate "
    "-RGID=id -RGLB=library -RGPL=platform -RGPU=machine -RGSM=sample && "
    cmd = [ 'gatk',
            'AddOrReplaceReadGroups',
            '-I', infile,
            '-O' , outfile,
            '-SO', 'coordinate',
            '-RGID', 'id',
            '-RGLB', 'library',
            '-RGPL', 'platform',
            '-RGPU', 'machine',
            '-RGSM', 'sample'
        ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))    

def gatk_md(infile, outfile, metrics):
    " gatk MarkDuplicates -I={params.chrom}.rg.bam -O={params.chrom}.dedupped.bam -CREATE_INDEX=true " 
    " -VALIDATION_STRINGENCY=SILENT -M=output.metrics && "
    
    cmd = [ 'gatk',
           'MarkDuplicates',
           '-I', infile, 
           '-O', outfile,
           '-CREATE_INDEX', 'true',
           '-VALIDATION_STRINGENCY', 'SILENT',
           '-M', metrics,
           ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))

def gatk_sncr(infile, outfile, genome ):
    " gatk SplitNCigarReads -R {params.gdir}/GRCh38.p7.genome.fa -I {params.chrom}.dedupped.bam " 
    " -O {params.chrom}.split.filtered.bam --java-options '-XXgcThreads:2 -XX:ConcGCThreads ' && "
    cmd = [ 'gatk', 'SplitNCigarReads',
           '-R', genome,
           '-I', infile, 
           '-O', outfile, 
           #'--java-options', "'-XXgcThreads:2 -XX:ConcGCThreads'" 
           ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))           
        
    
def gatk_htc(infile, outfile, genome, interval):
    " gatk HaplotypeCaller -R {params.gdir}/GRCh38.p7.genome.fa -L chr{params.chrom} " 
    " -I {params.chrom}.split.filtered.bam --dont-use-soft-clipped-bases -stand-call-conf 0.0 "
    " -O {params.chrom}.filtered.vcf && "    
    cmd = [ 'gatk',
           'HaplotypeCaller',
           '-R', genome,
           '-I', infile, 
           '-O', outfile,  
           '--dont-use-soft-clipped-bases',
           '-stand-call-conf', '0.0',
           ]
    try:
        run_command(cmd)
    except NonZeroReturnException as nzre:
        logging.error(f'problem with {infile}')
        logging.error(traceback.format_exc(None))


def gatk_sv(infile, outfile, genome, interval):
    " gatk SelectVariants -R {params.gdir}/GRCh38.p7.genome.fa -L chr{params.chrom} "
    "-V {params.chrom}.filtered.vcf -O {params.chrom}.snps.vcf -select-type SNP &&"


