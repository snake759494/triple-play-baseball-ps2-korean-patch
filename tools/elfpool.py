"""재배치용 빈 공간: 로그 출력 함수(printf 류)에만 넘겨지는 개발용 문자열 자리"""
import re, struct
import elfrefs

BASE = elfrefs.BASE
LOGF = {0x3230c0, 0x2156e8, 0x215760, 0x215820, 0x2158e0, 0x30d3b0, 0x321518, 0x323080, 0x320e40}


def find(elf, refs, exclude=()):
    pool = []
    seg = elf[0x3dce80 - BASE:0x412380 - BASE]
    for m in re.finditer(rb'(?<=\x00)[\x09\x0a\x20-\x7e]{6,}\x00+', seg):
        a = 0x3dce80 + m.start()
        if a in exclude: continue
        rs = refs.get(a)
        if not rs or any(r[0] != 'c' for r in rs): continue
        ok = True
        for _, ad, _ in rs:
            o = ad - BASE
            ws = struct.unpack_from('<10I', elf, o - 8)
            if not any((w >> 26) == 3 and ((w & 0x3ffffff) << 2) in LOGF for w in ws):
                ok = False; break
        if ok:
            pool.append((a, len(m.group()) - 1))   # 마지막 NUL 하나는 남김
    return pool
