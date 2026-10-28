"""트리플 플레이 베이스볼(북미판) 한글 패치 빌드

python tools/build.py  ->  'Triple Play Baseball (Korean).bin/.cue' (원본과 같은 폴더)
"""
import os, sys, re, csv, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdbuild, textdb, kfont, elfpatch, big, refpack, sfn, stadium, players

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = lambda *a: os.path.join(ROOT, *a)
SRC = P('Triple Play Baseball (USA).bin')
DST = P('Triple Play Baseball (Korean).bin')
TR = P('translation')
INGAME_ELF = [(0x3eb458, 0x3ebfb0), (0x3f21d8, 0x3f4d20), (0x3ff318, 0x400300)]
INGAME_FONTS = {'TAHOMA11', 'ARIAL10B', 'ARIAL20B', 'TAHOMA14'}
FONTS = ['TAHOMA14', 'TAHOMA11', 'AURORA20', 'AURO20B', 'AUR11', 'ARIAL20B', 'ARIAL11', 'ARIAL10B']
# FEL 좌표 보정 (파일, 요소) -> x 이동: 한글 라벨·값이 상자 테두리·구분선에 붙는 곳
FEL_DX = {('fes_seasonteam.fel', k): 4 for k in ('FOUNDED', 'RECORD2000', 'SERIESTITLES', 'DEVISIONTITLES', 'LASTTITLE2')}
FEL_DX.update({('fes_seasonteam.fel', k): -3 for k in ('FOUNDYEAR', 'RECORD', 'SERIES', 'DIVISION', 'LASTTITLE')})


def read_src(name, keyint=False):
    """번역 원본: 키|번역  (# 주석, \n 은 줄바꿈)"""
    out = {}
    for line in open(os.path.join(TR, 'src', name), encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'): continue
        k, t = line.split('|', 1)
        out[k] = t
    return out


def src_files():
    d = cdbuild.Disc(SRC) if False else None
    import shutil
    disc = cdbuild.Disc.__new__(cdbuild.Disc)
    disc.f = open(SRC, 'rb'); disc.n = os.path.getsize(SRC) // cdbuild.RAW
    ents = {e[0]: e for e in cdbuild.walk(disc)}
    def get(name):
        _, lba, size, _, _ = ents[name]
        return disc.read(lba, (size + 2047) // 2048)[:size]
    return get


class Enc:
    def __init__(s): s.map = {}
    def add(s, text):
        for ch in text:
            if ord(ch) >= 0x80 and ch not in s.map: s.map[ch] = len(s.map)
    def enc(s, text):
        out = bytearray()
        for ch in text:
            if ord(ch) < 0x80: out.append(ord(ch))
            else:
                c = kfont.code_of(s.map[ch]); out += bytes([c >> 8, c & 0xff])
        return bytes(out)


def unesc(t): return t.replace('\n', '\n')


def check_fmt(src, dst, where):
    f = lambda t: re.findall(r'%[-+ #0]*\d*(?:\.\d+)?[hlL]*[diouxXeEfgGcsp%]', t)
    if f(src) != f(dst):
        print(f'  [서식 불일치] {where}: {src!r} -> {dst!r}'); return 1
    return 0


def main():
    get = src_files()
    out = {}; enc = Enc(); errs = 0
    # 1) 문자열 테이블
    tables = {}
    for fn, tsv in [('DATA/ZFETEXT.ENG', 'zfetext.txt'), ('DATA/ZIGTEXT.ENG', 'zigtext.txt')]:
        strs = textdb.read(get(fn)); tr = read_src(tsv)
        new = []
        for i, s in enumerate(strs):
            k = str(i)
            if k in tr:
                t = unesc(tr[k]); errs += check_fmt(s.decode('latin1'), t, f'{tsv}:{k}')
                enc.add(t); new.append(t)
            else: new.append(s.decode('latin1'))
        tables[fn] = new
    # 경기 중 문자(경기 중 폰트에 우선 수록)
    ingame = set()
    for t in read_src('zigtext.txt').values(): ingame.update(t)
    for k, t in read_src('elf.txt').items():
        if any(a <= int(k, 16) < b for a, b in INGAME_ELF): ingame.update(t)
    # 2) FEL 레이아웃
    fel_tr = read_src('felayout.txt')   # key = 원문
    felbig = big.read(get('ART/FRONTEND/FELAYOUT.BIG'))
    fel_new = []
    for name, d in felbig:
        txt = refpack.unpack(d).decode('latin1')
        lines = txt.split('\r\n')
        for li, l in enumerate(lines):
            s = l.lstrip(' ')
            if s[:3] in ('TX:', 'TB:'):
                p = s[3:].split(',')
                if p[9] in fel_tr:
                    t = fel_tr[p[9]]; enc.add(t); p[9] = t
                    lines[li] = l[:len(l) - len(s)] + s[:3] + ','.join(p)
                    if name == 'fes_ingame.fel': ingame.update(t)
        # 그림자 줄(이름+숫자)은 본문 줄과 같은 폰트로 맞춘다(폰트가 다르면 한글 폭이 어긋남)
        tx = {}
        for li, l in enumerate(lines):
            s = l.lstrip(' ')
            if s[:3] == 'TX:': tx[s[3:].split(',')[0]] = li
        for nm_, li in tx.items():
            base = re.sub(r'\d+$', '', nm_)
            if base != nm_ and base in tx:
                l = lines[li]; s = l.lstrip(' '); p = s[3:].split(',')
                q = lines[tx[base]].lstrip(' ')[3:].split(',')
                if p[9] == q[9] and p[10] != q[10]:
                    p[10] = q[10]; lines[li] = l[:len(l) - len(s)] + 'TX:' + ','.join(p)
        for li, l in enumerate(lines):
            s = l.lstrip(' ')
            if s[:3] in ('TX:', 'TB:'):
                p = s[3:].split(',')
                dx = FEL_DX.get((name, p[0]))
                if dx:
                    p[2] = str(int(p[2]) + dx); lines[li] = l[:len(l) - len(s)] + s[:3] + ','.join(p)
        fel_new.append((name, '\r\n'.join(lines)))
    # 3) ELF 문자열
    elf = bytearray(get('SLUS_201.68'))
    elf_tr = read_src('elf.txt')     # key = 16진 주소
    for t in elf_tr.values(): enc.add(unesc(t))
    st_rows = stadium.load(os.path.join(TR, 'src', 'stadium.txt'))
    enc.add(stadium.chars(st_rows))
    # 선수 이름(이름 글자는 폰트 수록 우선순위가 가장 낮음)
    base_chars = set(enc.map)
    first = read_src('first.txt'); last = read_src('last.txt')
    for t in list(first.values()) + list(last.values()): enc.add(t)
    print(f'한글 글자 수: {len(enc.map)} (이름 전용 {len(set(enc.map) - base_chars)})')
    # 인코딩
    for fn, strs in tables.items():
        out[fn] = textdb.write([enc.enc(t) if isinstance(t, str) else t for t in strs])
    out['ART/FRONTEND/FELAYOUT.BIG'] = big.write([(n, refpack.compress(enc.enc(t))) for n, t in fel_new])
    errs += stadium.apply(elf, st_rows, enc)
    # 포지션 약어(0x3e2e88~): 원문은 내부 키로 쓰여 그대로 두고, 화면 표시용 표(PositionAbv)만 한글 사본으로
    POS = {'C': '포', '1B': '1루', '2B': '2루', 'SS': '유격', '3B': '3루', 'LF': '좌익', 'CF': '중견', 'RF': '우익',
           'RP': '구원', 'SP': '선발', 'CP': '마무리', 'P': '투', 'DH': '지명', '1B/3B': '1/3루', '2B/SS': '2/유격', 'OF': '외야', 'P/OF': '투/외'}
    copies = []
    for k in range(0x2496ec, 0x2496ec + 0x48, 4):   # PositionAbv 표
        a = struct.unpack_from('<I', elf, k)[0]
        if not 0x3dce80 <= a < 0x412380: break
        s0 = elf[a - 0xff000:elf.index(b'\0', a - 0xff000)].decode('latin1')
        if s0 in POS: copies.append((k, POS[s0])); enc.add(POS[s0])
    # 경기 중 로스터의 포지션·타격 손 표: 2B/3B/R 을 기록 약어(2루타/3루타/득점)와 같은 문자열로 공유하므로 사본으로
    HAND = dict(POS, PH='대타', R='우', L='좌', S='양')
    # 같은 화면의 기록 머리글 표(AVG/HR/RBI/SB)
    STAT = {'AVG': '타율', 'HR': '홈런', 'RBI': '타점', 'SB': '도루'}
    for k in list(range(0x27eb60, 0x27eb9c, 4)) + list(range(0x27e778, 0x27e78c, 4)) + list(range(0x27eba0, 0x27ec3c, 0x18)):
        a = struct.unpack_from('<I', elf, k)[0]
        if not 0x3dce80 <= a < 0x412380: continue
        s0 = elf[a - 0xff000:elf.index(b'\0', a - 0xff000)].decode('latin1')
        t = (HAND if k < 0x27eb9c and k >= 0x27eb60 else STAT).get(s0)
        if t: copies.append((k, t)); enc.add(t)
    # FESRostInfoBox::SetInfo 투수 손 표시: a2 = 좌완 ? "L" : "R"(R은 기록 약어 '득점'과 공유)
    for va, old, t in [(0x19e22c, 0x2446b5f0, '좌'), (0x19e230, 0x244690f8, '우')]:
        assert struct.unpack_from('<I', elf, va - 0xff000)[0] == old
        copies.append((('c', va, 0x3f), t)); enc.add(t)
    errs += elfstrings.apply(elf, elf_tr, enc, copies=copies)
    out['SLUS_201.68'] = elfpatch.patch(bytes(elf))
    pb, e = players.apply(get('DATA/ZPLAYERS.ATT'), first, last, enc); errs += e
    out['DATA/ZPLAYERS.ATT'] = pb
    zs = bytearray(get('DATA/ZSTATIC.BIG'))   # C0FB 묶음 안의 zplayers.att(비압축, 크기 동일)
    o, n = int.from_bytes(zs[6:9], 'big'), int.from_bytes(zs[9:12], 'big')
    assert zs[12:24] == b'zplayers.att'
    pz, e = players.apply(bytes(zs[o:o + n]), first, last, enc); errs += e
    zs[o:o + n] = pz; out['DATA/ZSTATIC.BIG'] = bytes(zs)
    # 3.5) 메뉴 라벨 이미지
    import eagl, imgko
    for o, names in imgko.LABELS.items():
        fn = f'ART/FRONTEND/{o}.O'; b = get(fn)
        ts = [t for t in eagl.parse(b) if t.name in names]
        boxes = {}   # 같은 라벨·크기의 레이어는 공통 영역으로(겹쳐 그려지므로 어긋나면 안 됨)
        for t in ts:
            bx = imgko.style(eagl.decode(b, t), (o, t.name) in imgko.PLAIN)[3]
            k = (names[t.name], t.w, t.h)
            o0 = boxes.get(k, bx); boxes[k] = (min(o0[0], bx[0]), min(o0[1], bx[1]), max(o0[2], bx[2]), max(o0[3], bx[3]))
        for t in ts:
            b = eagl.encode(b, t, imgko.render(eagl.decode(b, t), names[t.name], (o, t.name) in imgko.PLAIN, boxes[(names[t.name], t.w, t.h)]))
        out[fn] = b
    # 4) 폰트
    chars = sorted(((i, c) for c, i in enc.map.items()))
    os.makedirs(P('work', 'preview'), exist_ok=True)
    from PIL import Image
    for nm in FONTS:
        raw = get(f'DATA/{nm}.SFN')
        pri = sorted(chars, key=lambda ic: (ic[1] not in base_chars, ic[0]))
        b, img = kfont.build(nm, raw, pri)
        out[f'DATA/{nm}.SFN'] = b
        Image.fromarray((img * 17).astype('uint8')).save(P('work', 'preview', nm + '.png'))
        print(f'  {nm}: {len(raw)} -> {len(b)}  텍스처 {img.shape[1]}x{img.shape[0]}')
    if errs: print(f'오류 {errs}건')
    cdbuild.build(SRC, DST, out)
    open(P('Triple Play Baseball (Korean).cue'), 'w').write(
        'FILE "Triple Play Baseball (Korean).bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
    widescreen.write(out['SLUS_201.68'], ROOT, '한글 패치')
    widescreen.write(get('SLUS_201.68'), ROOT, None)
    print('완료:', DST)


import elfstrings, widescreen
if __name__ == '__main__':
    main()
