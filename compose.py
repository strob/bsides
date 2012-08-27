import cluster
import meap
from wolftones import wolfcut

import numm
import numpy as np

import pickle

def _linear_interp(map, x):
    keys = sorted(map.keys())
    for idx,k in enumerate(keys):
        if k>x:
            x1,y1 = (keys[idx-1], map[keys[idx-1]])
            x2,y2 = (k, map[k])
            weight= (x-x1) / (x2-x1)
            return (1-weight) * y1 + weight * y2


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
        out = pickle.load(open(filename))
        out.rhythms = filter(lambda x: len(x.groups) > 0, out.rhythms)
        return out

class Square:
    "cluster-independent alternative to `circle`"
    def __init__(self):
        self.groups = []
        self.theta = 0          # [0,1]
        self._fills = set()
        self._tones = {0:0.5, 1:0.5}

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

    def addTone(self, x, y):
        # truncate to 100 x-values
        x = int(x * 100) / 100.0

        self._tones[x] = y

    def getTone(self, x):
        assert x>=0 and x<=1, "x must be in range (0,1)"

        if x in self._tones:
            return self._tones[x]

        # linear interpolation
        return _linear_interp(self._tones, x)

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

        o1 = pow( abs ( cos(pi * theta * (index + 1) + duration) ), 2)
        o2 = pow( abs ( cos(nsegs * theta / percentage) ), 0.5)
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

            o1 = pow( abs( np.cos( np.pi * self.theta * idx + duration ) ), 2)
            o2 = pow( abs( np.cos( nsegs * self.theta / percentage ) ), 0.5)

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

        return Arrangement(timing, fills=fills, duration=self.getDuration(), tones=self._tones)

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

        # check if we've overflowed duration
        if len(seq) > 0:
            laststart, lastseg = seq[-1]
            if laststart + lastseg.duration > self.duration:
                print 'trimming last seg'
                seq.pop()
                newlastdur = self.duration-laststart
                seq.append((laststart, Seg(lastseg.start, newlastdur,-1)))
                newfills.append(Seg(lastseg.start + newlastdur,
                                    lastseg.duration - newlastdur,
                                    -1))

        # Convert everything from seconds to frames so we can be sure
        # of exactitude.
        seq = [(int(x[0]*R),x[1]) for x in seq]

        # Add in the wolftones at every gap -- build up an output array
        nframes = int(R*self.duration)
        out = np.zeros((nframes, 2), np.int16)
        print 'out', out.shape
        cur_fr = 0
        arr = tape.getArray()
        
        # Wolftone everything
        buffers = [arr[X.st_idx:X.end_idx] for X in self.fills]
        buffers.extend([arr[X.st_idx:X.end_idx] for X in newfills])
        nwolfframes = sum([len(X) for X in buffers])
        comp = self.getComposition(nwolfframes)

        wolftone = wolfcut(comp, buffers)

        print 'wolftone', wolftone.shape
        print 'seqdur', sum([x[1].nframes for x in seq])

        for st_fr, seg in seq:
            if st_fr > cur_fr:
                nframes = st_fr - cur_fr
                minnframes = min(len(out[cur_fr:]),
                              min(len(wolftone), nframes))
                if nframes != minnframes:
                    # XXX: why do these shapes mismatch sometimes ?!
                    print 'Warning: shape mismatch! out', nframes, len(out[cur_fr:]), len(wolftone)
                    nframes = minnframes

                out[cur_fr:cur_fr + nframes] = wolftone[:nframes]
                wolftone = wolftone[nframes:]

            amnt = min(len(out)-cur_fr, seg.nframes)
            if amnt != seg.nframes:
                print 'Out is a little short:', amnt, seg.nframes
            out[cur_fr:cur_fr+amnt] = arr[seg.st_idx:seg.st_idx + amnt]
            cur_fr = st_fr + seg.nframes

        # end with wolftones if necessary
        if len(wolftone) > 0:
            print 'some wolftones remain'
            out[-len(wolftone):] = wolftone

        return out

    def getSequencePreview(self):
        return Sequence([self.timings[X] for X in sorted(self.timings.keys())])

    def getTone(self, x, min_f=27.5, max_f=4186.01):
        # XXX: duplicated code.

        assert x>=0 and x<=1, "x must be in range (0,1)"

        if x in self.tones:
            y = self.tones[x]

        else:
            # linear interpolation
            y = _linear_interp(self.tones, x)

        return int(np.exp2(np.log2(y*min_f + (1-y)*max_f)))

    def getComposition(self, nframes):
        step_frames = int(max(R/30, nframes/100)) # Don't make too many notes!

        comp = []
        cur_frame = 0
        while cur_frame < nframes:
            amnt = min(nframes-cur_frame, step_frames)
            percent = cur_frame / float(nframes)

            comp.append((self.getTone(percent), amnt))

            cur_frame += amnt

        return comp

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
