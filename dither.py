import numm
import numpy as np

a = numm.sound2np('a.wav')
b = numm.sound2np('b.wav')

# a = np.int16(2**14 * np.sin(np.linspace(0, 2*np.pi*440, 44100)))
# b = np.int16(2**14 * np.sin(np.linspace(0, 2*np.pi*240, 44100)))

DITHER_FRAMES = 1024

dit_idx = 0
cur_snd = a

def flip():
    global cur_snd
    if cur_snd.data == a.data:
        cur_snd = b
    else:
        cur_snd = a

def audio_out(out):
    global dit_idx
    nrem = len(out)
    while nrem > 0:
        amnt = min(DITHER_FRAMES-dit_idx, nrem)

        out_st = len(out)-nrem
        out[out_st:out_st+amnt] = cur_snd[:amnt].reshape((amnt,-1))
        cur_snd[:] = np.roll(cur_snd, -len(cur_snd.shape)*amnt, axis=0)

        dit_idx += amnt
        if dit_idx >= DITHER_FRAMES:
            flip()
            dit_idx = 0

        nrem -= amnt

def video_out(out):
    pass

def mouse_in(type, px, py, button):
    global DITHER_FRAMES, dit_idx
    dit_idx = 0
    DITHER_FRAMES = 1 + int(px * 44100)
    print DITHER_FRAMES
