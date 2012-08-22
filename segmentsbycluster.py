from compose import Tape

import cv2
import numpy as np

cur_cluster = '0'
cur_idx = 0

def keyboard_in(type, button):
    global cur_cluster
    if len(button) == 1:
        cur_cluster = button.upper()

def video_out(a):
    cv2.putText(a, cur_cluster, (10,20), cv2.FONT_HERSHEY_PLAIN, 1, (0,255,0))

    # draw a grid of segment circles
    segs = clusters[cur_cluster]
    N = int(np.ceil(np.sqrt(len(segs))))

    stepx = 320 / N
    stepy = 240 / N
    r = int(min(stepx, stepy)/2)
    for i in range(len(segs)):
        row = int(i / N)
        col = i % N

        cv2.circle(a, (col*stepx + r, row*stepy + r), r, (255,0,0))
        

if __name__=='__main__':
    import sys
    import numm

    tape = Tape(sys.argv[1])
    arr = tape.getArray()
    clusters = tape.getClusters()

    numm.run(**globals())
