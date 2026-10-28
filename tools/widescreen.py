"""PCSX2 16:9 와이드 패치(pnach) 생성

EAGL::ViewPort::SetPerspective(0x2bdd28)의 투영 행렬에서 m00 = 1/t 를 0.75/t 로 바꿔 가로 시야를 4/3배 넓힌다.
  0x2bde10 lui at,0x3f80 -> lui at,0x3f40     (분자 1.0 -> 0.75, f1 = 0.75/t)
  0x2bde34 lwc1 f20,0x30(sp) -> div.s f0,f0,f20 (m11 = -aspect/t 는 원래 값 유지)
  0x2bde38 mul.s f0,f0,f1 -> lwc1 f20,0x30(sp)  (밀린 레지스터 복원)
파일 이름의 CRC는 PCSX2 방식(ELF 전체 32비트 단어 XOR)이라 실행파일이 바뀌면 다시 만들어야 한다.
"""
import glob, os, struct

BASE = 0xff000
PATCH = [(0x2bde10, 0x3c013f80, 0x3c013f40), (0x2bde34, 0xc7b40030, 0x46140003), (0x2bde38, 0x46010002, 0xc7b40030)]


def crc(elf):
    c = 0
    for w in struct.unpack_from('<%dI' % (len(elf) // 4), elf): c ^= w
    return c


def write(elf, root, tag):
    """tag: None = 원본, 문자열 = 제목 뒤에 붙일 말. 같은 대상의 예전 CRC 파일은 지운다."""
    for a, old, _ in PATCH:
        assert struct.unpack_from('<I', elf, a - BASE)[0] == old, hex(a)
    title = 'Triple Play Baseball (USA)' + (f' {tag}' if tag else '')
    name = 'SLUS-20168_%08X.pnach' % crc(elf)
    for f in glob.glob(os.path.join(root, 'SLUS-20168_*.pnach')):
        if os.path.basename(f) != name and open(f, encoding='utf-8').readline().strip() == f'gametitle={title} [SLUS-20168]':
            os.remove(f)
    lines = [f'gametitle={title} [SLUS-20168]', '', '[Widescreen 16:9]', 'gsaspectratio=16:9', 'author=Claude',
             'description=3D 원근 투영 가로 시야를 4/3 넓힘(EAGL ViewPort::SetPerspective). 2D HUD는 늘어남.']
    lines += ['patch=1,EE,%08x,word,%08x' % (a, new) for a, _, new in PATCH]
    with open(os.path.join(root, name), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('  와이드 패치:', name)
    return name
