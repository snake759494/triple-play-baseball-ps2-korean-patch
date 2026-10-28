"""EA RefPack (0x10FB) 압축 해제 / 리터럴 전용 압축"""


def unpack(b):
    p = 0
    flags = (b[0] << 8) | b[1]
    p = 2
    if flags & 0x0100:   # 압축 전 크기 필드 추가
        p += 3
    big = flags & 0x8000
    n = 4 if big else 3
    size = int.from_bytes(b[p:p + n], 'big'); p += n
    out = bytearray()
    while True:
        c0 = b[p]
        if c0 < 0x80:
            c1 = b[p + 1]; p += 2
            lit = c0 & 3; out += b[p:p + lit]; p += lit
            cnt = ((c0 & 0x1c) >> 2) + 3; off = ((c0 & 0x60) << 3) + c1 + 1
        elif c0 < 0xc0:
            c1, c2 = b[p + 1], b[p + 2]; p += 3
            lit = c1 >> 6; out += b[p:p + lit]; p += lit
            cnt = (c0 & 0x3f) + 4; off = ((c1 & 0x3f) << 8) + c2 + 1
        elif c0 < 0xe0:
            c1, c2, c3 = b[p + 1], b[p + 2], b[p + 3]; p += 4
            lit = c0 & 3; out += b[p:p + lit]; p += lit
            cnt = ((c0 & 0x0c) << 6) + c3 + 5; off = ((c0 & 0x10) << 12) + (c1 << 8) + c2 + 1
        elif c0 < 0xfc:
            p += 1; lit = ((c0 & 0x1f) << 2) + 4
            out += b[p:p + lit]; p += lit; continue
        else:
            p += 1; lit = c0 & 3; out += b[p:p + lit]; break
        for _ in range(cnt):
            out.append(out[-off])
    assert len(out) == size, (len(out), size)
    return bytes(out)


def pack(d):
    """리터럴 블록만 사용 (게임 디코더와 호환되는 가장 단순한 형태)"""
    out = bytearray(b'\x10\xfb') + len(d).to_bytes(3, 'big')
    p = 0
    while len(d) - p >= 4:
        n = min(112, (len(d) - p) & ~3)
        out.append(0xe0 + (n - 4) // 4); out += d[p:p + n]; p += n
    out.append(0xfc + (len(d) - p)); out += d[p:]
    return bytes(out)


def compress(d):
    """해시 체인 LZ 압축 (짧은/중간/긴 복사 명령 사용)"""
    n = len(d)
    out = bytearray(b'\x10\xfb') + n.to_bytes(3, 'big')
    head = {}; prev = [-1] * n
    lit0 = 0; i = 0

    def insert(p):
        if p + 3 <= n:
            h = d[p:p + 3]; prev[p] = head.get(h, -1); head[h] = p

    while i < n:
        best_len = 0; best_off = 0
        if i + 3 <= n:
            c = head.get(d[i:i + 3], -1); tries = 64
            while c >= 0 and tries and i - c <= 131072:
                l = 3
                while i + l < n and l < 1028 and d[c + l] == d[i + l]: l += 1
                off = i - c
                ok = (l >= 3 and off <= 1024) or (l >= 4 and off <= 16384) or l >= 5
                if ok and l > best_len: best_len, best_off = l, off
                c = prev[c]; tries -= 1
        if best_len:
            # 남은 리터럴(0~3)을 복사 명령에 붙인다
            while i - lit0 > 3:
                k = min(112, (i - lit0) & ~3); out.append(0xe0 + (k - 4) // 4); out += d[lit0:lit0 + k]; lit0 += k
            lit = i - lit0; l = best_len; o = best_off - 1
            if l <= 10 and best_off <= 1024:
                out += bytes([((o >> 3) & 0x60) | ((l - 3) << 2) | lit, o & 0xff])
            elif l <= 67 and best_off <= 16384:
                out += bytes([0x80 | (l - 4), (lit << 6) | (o >> 8), o & 0xff])
            else:
                out += bytes([0xc0 | ((o >> 16) << 4) | (((l - 5) >> 8) << 2) | lit, (o >> 8) & 0xff, o & 0xff, (l - 5) & 0xff])
            out += d[lit0:i]
            for p in range(i, i + l): insert(p)
            i += l; lit0 = i
        else:
            insert(i); i += 1
    while n - lit0 > 3:
        k = min(112, (n - lit0) & ~3); out.append(0xe0 + (k - 4) // 4); out += d[lit0:lit0 + k]; lit0 += k
    out.append(0xfc + (n - lit0)); out += d[lit0:]
    return bytes(out)
