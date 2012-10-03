import numm
import cv2
import numpy as np
from functools import reduce

import compose

def draw(comp, W=1200, H=600):
    arr = np.zeros((H,W,3), np.uint8)
    segs = reduce(lambda x,y: x+y, [X.getArrangement().getSequencePreview().segs for X in comp.rhythms])

    out_t = 0
    duration = max([X.start+X.duration for X in segs])
    for seg in segs:
        cv2.line(arr,
                 (int(W*(out_t/duration)), 0),
                 (int(W*(seg.start/duration)), H),
                 (255,255,255))

        out_t += seg.duration

    return arr

if __name__=='__main__':
    import sys
    comp = compose.Composition.fromfile(sys.argv[1])
    numm.np2image(draw(comp), sys.argv[2])
