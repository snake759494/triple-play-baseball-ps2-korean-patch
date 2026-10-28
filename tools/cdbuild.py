"""MODE2/2352 BIN 이미지 재빌드: 수정 파일을 Form1 섹터로 기록하고 EDC/ECC 재계산

크기가 원래 섹터 수 안에 들어가면 제자리, 넘치면 이미지 끝에 붙인다.
ISO9660 디렉터리 레코드(LBA·크기)와 PVD 볼륨 크기를 갱신한다.
"""
import os, shutil, struct
import numpy as np

RAW, SEC = 2352, 2048

# --- EDC/ECC 표 ---
_edc = []
for i in range(256):
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    _edc.append(e)
_EDC = np.array(_edc, np.uint32)
_ecc_f = bytearray(256); _ecc_b = bytearray(256)
for i in range(256):
    j = (i << 1) ^ (0x11D if i & 0x80 else 0)
    _ecc_f[i] = j & 0xff; _ecc_b[i ^ j & 0xff] = i
_ECCF = np.frombuffer(bytes(_ecc_f), np.uint8)
_ECCB = np.frombuffer(bytes(_ecc_b), np.uint8)


def edc(b):
    e = 0
    for x in b:
        e = (e >> 8) ^ _edc[(e ^ x) & 0xff]
    return e


def _ecc_pq(s, major_count, minor_count, major_mult, minor_inc, dst):
    size = major_count * minor_count
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = s[0xC + index]
            index += minor_inc
            if index >= size: index -= size
            a ^= t; b ^= t; a = _ecc_f[a]
        a = _ecc_b[_ecc_f[a] ^ b]
        s[dst + major] = a
        s[dst + major + major_count] = a ^ b


def make_sector(lba, data, sub=b'\x00\x00\x08\x00'):
    s = bytearray(RAW)
    s[0:12] = b'\x00' + b'\xff' * 10 + b'\x00'
    a = lba + 150
    m, r = divmod(a, 75 * 60); sec, f = divmod(r, 75)
    bcd = lambda v: ((v // 10) << 4) | (v % 10)
    s[12:16] = bytes([bcd(m), bcd(sec), bcd(f), 2])
    s[16:20] = sub; s[20:24] = sub
    s[24:24 + SEC] = data.ljust(SEC, b'\0')
    struct.pack_into('<I', s, 0x818, edc(s[16:0x818]))
    hdr = s[12:16]; s[12:16] = b'\0\0\0\0'
    _ecc_pq(s, 86, 24, 2, 86, 0x81C)
    _ecc_pq(s, 52, 43, 86, 88, 0x8C8)
    s[12:16] = hdr
    return bytes(s)


class Disc:
    def __init__(s, path):
        s.f = open(path, 'r+b')
        s.n = os.path.getsize(path) // RAW

    def read(s, lba, cnt=1):
        out = bytearray()
        for i in range(cnt):
            s.f.seek((lba + i) * RAW); out += s.f.read(RAW)[24:24 + SEC]
        return bytes(out)

    def subhdr(s, lba):
        s.f.seek(lba * RAW + 16); return s.f.read(4)

    def write(s, lba, data, last_eof=True):
        cnt = max(1, (len(data) + SEC - 1) // SEC)
        for i in range(cnt):
            sub = b'\x00\x00\x08\x00'
            if lba + i < s.n:
                sub = s.subhdr(lba + i)
            if last_eof and i == cnt - 1:
                sub = b'\x00\x00\x89\x00'   # EOR|EOF|DATA
            elif sub[2] & 0x81:
                sub = b'\x00\x00\x08\x00'
            s.f.seek((lba + i) * RAW)
            s.f.write(make_sector(lba + i, data[i * SEC:(i + 1) * SEC], sub))
        s.n = max(s.n, lba + cnt)


def walk(d, lba=None, size=None, path=''):
    if lba is None:
        pvd = d.read(16)
        lba, size = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
    data = d.read(lba, (size + SEC - 1) // SEC); p = 0; out = []
    while p < len(data):
        n = data[p]
        if n == 0: p = (p // SEC + 1) * SEC; continue
        l, sz = struct.unpack_from('<I', data, p + 2)[0], struct.unpack_from('<I', data, p + 10)[0]
        fl = data[p + 25]; nm = data[p + 33:p + 33 + data[p + 32]]
        if nm not in (b'\0', b'\1'):
            nm = nm.decode('latin1').split(';')[0]
            if fl & 2: out += walk(d, l, sz, path + nm + '/')
            else: out.append((path + nm, l, sz, lba, p))
        p += n
    return out


def build(src, dst, files, log=print):
    """files: {'DATA/ZFETEXT.ENG': bytes}"""
    shutil.copyfile(src, dst)
    d = Disc(dst)
    ents = {e[0]: e for e in walk(d)}
    end = d.n
    for name, data in files.items():
        _, lba, size, dlba, off = ents[name]
        old = (size + SEC - 1) // SEC; new = (len(data) + SEC - 1) // SEC
        pos = lba if new <= old else end
        if pos == end: end += new
        d.write(pos, data)
        sec = dlba + off // SEC; o = off % SEC
        blk = bytearray(d.read(sec))
        struct.pack_into('<I', blk, o + 2, pos); struct.pack_into('>I', blk, o + 6, pos)
        struct.pack_into('<I', blk, o + 10, len(data)); struct.pack_into('>I', blk, o + 14, len(data))
        d.write(sec, bytes(blk), last_eof=(d.subhdr(sec)[2] & 1) == 1)
        log(f'  {name}: {size} -> {len(data)} @ {pos}{" (이동)" if pos != lba else ""}')
    if d.n > os.path.getsize(src) // RAW:
        pvd = bytearray(d.read(16))
        struct.pack_into('<I', pvd, 80, d.n); struct.pack_into('>I', pvd, 84, d.n)
        d.write(16, bytes(pvd), last_eof=False)
    d.f.close()
