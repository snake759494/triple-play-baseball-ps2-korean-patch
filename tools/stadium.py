"""구장 정보 표(ELF 0x3be674, 128바이트 x 31): 도시·팀·바닥 종류·설명 10줄 포인터

설명 첫 줄부터 이어지는 원래 줄들의 영역에 [도시, 팀, 줄1..] 을 차례로 채우고 포인터를 바꾼다.
"""
import struct
import elfstrings

BASE = 0xff000
TABLE = 0x2bf674          # 파일 오프셋
SURF = {'Blue': '블루', 'Natural': '천연', 'Artificial': '인조', 'Grass': '잔디', 'Turf': '잔디'}


def _str(elf, a):
    o = a - BASE
    return bytes(elf[o:elf.index(b'\0', o)])


def apply(elf, rows, enc, log=print):
    errs = 0
    done = {}
    for i, (city, team, desc) in rows.items():
        ro = TABLE + i * 128
        w = list(struct.unpack_from('<32I', elf, ro))
        start = w[17]
        ds = [p for p in w[17:27] if start <= p < start + 800]
        end = max(p + len(_str(elf, p)) + 1 for p in ds)
        lines = elfstrings.wrap(desc, 10)
        if len(lines) > 10:
            log(f'  [구장 {i}] 줄 수 초과 {len(lines)}'); errs += 1; continue
        items = [enc.enc(city)] + ([enc.enc(team)] if team != '--' else []) + [enc.enc(l) for l in lines] + [b' ']
        need = sum(len(x) + 1 for x in items)
        if need > end - start:
            log(f'  [구장 {i}] 영역 부족 {need}/{end - start}'); errs += 1; continue
        elf[start - BASE:end - BASE] = bytes(end - start)
        pos = start; addr = []
        for x in items:
            elf[pos - BASE:pos - BASE + len(x)] = x; addr.append(pos); pos += len(x) + 1
        k = 0
        w[1] = addr[k]; k += 1
        if team != '--': w[2] = addr[k]; k += 1
        blank = addr[-1]
        ls = addr[k:-1]
        for j in range(10):
            w[17 + j] = ls[j] if j < len(ls) else blank
        # 바닥 종류(여러 레코드 공유): 처음 나온 자리에 한 번만 기록
        for f in (4, 5):
            a = w[f]
            if a not in done:
                s = _str(elf, a).decode('latin1')
                if s in SURF:
                    b = enc.enc(SURF[s]); n, mx = elfstrings.avail(elf, a - BASE)
                    if len(b) <= mx:
                        elf[a - BASE:a - BASE + mx + 1] = b + bytes(mx + 1 - len(b))
                    else:
                        log(f'  [구장 바닥 길이 초과] {s}'); errs += 1
                done[a] = True
        struct.pack_into('<32I', elf, ro, *w)
    return errs


def load(path):
    rows = {}
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'): continue
        i, city, team, desc = line.split('|', 3)
        rows[int(i)] = (city, team, desc)
    return rows


def chars(rows):
    return ''.join(c + t + d for c, t, d in rows.values()) + ''.join(SURF.values())
