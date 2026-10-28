"""EAGL 텍스처 오브젝트(.O, ELF 재배치 파일) 읽기/쓰기

texture_<이름> 심볼 -> 헤더(+0x40 TEX0 등 GIF 레지스터, +0x90 업로드 설명자 포인터)
설명자: +0x3C 픽셀 포인터, +0x58 팔레트 포인터(상위 32비트 = 폭), +0x60 높이(상위 = PSM)
픽셀은 선형 배치, 8bpp 팔레트는 PS2 CSM1 배열(8~15 <-> 16~23 교환), 알파 0~0x80.
"""
import struct
import numpy as np

D = 0x40   # .data 섹션 파일 오프셋


class Tex:
    pass


def _swz(i):  # CSM1 팔레트 인덱스 교환
    return (i & ~0x18) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)


SWZ = np.array([_swz(i) for i in range(256)])


def parse(b):
    shoff = struct.unpack_from('<I', b, 0x20)[0]; shn, shstr = struct.unpack_from('<HH', b, 0x30)
    sh = [struct.unpack_from('<10I', b, shoff + i * 40) for i in range(shn)]
    data = [s for s in sh if s[1] == 1][0]
    assert data[4] == D
    sym = [s for s in sh if s[1] == 2][0]; strt = sh[sym[6]]
    texs = []
    for i in range(sym[5] // 16):
        n, v, sz, inf, o, ndx = struct.unpack_from('<IIIBBH', b, sym[4] + i * 16)
        name = b[strt[4] + n:b.index(b'\0', strt[4] + n)].decode()
        if not name.startswith('texture_'): continue
        t = Tex(); t.name = name[8:]; t.hdr = v
        t.tex0 = struct.unpack_from('<Q', b, D + v + 0x40)[0]
        t.desc = struct.unpack_from('<I', b, D + v + 0x90)[0]
        d = D + t.desc
        t.pix = struct.unpack_from('<I', b, d + 0x3c)[0]
        t.pal, t.w = struct.unpack_from('<II', b, d + 0x58)
        t.h, t.psm = struct.unpack_from('<II', b, d + 0x60)
        texs.append(t)
    return texs


def decode(b, t):
    """RGBA 배열 (알파 0~255)"""
    w, h = t.w, t.h
    if t.psm == 0x13:
        idx = np.frombuffer(b, np.uint8, w * h, D + t.pix).reshape(h, w)
        pal = np.frombuffer(b, np.uint8, 1024, D + t.pal).reshape(256, 4)[SWZ]
    elif t.psm == 0x14:
        raw = np.frombuffer(b, np.uint8, w * h // 2, D + t.pix)
        idx = np.zeros(w * h, np.uint8); idx[0::2] = raw & 15; idx[1::2] = raw >> 4
        idx = idx.reshape(h, w)
        pal = np.frombuffer(b, np.uint8, 64, D + t.pal).reshape(16, 4)
    elif t.psm == 0x00:
        a = np.frombuffer(b, np.uint8, w * h * 4, D + t.pix).reshape(h, w, 4).copy()
        a[..., 3] = np.minimum(255, a[..., 3].astype(int) * 2)
        return a
    else:
        return None
    out = pal[idx].copy()
    out[..., 3] = np.minimum(255, out[..., 3].astype(int) * 2)
    return out


def encode(b, t, rgba):
    """같은 크기·형식으로 다시 기록(팔레트도 새로 만든다)"""
    b = bytearray(b)
    a = rgba.copy().astype(np.int32)
    a[..., 3] = (a[..., 3] + 1) // 2
    h, w = t.h, t.w
    assert a.shape[:2] == (h, w)
    n = 256 if t.psm == 0x13 else 16
    from PIL import Image
    flat = a.reshape(-1, 4).astype(np.uint8)
    im = Image.fromarray(flat.reshape(h, w, 4), 'RGBA')
    q = im.quantize(colors=n, method=Image.Quantize.FASTOCTREE)
    pal = np.array(q.getpalette('RGBA')[:n * 4], np.uint8).reshape(-1, 4)
    pal = np.vstack([pal, np.zeros((n - len(pal), 4), np.uint8)])
    idx = np.array(q, np.uint8)
    if t.psm == 0x13:
        b[D + t.pix:D + t.pix + w * h] = idx.tobytes()
        inv = np.zeros(256, int); inv[SWZ] = np.arange(256)
        b[D + t.pal:D + t.pal + 1024] = pal[inv].tobytes()
    else:
        f = idx.reshape(-1)
        b[D + t.pix:D + t.pix + w * h // 2] = (f[0::2] | (f[1::2] << 4)).astype(np.uint8).tobytes()
        b[D + t.pal:D + t.pal + 64] = pal.tobytes()
    return bytes(b)
