import cluster
import meap

import numm
import numpy as np

import pickle

class Tape:
    def __init__(self, path, key="AvgMFCC(13)"):
        self.path = path
        self.key = key

        self._used = set()

        self._clusters = self._get_clusters()
        self._features = self._get_features()
        self._array = self._get_array()

    def getFeatures(self):
        return self._features

    def getSegments(self):
        segs = set()
        for k,vals in self.getClusters().items():
            segs = segs.union(vals)
        return segs

    def _get_features(self):
        a = meap.analysis(self.path)
        out = [X[self.key] for X in a]
        return np.array(out)

    def getClosestUnused(self, seg):
        F = self.getFeatures()
        obs = F[seg.idx]

        closeness = pow(F - obs, 2).sum(axis=1).argsort()
        print closeness.shape

        for idx in closeness:
            if idx not in self._used:
                return self.getCluster(idx)

    def getCluster(self, idx):
        "returns (cluster_key, cluster_idx)"
        for cluster in self._clusters.keys():
            cluster_indices = [X.idx for X in self._clusters[cluster]]
            if idx in cluster_indices:
                return (cluster, cluster_indices.index(idx))

    def getClusters(self):
        return self._clusters

    def _get_clusters(self, nbins=36):
        clusters = cluster.cluster(self.path, key=self.key, nbins=nbins)

        def _name_cluster(idx):
            if idx < 10:
                return str(idx)
            elif idx < nbins:
                return chr(idx - 10 + 65)
            elif idx == nbins:
                return '|'

        out = {}

        for idx,segs in clusters.items():
            out[_name_cluster(int(idx))] = [Seg(self, st, dur, int(aidx)) for st,dur,aidx in segs]

        return out

    def getUnusedClusters(self):
        clusters = self.getClusters()
        for key in clusters:
            clusters[key] = filter(lambda x: not self.isUsed(x), clusters[key])
        return clusters

    def use(self, seg):
        self._used.add(seg.idx)

    def isUsed(self, seg):
        return seg.idx in self._used

    def copy(self):
        t = Tape(self.path)
        t._used = self._used.copy()
        return t

    def _get_array(self):
        return numm.sound2np(self.path)

    def getArray(self):
        return self._array

R=44100                         # XXX: where, ever, do you go?
class Seg:
    def __init__(self, tape, start, duration, idx):
        self.tape = tape
        self.start = start
        self.duration = duration
        self.idx = idx

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

class Composition:
    def __init__(self, rhythms):
        self.rhythms = rhythms

    def append(self, c):
        self.rhythms.append(c)

    def save(self, filename):
        pickle.dump(self, open(filename, 'w'))

    @classmethod
    def fromfile(cls, filename):
        return pickle.load(open(filename))

class Square:
    "cluster-independent alternative to `circle`"
    def __init__(self):
        self.groups = []

    def append(self, group):
        self.groups.append(group)

    def getDuration(self):
        dur = 0
        for g in self.groups:
            dur += sum([x.duration for x in g])
        return dur

    def getArrangement(self):
        timing = {}
        offset = 0

        duration = self.getDuration()

        for group in self.groups:
            if len(group) == 0:
                print 'Warning: empty group'
                continue

            step = (duration - offset) / len(group)

            for idx,seg in enumerate(group):
                # XXX: prevent exact intersections?
                timing[idx * step + offset] = seg

            offset += group[0].duration

        return Arrangement(timing)

class Circle:
    def __init__(self, clusters=None, theta=0, duration=10):
        if clusters is None:
            clusters = {}
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
    def __init__(self, timings=None, fills=None, duration=None):
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
