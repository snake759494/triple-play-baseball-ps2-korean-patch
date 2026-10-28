"""ELF 내부 문자열 교체

- 들어가면 제자리(원래 길이 + 뒤따르는 0 패딩 안).
- 넘치면 재배치: 로그 전용 문자열 자리와 제자리 교체로 남은 자리를 빈 공간으로 쓰고
  데이터 포인터(u32)와 코드의 addiu 하위 16비트를 고친다(lui 는 그대로 두므로 같은 64KB 구간 안에서만).
- 문단(구장 소개): 'G:시작주소-끝주소' 키로 여러 줄 슬롯에 자동 줄나눔해서 넣는다.
"""
import struct
import elfrefs, elfpool

BASE = 0xff000
LINE_W = 46   # 문단 한 줄 최대 표시 폭(반각 기준, 한글 1자 = 2)


def avail(elf, off):
    e = elf.index(b'\0', off)
    z = e
    while z < len(elf) and elf[z] == 0: z += 1
    return e - off, z - off - 1     # 원래 길이, 최대 길이(NUL 제외)


def hi_of(a): return ((a + 0x8000) >> 16) & 0xffff


def wrap(text, n):
    """반각 폭 기준 LINE_W 로 줄나눔"""
    words = text.split(' '); lines = []; cur = ''
    w = lambda s: sum(2 if ord(c) >= 0x80 else 1 for c in s)
    for wd in words:
        t = (cur + ' ' + wd) if cur else wd
        if w(t) > LINE_W and cur:
            lines.append(cur); cur = wd
        else:
            cur = t
    if cur: lines.append(cur)
    return lines


def apply(elf, tr, enc, log=print, copies=()):
    """copies: [(포인터 파일오프셋, 한글)] 원문은 두고 그 포인터만 새 사본으로 바꾼다"""
    errs = 0
    refs = elfrefs.scan(bytes(elf))
    jobs = []   # (주소, 원문, 인코딩 바이트)
    for k, t in tr.items():
        if k.startswith('G:'):
            a0, a1 = (int(x, 16) for x in k[2:].split('-'))
            slots = []
            a = a0
            while a <= a1:
                n, mx = avail(elf, a - BASE)
                slots.append(a); a += n + 1
                while elf[a - BASE] == 0: a += 1
            lines = wrap(t, len(slots))
            if len(lines) > len(slots):
                log(f'  [문단 줄 수 초과] {k}: {len(lines)}/{len(slots)}'); errs += 1; continue
            lines += [''] * (len(slots) - len(lines))
            for a, l in zip(slots, lines):
                n, _ = avail(elf, a - BASE)
                jobs.append((a, elf[a - BASE:a - BASE + n].decode('latin1'), enc.enc(l)))
            continue
        a = int(k, 16); off = a - BASE
        n, mx = avail(elf, off)
        cur = elf[off:off + n].decode('latin1')
        jobs.append((a, cur, enc.enc(t.replace('\\n', '\n'))))
    targets = {a for a, _, _ in jobs}
    pool = [(a, n) for a, n in elfpool.find(bytes(elf), refs) if a not in targets]
    later = []
    for a, cur, b in jobs:
        off = a - BASE
        n, mx = avail(elf, off)
        if len(b) <= mx:
            elf[off:off + mx + 1] = b + bytes(mx + 1 - len(b))
            free = mx - len(b) - 1
            if free >= 4: pool.append((a + len(b) + 1, free))
        else:
            later.append((a, cur, b))
    moved = 0
    for a, cur, b in later:
        rs = refs.get(a, [])
        if not rs:
            log(f'  [ELF 길이 초과·참조 없음] {a:x}: {len(b)}/{avail(elf, a - BASE)[1]} {cur!r}'); errs += 1; continue
        his = {hi_of(a)} if any(r[0] == 'c' for r in rs) else None
        slot = None
        for i, (pa, pn) in enumerate(pool):
            if pn >= len(b) and (his is None or hi_of(pa) in his):
                slot = i; break
        if slot is None:
            log(f'  [재배치 공간 부족] {a:x}: {len(b)}바이트 {cur!r}'); errs += 1; continue
        pa, pn = pool[slot]
        po = pa - BASE
        elf[po:po + len(b) + 1] = b + b'\0'
        rest = pn - len(b) - 1
        if rest >= 4: pool[slot] = (pa + len(b) + 1, rest)
        else: pool.pop(slot)
        for r in rs:
            if r[0] == 'd':
                struct.pack_into('<I', elf, r[1], pa)
            else:
                ao = r[1] - BASE
                w = struct.unpack_from('<I', elf, ao)[0]
                struct.pack_into('<I', elf, ao, (w & 0xffff0000) | (pa & 0xffff))
        moved += 1
    for po, t in copies:
        b = enc.enc(t)
        slot = next((i for i, (pa, pn) in enumerate(pool) if pn >= len(b)), None)
        if slot is None:
            log(f'  [사본 공간 부족] {t}'); errs += 1; continue
        pa, pn = pool[slot]
        elf[pa - BASE:pa - BASE + len(b) + 1] = b + b'\0'
        rest = pn - len(b) - 1
        if rest >= 4: pool[slot] = (pa + len(b) + 1, rest)
        else: pool.pop(slot)
        struct.pack_into('<I', elf, po, pa)
    log(f'  ELF 문자열: {len(jobs)}개 (재배치 {moved}), 남은 빈 공간 {sum(n for _, n in pool)}바이트')
    return errs
