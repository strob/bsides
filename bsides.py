# zoom-based UI to compose a full tape

from compose import Tape, Composition, Square

import numpy as np
import numm
import cv2

ZOOM_LEVELS = ['structure', 'rhythm', 'sound']
zoom_idx = 0

playseg = None
audio_frame = 0

mousex = 0
mousey = 0

def video_out(a):
    cv2.putText(a, ZOOM_LEVELS[zoom_idx], (10, 20), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,255))
    if ZOOM_LEVELS[zoom_idx] == 'structure':
        structure_video(a)
    elif ZOOM_LEVELS[zoom_idx] == 'rhythm':
        rhythm_video(a)
    else:
        sound_video(a)

def audio_out(a):
    global audio_frame
    segarr = getplayarr()

    if segarr is None:
        return

    segarr = segarr[audio_frame:]

    if len(segarr) < len(a):
        a[:len(segarr)] = segarr
        audio_advance()
        return audio_out(a[len(segarr):])

    a[:] = segarr[:len(a)]
    audio_frame += len(a)

def getseg():
    if ZOOM_LEVELS[zoom_idx] == 'sound':
        return sound_pages[sound_page_idx][sound_idx]

def getplayseg():
    return playseg

def getplayarr():
    if ZOOM_LEVELS[zoom_idx] == 'sound':
        s = getplayseg()
        if s is None:
            return
        return tape.getArray()[s.st_idx:s.end_idx]
    else:
        return rhythm_array

def audio_advance():
    global playseg, audio_frame, rhythm_square, structure_rhythm_idx
    audio_frame = 0

    if ZOOM_LEVELS[zoom_idx] == 'structure':
        rhythms = composition.rhythms
        if len(rhythms) == 0:
            return
        structure_rhythm_idx = (1 + structure_rhythm_idx) % len(rhythms)
        rhythm_square = rhythms[structure_rhythm_idx] 
        rhythm_change()

    elif ZOOM_LEVELS[zoom_idx] == 'sound':
        playseg = None

def sound_video(a):
    if sound_page_idx >= len(sound_pages) or len(sound_pages[sound_page_idx]) == 0:
        print 'warning: big sound_page_idx', sound_page_idx, len(sound_pages)
        return
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

    cv2.putText(a, 'page %d(%d)' % (sound_page_idx, len(sound_pages)), (10, 220), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,0))
    cv2.putText(a, 'sort by %s' % (SOUND_ORDERINGS[sound_order_idx]), (10, 200), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,0))

structure_rhythm_idx = 0


def structure_video(a):
    nsquares = len(composition.rhythms)
    N = int(np.ceil(np.sqrt(nsquares)))
    if N > 0:
        w,h = 320/N, 240/N
    for idx,square in enumerate(composition.rhythms):
        x= w*(idx %N)
        y= h*(int(idx/N))

        draw_square(a[y:y+h,x:x+w], square)

rhythm_square = None
rhythm_sequence = None
rhythm_array = None
rhythm_twisting = False
rhythm_toning = False

def rhythm_init():
    global rhythm_sequence, audio_frame, rhythm_array
    audio_frame = 0
    if len(rhythm_square.groups) > 0:
        rhythm_change()
    else:
        rhythm_sequence = None
        rhythm_array = None

def rhythm_change():
    global rhythm_array, rhythm_sequence, audio_frame

    print 'rhythm_change'

    rhythm_sequence = rhythm_square.getArrangement().getSequencePreview().segs
    rhythm_array = rhythm_square.getArrangement().getArray(tape)
    if audio_frame > len(rhythm_array):
        audio_frame = 0

def rhythm_video(a):
    draw_square(a, rhythm_square)

def draw_square(a, square):
    groups = square.groups

    arrangement = square.getArrangement()
    timings = arrangement.timings

    duration = square.getDuration()

    def get_timing(seg):
        for t,s in timings.items():
            if seg == s:
                return t

    curseg = getseg()

    ngroups = len(groups)

    if ngroups == 0:
        return

    h = a.shape[0] / ngroups
    w = a.shape[1]
    for idx,segs in enumerate(groups):
        y = idx * h

        if square.isFill(idx):
            percent = sum([x.duration for x in segs]) / duration
            h2 = int(h * percent)
            a[y+h-h2:y+h] += (255,0,255)
            continue
            
        for s in segs:
            st = get_timing(s)
            end = st + s.duration
            x1 = int(st*w/duration)
            x2 = int(end*w/duration)

            color = (0,200,0)
            a[y:y+h,x1:x2] += color

    if rhythm_square == square:
        a[:,int(a.shape[1] * (audio_frame / float(len(rhythm_array))))] += (255,0,0)

    tx = range(w)
    ty = [int(a.shape[0]*square.getTone(X/float(w))) for X in tx]
    a[ty,tx] += (0,0,255)
    for px,py in square._tones.items():
        x = int(px*w)
        y = int(py*a.shape[0])
        cv2.circle(a, (x,y), 3, (0,0,255))
            

def keyboard_in(type, button):
    print 'keyboard_in', type, button

    if button == 's':
        composition.save(comppath)

    if ZOOM_LEVELS[zoom_idx] == 'structure':
        structure_keys(type, button)
    elif ZOOM_LEVELS[zoom_idx] == 'rhythm':
        rhythm_keys(type, button)
    else:
        sound_keys(type, button)

def structure_keys(type, button):
    global zoom_idx, rhythm_square
    if type == 'key-press':
        if button == 'n':
            rhythm_square = Square()
            rhythm_init()
            composition.append(rhythm_square)
            zoom_idx = ZOOM_LEVELS.index('rhythm')
        elif button == 'e':
            out = np.concatenate([X.getArrangement().getArray(tape) for X in composition.rhythms])
            numm.np2sound(out, 'export.wav')

def rhythm_keys(type, button):
    global zoom_idx, rhythm_twisting, rhythm_toning
    if type == 'key-press':
        if button == 'n':
            sound_init()
            zoom_idx = ZOOM_LEVELS.index('sound')
        elif button == 'r':
            # rhythm_square.setTheta(mousex)
            # rhythm_change()
            rhythm_twisting = True
        elif button == 't':
            rhythm_square.addTone(mousex, mousey)
            rhythm_change()
            # rhythm_toning = True
        elif button == 'Escape':
            if len(rhythm_square.groups) == 0:
                composition.rhythms.remove(rhythm_square)

            structure_init()
            zoom_idx = ZOOM_LEVELS.index('structure')
    elif type == 'key-release':
        if button == 'r':
            rhythm_twisting = False
            rhythm_change()
        if button == 't':
            rhythm_toning = False
            rhythm_change()

def structure_init():
    global structure_rhythm_idx, audio_frame, rhythm_square
    audio_frame = 0
    structure_rhythm_idx = 0

    if len(composition.rhythms) == 0:
        return
    rhythm_square = composition.rhythms[structure_rhythm_idx]
    rhythm_change()
    

def sound_keys(type, button):
    global sound_page_idx, sound_idx, sound_order_idx

    if type == 'key-press':
        try:
            i = int(button)
            sound_page_idx = i
            sound_idx = 0
            return
        except ValueError:
            pass

        if button == 'c':
            sound_order_idx = SOUND_ORDERINGS.index('cluster')
        elif button == 'm':
            sound_order_idx = SOUND_ORDERINGS.index('similarity')
        elif button == 't':
            sound_order_idx = SOUND_ORDERINGS.index('time')
        elif button == 'o':
            sound_order_idx = SOUND_ORDERINGS.index('closeness')
        if button in 'cmto':
            paginate_sound()


def mouse_in(type, px, py, button):
    global mousex, mousey
    mousex = px
    mousey = py
    # print type, px, py, button
    if ZOOM_LEVELS[zoom_idx] == 'sound':
        sound_mouse(type, px, py, button)
    elif ZOOM_LEVELS[zoom_idx] == 'rhythm':
        rhythm_mouse(type, px, py, button)

SOUND_ORDERINGS = ['time', 'cluster', 'similarity', 'closeness']
sound_order_idx = 0

sound_pages = []
sound_page_idx = 0
sound_idx = 0

# mouse drag interaction
sound_dragging = False
sound_dragging_first = None
sound_selection = []

# similarity search invarients
sound_similarity_base = None

def sound_init():
    global sound_order_idx, sound_page_idx, sound_idx
    sound_order_idx = 0
    sound_idx = 0
    sound_page_idx = 0
    paginate_sound()

def paginate_sound():
    global sound_pages, sound_page_idx
    print 'start paginate'

    curseg = getseg()
    if curseg:
        print 'curseg', curseg.start, curseg.idx

    sound_pages = []
    sound_page_idx = 0

    if SOUND_ORDERINGS[sound_order_idx] == 'time':
        print 'order by time'
        segs = tape.getSegments()
        segs.sort(cmp=lambda x,y: int(44100*(x.start-y.start)))
        npages = 10
        npp = len(segs) / npages

        for i in range(npages):
            psegs = segs[i*npp:(i+1)*npp]
            sound_pages.append(psegs)
            if curseg and curseg in psegs:
                print 'curseg in timepage', i
                sound_page_idx = i
    elif SOUND_ORDERINGS[sound_order_idx] == 'cluster':
        clusters = tape.getClusters()
        for idx,(k,v) in enumerate(sorted(clusters.items())):
            sound_pages.append(v)
            if curseg and curseg in v:
                print 'curseg in cluster', idx
                sound_page_idx = idx
    elif SOUND_ORDERINGS[sound_order_idx] == 'similarity':
        similarity_tape = Tape(tape.path, nbins=9)
        base = curseg
        nsegs = min(len(similarity_tape.getSegments()), 100)
        page = []
        sound_pages.append(page)

        while len(page) < nsegs:
            cluster,idx = similarity_tape.getClosestUnused(base)
            base = similarity_tape.getClusters()[cluster][idx]
            similarity_tape.use(base)
            page.append(base)

    else:
        # closeness
        base = curseg
        page = []
        ordered = tape.orderBySegment(base)
        sound_pages.append(ordered[:100])

    print 'done paginate'

def rhythm_mouse(type, px, py, button):
    global rhythm_sequence
    ngroups = len(rhythm_square.groups)
    g_idx = int(py * ngroups)
    if type == 'mouse-button-press' and ngroups > 0:
        if button == 1:
            if rhythm_square.isFill(g_idx):
                rhythm_square.removeFill(g_idx)
            else:
                rhythm_square.addFill(g_idx)
            rhythm_change()
        elif button == 3:
            print "delete", g_idx
            group = rhythm_square.remove(g_idx)
            for s in group:
                tape.unuse(s)

    if rhythm_twisting:
        # XXX: relative motion!
        rhythm_square.setTheta(px)
        rhythm_sequence = rhythm_square.getArrangement().getSequencePreview().segs
    elif rhythm_toning:
        rhythm_square.addTone(px, py)
    
def sound_mouse(type, px, py, button):
    global sound_idx, sound_dragging, sound_selection, sound_dragging_first, zoom_idx, playseg, audio_frame

    nsegs = len(sound_pages[sound_page_idx])
    N = int(np.ceil(np.sqrt(nsegs)))

    _oidx = sound_idx
    sound_idx = min(nsegs-1, int(px*N) + N*int(py*N))

    if type == 'mouse-button-press':
        sound_selection = []
        sound_dragging = True
        sound_dragging_first = sound_pages[sound_page_idx][sound_idx]

    if type == 'mouse-move' and sound_dragging:
        sound_make_selection()

    if type == 'mouse-button-release':
        # Add selection to the rhythm
        sound_dragging = False
        sound_make_selection()
        rhythm_square.append(sound_selection)

        for seg in sound_selection:
            tape.use(seg)

        rhythm_init()
        zoom_idx = ZOOM_LEVELS.index('rhythm')

    if (_oidx != sound_idx) or (playseg is None):
        audio_frame = 0
        playseg = sound_pages[sound_page_idx][sound_idx]

def sound_make_selection():
    global sound_selection

    spage = sound_pages[sound_page_idx]
    sound_selection = []

    st = min(spage.index(sound_dragging_first), sound_idx)
    end = max(spage.index(sound_dragging_first), sound_idx) + 1
    for idx in range(st,end):
        if not tape.isUsed(spage[idx]):
            sound_selection.append(spage[idx])


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

    tape = Tape(source, nbins=9)
    # preload array
    tape.getArray()

    composition = Composition([])
    if os.path.exists(comppath):
        composition = Composition.fromfile(comppath)
        for r in composition.rhythms:
            for g in r.groups:
                for s in g:
                    tape.use(s)

    structure_init()

    numm.run(**globals())
