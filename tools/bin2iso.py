"""검증용: MODE2/2352 BIN -> 2048 ISO"""
import sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, 'rb') as f, open(dst, 'wb') as o:
    while True:
        b = f.read(2352 * 512)
        if not b: break
        o.write(b''.join(b[i + 24:i + 2072] for i in range(0, len(b), 2352)))
