# zoom-based UI to compose a full tape

from compose import Tape, Composition, Square

import numpy as np
import cv2

ZOOM_LEVELS = ['structure', 'rhythm', 'sound']
zoom_idx = 0

rhythm_square = None

def video_out(a):
    cv2.putText(a, ZOOM_LEVELS[zoom_idx], (10, 20), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,255))
    if ZOOM_LEVELS[zoom_idx] == 'structure':
        structure_video(a)
    elif ZOOM_LEVELS[zoom_idx] == 'rhythm':
        rhythm_video(a)
    else:
        sound_video(a)

def sound_video(a):
    segs = sound_pages[sound_page_idx]
    N = int(np.ceil(np.sqrt(len(segs))))
    w,h = (int(320/N), int(240/N))

    for i,s in enumerate(segs):
        x,y = ((i%N)*w, (i/N)*h)

        color = (0,75,0)
        if tape.isUsed(s):
            color = (255,0,0)
        elif sound_idx == i:
            color = (0,255,0)
        elif s in sound_selection:
            color = (0,255,255)

        a[y:y+h,x:x+w] += color

def structure_video(a):
    nsquares = len(composition.rhythms)
    N = int(np.ceil(np.sqrt(nsquares)))
    if N > 0:
        w,h = 320/N, 240/N
    for idx,square in composition.rhythms:
        x= idx %N
        y= int(idx/N)

        draw_square(a[y:y+h,x:x+w], square)

def rhythm_video(a):
    draw_square(a, rhythm_square)

def draw_square(a, square):
    groups = square.groups
    arrangement = square.getArrangement()
    timings = arrangement.timings

    times = sorted(timings.keys())
    if len(times) == 0:
        return

    duration = times[-1] + timings[times[-1]].duration

    def get_timing(seg):
        for t,s in timings.items():
            if seg == s:
                return t

    ngroups = len(groups)
    h = a.shape[0] / ngroups
    w = a.shape[1]
    for idx,segs in enumerate(groups):
        y = idx * h
        for s in segs:
            st = get_timing(s)
            end = st + s.duration
            x1 = int(st*w/duration)
            x2 = int(end*w/duration)

            a[y:y+h,x1:x2] += (0,255,0)
            

def keyboard_in(type, button):
    print 'keyboard_in', type, button
    if ZOOM_LEVELS[zoom_idx] == 'structure':
        structure_keys(type, button)
    elif ZOOM_LEVELS[zoom_idx] == 'rhythm':
        rhythm_keys(type, button)
    else:
        sound_keys(type, button)

def structure_keys(type, button):
    global zoom_idx, rhythm_square
    if type == 'key-press' and button == 'n':
        rhythm_square = Square()
        composition.append(rhythm_square)
        zoom_idx = ZOOM_LEVELS.index('rhythm')
def rhythm_keys(type, button):
    global zoom_idx
    if type == 'key-press' and button == 'n':
        sound_init()
        zoom_idx = ZOOM_LEVELS.index('sound')
def sound_keys(type, button):
    pass


def mouse_in(type, px, py, button):
    # print type, px, py, button
    if ZOOM_LEVELS[zoom_idx] == 'sound':
        sound_mouse(type, px, py, button)

SOUND_ORDERINGS = ['time', 'cluster', 'similarity']
sound_order_idx = 0

sound_pages = []
sound_page_idx = 0
sound_idx = 0

# mouse drag interaction
sound_dragging = False
sound_dragging_first = None
sound_selection = []

def sound_init():
    global sound_page_idx, sound_idx
    sound_idx = 0
    sound_page_idx = 0
    paginate_sound()

def paginate_sound():
    global sound_pages
    if SOUND_ORDERINGS[sound_order_idx] == 'time':
        segs = list(tape.getSegments())
        segs.sort(cmp=lambda x,y: int(44100*(x.start-y.start)))
        npages = 10
        npp = len(segs) / npages
        sound_pages = []
        for i in range(10):
            sound_pages.append(segs[i*npp:(i+1)*npp])
    else:
        pass

def sound_mouse(type, px, py, button):
    global sound_idx, sound_dragging, sound_dragging_first, sound_selection, zoom_idx

    nsegs = len(sound_pages[sound_page_idx])
    N = int(np.ceil(np.sqrt(nsegs)))

    _oidx = sound_idx
    sound_idx = min(nsegs-1, int(px*N) + N*int(py*N))

    if type == 'mouse-button-press':
        sound_selection = []
        sound_dragging = True
        sound_dragging_first = sound_pages[sound_page_idx][sound_idx]

    if type == 'mouse-move' and sound_dragging:
        spage = sound_pages[sound_page_idx]
        sound_selection = []
        for idx in range(spage.index(sound_dragging_first), sound_idx):
            if not tape.isUsed(spage[idx]):
                sound_selection.append(spage[idx])

    if type == 'mouse-button-release':
        # Add selection to the rhythm
        sound_dragging = False
        rhythm_square.append(sound_selection)

        for seg in sound_selection:
            tape.use(seg)

        zoom_idx = ZOOM_LEVELS.index('rhythm')


if __name__=='__main__':
    import sys
    import os

    import numm

    USAGE = 'python bsides.py SOURCE [COMPOSITION]'

    if len(sys.argv) < 2:
        print USAGE
        sys.exit(1)

    source = sys.argv[1]
    comppath = source + '.composition.pkl'
    if len(sys.argv) > 2:
        comppath = sys.argv[2]

    tape = Tape(source)
    composition = Composition([])
    if os.path.exists(comppath):
        composition = Composition.fromfile(comppath)

    numm.run(**globals())
