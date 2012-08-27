import cluster
import meap
from wolftones import wolfcut

import numm
import numpy as np

import pickle

class Tape:
    def __init__(self, path, key="AvgMFCC(13)", nbins=36):
        self.path = path
        self.key = key

        self._used = set()

        self._features = self._get_features()
        self._segments = self._get_segments()
        self._clusters = self._get_clusters(nbins=nbins)

    def getFeatures(self):
        return self._features

    def _get_segments(self):
        a = meap.analysis(self.path)
        return [Seg(X["onset_time"], X["chunk_length"], idx)
                for idx,X in enumerate(a)]

    def getSegments(self):
        return self._segments

    def _get_features(self):
        a = meap.analysis(self.path)
        out = [X[self.key] for X in a]
        return np.array(out)

    def orderBySegment(self, seg):
        F = self.getFeatures()
        obs = F[seg.idx]

        closeness = pow(F - obs, 2).sum(axis=1).argsort()

        return [self._segments[X] for X in closeness]

    def getClosestUnused(self, seg):
        F = self.getFeatures()
        obs = F[seg.idx]

        closeness = pow(F - obs, 2).sum(axis=1).argsort()

        for idx in closeness:
            if idx not in self._used:
                return self.getCluster(idx)

        print 'Warning: everything is used'

    def getCluster(self, idx):
        "returns (cluster_key, cluster_idx)"
        for cluster in self._clusters.keys():
            cluster_indices = [X.idx for X in self._clusters[cluster]]
            if idx in cluster_indices:
                return (cluster, cluster_indices.index(idx))

        print 'Warning: cluster not found for', idx, len(self._segments)

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
            out[_name_cluster(int(idx))] = [self._segments[int(aidx)] for st,dur,aidx in segs]

        return out

    def getClusters(self):
        return self._clusters

    def getUnusedClusters(self):
        clusters = self.getClusters()
        for key in clusters:
            clusters[key] = filter(lambda x: not self.isUsed(x), clusters[key])
        return clusters

    def use(self, seg):
        self._used.add(seg.idx)

    def unuse(self, seg):
        self._used.remove(seg.idx)

    def isUsed(self, seg):
        return seg.idx in self._used

    def copy(self):
        t = Tape(self.path)
        t._used = self._used.copy()
        return t

    def _get_array(self):
        return numm.sound2np(self.path)

    def getArray(self):
        if not hasattr(self, "_array"):
            self._array = self._get_array()

        return self._array

R=44100                         # XXX: where, ever, do you go?
class Seg:
    def __init__(self, start, duration, idx):
        self.start = start
        self.duration = duration
        self.idx = idx

    @property
    def st_idx(self):
        return int(self.start * R)
    @property
    def end_idx(self):
        return int((self.start + self.duration) * R)

    @property
    def nframes(self):
        return self.end_idx - self.st_idx

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
        self.theta = 0          # [0,1]
        self._fills = set()

    def append(self, group):
        self.groups.append(group)

    def remove(self, idx):
        g = self.groups.pop(idx)

        # Adust ``fill'' designation
        if idx in self._fills:
            self._fills.remove(idx)
        np_fills = np.array(list(self._fills))
        np_fills[np_fills > idx] -= 1
        self._fills = set(np_fills.tolist())

        return g

    def isFill(self, idx):
        return idx in self._fills
    def addFill(self, idx):
        self._fills.add(idx)
    def removeFill(self, idx):
        self._fills.remove(idx)

    def setTheta(self, t):
        self.theta = t
    def getLines(self):
        """We scatter each group evenly between a start and end
        offset, where both offsets for each group are determined by a
        single `theta,' between 0 and 1.

        To map theta (deterministically but non-trivially) to 2*N
        offsets, we use each group's index, duration, percentage, and
        nsegs as a sort of locally-sensitive hash along with theta.

        As a first pass, let's try, for no particular reason:

        o1 = abs ( cos(pi * theta * (index + 1) + duration) )
        o2 = abs ( cos(nsegs * theta / percentage) )
        """
        nlines = len(self.groups) - len(self._fills)
        idx = 0
        lines = []
        for g_i,group in enumerate(self.groups):
            if self.isFill(g_i):
                continue
            idx += 1

            duration = sum([X.duration for X in group])
            percentage = duration / self.getDuration()
            nsegs = len(group)

            o1 = abs( np.cos( np.pi * self.theta * idx + duration ) )
            o2 = abs( np.cos( nsegs * self.theta / percentage ) )

            lines.append(( o1, o2 ))
        return lines

    def getDuration(self):
        dur = 0
        for g in self.groups:
            dur += sum([x.duration for x in g])
        return dur

    def getArrangement(self):
        timing = {}

        duration = self.getDuration()
        lines = self.getLines() # XXX

        fills = []

        for idx,group in enumerate(self.groups):
            if self.isFill(idx):
                fills.extend(group)
                continue

            o1, o2 = lines.pop(0)
            start = o1 * duration
            ndur = o2 * (duration - start)
            step = ndur / len(group)

            for idx,seg in enumerate(group):
                t = start + idx * step
                # Avoid exact overlaps.
                while timing.has_key(t):
                    print 'Warning: overlap', t
                    t += np.random.random() * 0.002 - 0.001

                timing[t] = seg

        return Arrangement(timing, fills=fills, duration=self.getDuration())

class Arrangement:
    def __init__(self, timings=None, fills=None, duration=None, tones=None):
        self.timings = timings
        self.fills = fills
        self.duration = duration
        self.tones = tones

    def getArray(self, tape):
        """Start with insertions. Override on overlap while storing
        the remainder in a `fills' buffer. Make wolftones!
        """
        print 'getArray'
        seq = []                # (start, seg)
        newfills = []
        for t in sorted(self.timings.keys()):
            print t
            seg = self.timings[t]

            # Check for overlaps with the last segment, and occlude it
            # if necessary.
            if len(seq) > 0 and seq[-1][0] + seq[-1][1].duration > t:
                laststart, lastseg = seq.pop()

                newlastdur = t - laststart
                newlastseg = Seg(lastseg.start, newlastdur, -1)
                seq.append((laststart, newlastseg))
                lastsegfill = Seg(lastseg.start + newlastdur,
                                  lastseg.duration - newlastdur, 
                                  -1)
                newfills.append(lastsegfill)

            seq.append((t, seg))

        print 'seq', seq
        # check if we've overflowed duration
        if len(seq) > 0:
            laststart, lastseg = seq[-1]
            if laststart + lastseg.duration > self.duration:
                print 'trimming last seg'
                seq.pop()
                newlastdur = self.duration-lastseg.start
                seq.append((laststart, Seg(lastseg.start, newlastdur,-1)))
                newfills.append(Seg(lastseg.start + newlastdur,
                                    lastseg.duration - newlastdur,
                                    -1))
            

        # Add in the wolftones at every gap -- build up an output array
        out = np.zeros((R*self.duration, 2), np.int16)
        cur_t = 0
        arr = tape.getArray()
        
        # Wolftone everything
        # XXX: Use user-gen composition!
        buffers = [arr[X.st_idx:X.end_idx] for X in self.fills]
        buffers.extend([arr[X.st_idx:X.end_idx] for X in newfills])
        nwolfframes = sum([len(X) for X in buffers])
        comp = [(1500, nwolfframes)] # XXX: use variable wolf-toning
        wolftone = wolfcut(comp, buffers)

        for t, seg in seq:
            if t > cur_t:
                # XXX: wolftone
                nframes = int(R*(t - cur_t))
                out[int(R*cur_t):int(R*cur_t) + nframes] = wolftone[:nframes]
                wolftone = wolftone[nframes:]
            out[int(R*t):int(R*t)+seg.nframes] = arr[seg.st_idx:seg.end_idx]
            cur_t = t + seg.duration
            
        return out

    def getSequencePreview(self):
        return Sequence([self.timings[X] for X in sorted(self.timings.keys())])

class Sequence:
    def __init__(self, segs):
        self.segs = segs

    def getArray(self):
        if len(self.segs) == 0:
            print 'warning: no segments'
            return (2**14 * np.sin(np.linspace(0, 2*np.pi*440, 44100))).astype(np.int16)

        # XXX: Assume that all segments are from the same tape (?)
        # XXX: Also broken now that Seg doesn't point to tape
        arr = self.segs[0].tape.getArray()

        return np.concatenate([arr[X.st_idx:X.end_idx] for X in self.segs])
