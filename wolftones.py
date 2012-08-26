import numpy as np

R = 44100

def wolfcut(composition, buffers):
    """A `composition' is a list of [(frequency, nframes)] and
    `buffers' a list of np_arrays, such that the sum of nframes in the
    composition is equal to the sum of rows in the buffers. The output
    is a single, wolfcut, numpy buffer.
    """
    nframes = sum([X[1] for X in composition])
    assert nframes == sum([len(X) for X in buffers]), "Frame count much match composition length"

    # XXX: would a function or composition buffer make more sense?

    out = np.zeros((nframes, 2), np.int16)
    out_idx = 0
    buf_idx = 0
    for (fr, nf) in composition:
        print (fr, nf)
        nrem = nf
        period = R/fr
        while nrem > 0:
            prem = min(nrem, period)
            while prem > 0:
                amnt = min(prem, len(buffers[buf_idx]))
                out[out_idx:out_idx+amnt] = buffers[buf_idx][:amnt]
                out_idx += amnt
                nrem -= amnt
                prem -= amnt
                if amnt == len(buffers[buf_idx]):
                    #done with this buffer
                    buffers.pop(buf_idx)
                else:
                    buffers[buf_idx] = buffers[buf_idx][amnt:]
                    # # Defer frames to avoid pitch-shifting
                    # if len(buffers) > 1:
                    #     buffers[buf_idx] = np.roll(buffers[buf_idx], -amnt*len(buffers), axis=0)
                if len(buffers) == 0:
                    return out
                buf_idx = (buf_idx + 1) % len(buffers)

if __name__=='__main__':
    import numm
    import sys
    buffers = [numm.sound2np(X) for X in sys.argv[1:]]

    nframes = sum([len(X) for X in buffers])

    # freqrot = [440, 800, 1500, 300]
    freqrot = [4400, 1800, 1500, 2222]

    comp = []
    f_idx = 0
    w_len = R/4
    while nframes > 0:
        amnt = min(nframes, w_len)
        comp.append((freqrot[f_idx], amnt))
        f_idx = (f_idx + 1) % len(freqrot)
        nframes -= amnt
        
    out = wolfcut(comp, buffers)

    numm.np2sound(out, 'wolf.wav')
