import cluster

import numm
import numpy as np

class Tape:
    def __init__(self, path):
        self.path = path
        self._used = set()

    def getClusters(self, nbins=36, key="AvgMFCC(13)"):
        clusters = cluster.cluster(self.path, key=key, nbins=nbins)

        def _name_cluster(idx):
            if idx < 10:
                return str(idx)
            elif idx < nbins:
                return chr(idx - 10 + 65)
            elif idx == nbins:
                return '|'

        out = {}

        for idx,segs in clusters.items():
            out[_name_cluster(int(idx))] = [Seg(self, st, dur) for st,dur in segs]

        return out

    def getUnusedClusters(self):
        clusters = self.getClusters()
        for key in clusters:
            clusters[key] = filter(lambda x: x not in self._used, clusters[key])
        return clusters

    def use(self, seg):
        self._used.add(seg)

    def copy(self):
        t = Tape(self.path)
        t._used = self._used.copy()
        return t

    def getArray(self):
        return numm.sound2np(self.path)

R=44100                         # XXX: where, ever, do you go?
class Seg:
    def __init__(self, tape, start, duration):
        self.tape = tape
        self.start = start
        self.duration = duration

    @property
    def st_idx(self):
        return int(self.start * R)
    @property
    def end_idx(self):
        return int((self.start + self.duration) * R)

"""
A Circle is the highest-level composition structure,
which expands into an Arrangement,
& from there into a Sequence.
"""

class Circle:
    def __init__(self, clusters=None, theta=0, duration=10):
        self.clusters = clusters # {ClusterID: NSegs}
        self.theta = theta
        self.duration = duration

    def getNSegs(self, clusterId):
        return self.clusters.get(clusterId, 0)
    def setNSegs(self, clusterId, nsegs):
        self.clusters[clusterId] = nsegs

    def getArrangement(self, tape):
        """Naive first-pass:
        Equally space each cluster within duration, with marginal offsets
        """
        offset = 0

        fullclusters = tape.getClusters() # XXX: scarcity, etc.

        timings = {}

        for clusterid, nsegs in self.clusters.items():
            dur = self.duration - offset

            segs = fullclusters[clusterid][:nsegs]

            if len(segs) == 0:
                print 'warning: no segs in cluster', clusterid
                continue

            step = dur / len(segs)

            for idx, seg in enumerate(segs):
                timings[offset + step*idx] = seg

            offset += segs[0].duration

        return Arrangement(timings)

class Arrangement:
    def __init__(self, timings=None, fills=None, duration=10):
        self.timings = timings
        self.fills = fills
        self.duration = duration

    def getSequence(self):
        """Naive first pass:
        No dithering or filling -- just splice in segments in order.
        """

        return Sequence([self.timings[X] for X in sorted(self.timings)])


class Sequence:
    def __init__(self, segs):
        self.segs = segs

    def getArray(self):
        if len(self.segs) == 0:
            print 'warning: no segments'
            return (2**14 * np.sin(np.linspace(0, 2*np.pi*440, 44100))).astype(np.int16)

        # XXX: Assume that all segments are from the same tape (?)
        arr = self.segs[0].tape.getArray()

        return np.concatenate([arr[X.st_idx:X.end_idx] for X in self.segs])
