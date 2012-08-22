from compose import Tape

import cv2
import numpy as np

cur_cluster = '0'
cur_idx = 0
cur_frame = 0

def keyboard_in(type, button):
    global cur_cluster, cur_idx, cur_frame
    if len(button) == 1:
        cur_cluster = button.upper()

        cur_idx = 0
        cur_frame = 0

def mouse_in(type, px, py, button):
    global cur_idx, cur_frame
    
    nsegs = len(clusters[cur_cluster])
    N = int(np.ceil(np.sqrt(nsegs)))

    _oidx = cur_idx
    cur_idx = min(nsegs-1, int(px*N) + N*int(py*N))

    if cur_idx != _oidx:
        cur_frame = 0

def audio_out(a):
    global cur_frame, cur_idx
    seg = clusters[cur_cluster][cur_idx]
    segarr = arr[seg.st_idx:seg.end_idx][cur_frame:]

    if len(segarr) < len(a):
        a[:len(segarr)] = segarr
        cur_frame = 0
        cur_idx = (cur_idx + 1) % (len(clusters[cur_cluster]))
        return

    a[:] = segarr[:len(a)]
    cur_frame = cur_frame + len(a)

def video_out(a):
    # draw a grid of segment circles
    segs = clusters[cur_cluster]
    N = int(np.ceil(np.sqrt(len(segs))))

    stepx = 320 / N
    stepy = 240 / N
    r = int(min(stepx, stepy)/2)
    for i in range(len(segs)):
        row = int(i / N)
        col = i % N

        color = (255,255,255)
        stroke = 1
        if i == cur_idx:
            color = (255,0,0)
            stroke = -1

        x,y = (col*stepx + r, row*stepy + r)
        cv2.circle(a, (x,y), r, color, stroke)
        cv2.putText(a, str(i), (x,y), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,255))

    cv2.putText(a, cur_cluster, (305,230), cv2.FONT_HERSHEY_PLAIN, 1, (0,255,0))

if __name__=='__main__':
    import sys
    import numm

    tape = Tape(sys.argv[1])
    arr = tape.getArray()
    clusters = tape.getClusters()

    numm.run(**globals())
