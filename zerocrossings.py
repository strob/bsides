
def zerocrossings(a):
    return (a[1:].astype(int) * a[:-1]) <= 0

def next_zerocrossing(zcs, idx):
    # always late, ie. the *next* zero-crossing
    return idx + zcs[idx:].argmax()
