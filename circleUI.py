from compose import Tape, Circle, Arrangement, Sequence
import numpy as np
import cv2

a_idx = 0

arrangement = None
arr = None

def audio_out(a):
    global a_idx
    if arr is None:
        return

    a[:] = np.roll(arr, -a_idx, axis=0)[:len(a)].reshape((len(a), -1))

    a_idx = (a_idx + len(a)) % (len(arr))

def video_out(a):
    if arr is None:
        return

    w,h = 320,240
    r = int(0.75 * min(w,h)/2)
    cv2.circle(a, (w/2,h/2), r, (0,255,0))

    duration = len(arr) / 44100.0
    impulses = sorted(arrangement.timings.keys())
    
    for t in impulses:
        percent = t / duration
        x = int(w/2 + r * np.cos(2*np.pi*percent))
        y = int(h/2 + r * np.sin(2*np.pi*percent))

        cv2.circle(a, (x, y), 5, (255, 0, 0))

def keyboard_in(type, button):
    global arr, arrangement

    cid = button.upper()
    if type == 'key-press' and len(cid) == 1:
        circle.setNSegs(cid, circle.getNSegs(cid) + 1)

    arrangement = circle.getArrangement(tape)
    arr = arrangement.getSequence().getArray()

    print circle.clusters, arr.shape


if __name__=='__main__':
    import sys
    import numm

    SRC = sys.argv[1]

    tape = Tape(SRC)
    circle = Circle({})

    numm.run(**globals())
