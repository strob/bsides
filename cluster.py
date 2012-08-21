# Combine `feat` files and cluster into 15 bins.

import numpy as np
from scipy.cluster.vq import kmeans, vq
import json
import numm

import meap

import os


def cluster(src, key="AvgTonalCentroid(6)", nbins=15, min_volume=-30):
    jsonfile = "%s-%s-%d.json" % (src, key, nbins)
    if os.path.exists(jsonfile):
        return deserialize(jsonfile)

    analyses = meap.analysis(src)

    segs = []
    features = []
    rms = []
    for idx, analysis in enumerate(analyses):
        for X in analysis:
            segs.append((X["onset_time"] + 300 * idx, X["chunk_length"]))
            features.append(X[key])
            rms.append(X["RMSAmplitude(1)"])

    rms = np.array(rms)
    features = np.array(features)
    segs = np.array(segs)

    too_quiet = rms < min_volume

    quiet_segs = segs[too_quiet]

    features = features[np.invert(too_quiet)]
    segs = segs[np.invert(too_quiet)]

    codebook, distortion = kmeans(features, nbins)

    clusters, distance = vq(features, codebook)

    out = {}
    for i in range(nbins + 1):
        out[i] = []

    for idx, cluster in enumerate(clusters):
        out[cluster].append(segs[idx].tolist())

    out[nbins] = quiet_segs.tolist()

    serialize(out, jsonfile)
    
    return out

def serialize(clusters, filename):
    json.dump(clusters, open(filename, 'w'))
def deserialize(filename):
    return json.load(open(filename))

def wave(src_np, clusters, outpattern, R=44100):
    for idx, segs in clusters.items():
        segchunks = [src_np[int(R*st):int(R*(st+dur))] for (st, dur) in segs]
        if len(segchunks) == 0:
            print 'zero-length cluster', idx
            continue
        segchunks = np.concatenate(segchunks)
        numm.np2sound(segchunks, outpattern % (idx))

if __name__=='__main__':
    import sys

    keys = ["AvgTonalCentroid(6)", "AvgMFCC(13)", "AvgChroma(12)"]
    nclusters = 36

    for src in sys.argv[1:]:
        src_np = None

        for key in keys:
            jsonfile = "%s-%s-%d.json" % (src, key, nclusters)
            if os.path.exists(jsonfile):
                continue

            if src_np is None:
                src_np = numm.sound2np(src)

            clusters = cluster(src, key=key, nbins=nclusters)
            wave(src_np, clusters, "%s-%s-%d-%%06d.wav" % (src, key, nclusters))
