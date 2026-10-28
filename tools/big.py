"""BIGF 아카이브 읽기/쓰기"""
import struct


def read(b):
    n, hdr = struct.unpack('>II', b[8:16]); p = 16; ents = []
    for _ in range(n):
        o, s = struct.unpack('>II', b[p:p + 8]); p += 8
        e = b.index(b'\0', p); ents.append((b[p:e].decode(), b[o:o + s])); p = e + 1
    return ents


def write(ents, align=1):
    hdr = 16 + sum(8 + len(n) + 1 for n, _ in ents)
    data = bytearray(); offs = []
    pos = hdr
    for n, d in ents:
        offs.append(pos); data += d; pos += len(d)
    h = bytearray(b'BIGF') + struct.pack('>III', pos, len(ents), hdr)
    for (n, d), o in zip(ents, offs):
        h += struct.pack('>II', o, len(d)) + n.encode() + b'\0'
    return bytes(h + data)
