import cluster
import numm
import random

R = 44100
# PADDING = R / 4                 # frames between segments
# SOURCE = 'snd/Dance_A.wav'
SOURCE = 'snd/Duran_A.wav'
NBINS = 50

cur_cluster = 0
cluster_idx = 0
paused = False
frame_idx = 0

audio = numm.sound2np(SOURCE)
clusters = cluster.cluster(SOURCE, NBINS)

for c in clusters.values():
    random.shuffle(c)

def get_segment(cluster, idx):
    idx = idx % len(clusters[cluster])
    start, duration = clusters[cluster][idx]
    return audio[int(R*start):int(R*(start+duration))]

def audio_out(a):
    global frame_idx, cluster_idx, paused

    if paused:
        paused = False
        return

    seg = get_segment(cur_cluster, cluster_idx)

    amnt = min(len(seg)-frame_idx, len(a))
    a[:amnt] = seg[frame_idx:frame_idx+amnt]

    frame_idx += amnt

    if frame_idx >= len(seg):
        cluster_idx += 1
        frame_idx = 0
        paused = True
        print 'cluster', cur_cluster, 'idx', cluster_idx

def keyboard_in(type, key):
    global cur_cluster, cluster_idx
    if type == 'key-press':
        cluster_idx = 0
        frame_idx = 0
        cur_cluster = (cur_cluster + 1) % 15
        print 'cluster', cur_cluster
    


if __name__=='__main__':
    numm.run(**globals())
