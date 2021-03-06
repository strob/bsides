"Run the MEAPSoft Analyzer"

import chop

import subprocess
import glob
import re

MEAP_PATH = "lib/MEAPsoft-2.0.beta/bin/MEAPsoft.jar"

def run(cmd):
    p = subprocess.Popen(cmd)
    p.wait()

def analyze(src):
    f_paths = []
    for path in chop.chopped(src):
        f_path = path + ".feat"
        f_paths.append(f_path)
        # Segment
        cmd = ["java", "-cp",
               MEAP_PATH,
               "com.meapsoft.Segmenter",
               "-o", f_path,
               "-d",            # "old-style" onset detector
               "-0",            # start at 0
               path]
        run(cmd)

        # Features
        cmd = ["java", "-cp",
               MEAP_PATH,
               "com.meapsoft.FeatExtractor",
               "-f", "AvgMelSpec",
               "-f", "SpectralStability",
               "-f", "AvgTonalCentroid",
               "-f", "AvgSpecFlatness",
               "-f", "AvgChroma",
               "-f", "AvgPitch",
               "-f", "AvgMFCC",
               "-f", "RMSAmplitude",
               f_path]
        run(cmd)
    return f_paths

def _ncols(key):
    parentheticals = re.findall(r"\((\d+)\)", key)
    if len(parentheticals) == 1:
        return int(parentheticals[0])
    elif len(parentheticals) > 1:
        raise AssertionError("too many parentheticals")
    return 1

def _load(meap):
    lines = open(meap).read().split('\n')
    keys = lines[0].split('\t')

    segs = []
    for l in lines[1:]:
        valid = True
        d = {}
        cols = l.split('\t')
        idx = 0
        for key in keys:
            ncols = _ncols(key)
            key = key.strip()

            d[key] = cols[idx:idx+ncols]
            if not key.startswith('#'):
                d[key] = [float(x) for x in d[key]]
            if ncols == 1:
                if len(d[key]) > 0:
                    d[key] = d[key][0]
                else:
                    valid = False
            idx += ncols
        if valid:
            segs.append(d)
    return segs

def _combine(analyses, t=300):
    out = []
    for idx,analysis in enumerate(analyses):
        for X in analysis:
            X["onset_time"] += t*idx
            out.append(X)
    return out

def analysis(src):
    f_paths = glob.glob(src + '*.feat')
    if len(f_paths) == 0:
        f_paths = analyze(src)

    return _combine([_load(X) for X in f_paths])
    

if __name__=='__main__':
    import sys
    for p in sys.argv[1:]:
        print analysis(p)
