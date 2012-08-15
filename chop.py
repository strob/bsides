# MEAPSoft seems to use a lot of memory in feature extraction.
# We will cut the tape sides into smaller chunks, and then analyze.

import numm
import numpy as np
import glob

R = 44100

def chop(src, nsecs=300):
    "Return a list of output files that have been written to disk"
    # XXX: May be nice to split on silence, instead of seconds.
    acc = np.zeros((nsecs*R,2), dtype=np.int16)
    idx = 0
    count = 0
    paths = []
    for chunk in numm.sound_chunks(src):
        if idx + len(chunk) <= len(acc):
            acc[idx:idx+len(chunk)] = chunk
            idx += len(chunk)
        else:
            nframes = len(acc) - idx
            acc[idx:] = chunk[:nframes]
            path = src + '.%06d.wav' % (count)
            numm.np2sound(acc, path)
            count += 1
            paths.append(path)

            acc[:] = 0
            acc[:len(chunk)-nframes] = chunk[nframes:]

            idx = len(chunk)-nframes

    if idx < len(acc):
        remainder = acc[:idx]
        path = src + '.%06d.wav' % (count)
        numm.np2sound(remainder, path)
        paths.append(path)
        
    return paths

def chopped(src):
    paths = glob.glob(src + '.0*.wav')
    if len(paths) == 0:
        return chop(src)
    else:
        return paths

if __name__=='__main__':
    import sys
    for p in sys.argv[1:]:
        print chopped(p)
