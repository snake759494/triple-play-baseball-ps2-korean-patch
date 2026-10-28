"""선수 이름 칸 찾기: 16바이트(이름) + 16바이트(성), 각각 ASCII 이름 + 0 채움"""
import re

NAME = re.compile(rb"[A-Za-z][A-Za-z .'\-]*")


def field(b, p):
    s = b[p:p + 16]
    m = NAME.match(s)
    if not m or any(s[m.end():]): return None
    return m.group().decode()


def pairs(b):
    out = []
    p = 0
    while p + 32 <= len(b):
        f = field(b, p)
        if f is not None and (p == 0 or b[p - 1] == 0 or True):
            l = field(b, p + 16)
            if l is not None and len(f) >= 1 and len(l) >= 2:
                out.append((p, f, l)); p += 32; continue
        p += 4
    return out


def apply(b, first, last, enc, log=print):
    """이름 칸을 한글로 바꾼다(16바이트 칸, NUL 포함). 반환: (새 바이트, 오류 수)"""
    b = bytearray(b); errs = 0; miss = set()
    for p, f, l in pairs(bytes(b)):
        for off, s, tab in ((p, f, first), (p + 16, l, last)):
            t = tab.get(s)
            if t is None:
                miss.add(s); continue
            e = enc.enc(t)
            if len(e) > 15:
                log(f'  [이름 길이 초과] {s} -> {t} ({len(e)})'); errs += 1; continue
            b[off:off + 16] = e + bytes(16 - len(e))
    if miss: log(f'  [이름 표기 없음] {sorted(miss)[:20]} ... {len(miss)}개')
    return bytes(b), errs
