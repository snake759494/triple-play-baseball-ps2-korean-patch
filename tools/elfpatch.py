"""ELF 패치: FONT_buildmesh 의 1바이트 읽기를 2바이트(선행 0x80 이상) 해석으로 확장

훅 위치 0x2d09b8 (lbu s3,(s4); addiu s4,s4,1) -> 미사용 함수 FONT_drawtextw(0x2d1100) 자리로 점프.
뒤 바이트가 0 이면 결합하지 않아 문자열 끝을 넘지 않는다.
"""
import struct

BASE = 0xff000   # vaddr - file offset
R = dict(zero=0, v0=2, s3=19, s4=20)


def I(op, rs, rt, imm): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xffff)
def J(op, tgt): return (op << 26) | ((tgt >> 2) & 0x3ffffff)
def SLL(rd, rt, sa): return (R[rt] << 16) | (R[rd] << 11) | (sa << 6)
def OR(rd, rs, rt): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | 0x25
NOP = 0
def BR(op, rs, rt, at, to): return I(op, rs, rt, (to - at - 4) >> 2)

HOOK = 0x2d09b8
CAVE = 0x2d1100
BACK = 0x2d09c0


def patch(elf):
    b = bytearray(elf)
    def put(a, ws):
        for i, w in enumerate(ws):
            struct.pack_into('<I', b, a - BASE + i * 4, w)
    assert struct.unpack_from('<I', b, HOOK - BASE)[0] == I(0x24, 's4', 's3', 0)   # lbu s3,0(s4)
    put(HOOK, [J(2, CAVE), I(0x24, 's4', 's3', 0)])
    c = CAVE
    done = c + 0x28
    put(c, [
        I(9, 's4', 's4', 1),             # addiu s4,s4,1
        I(11, 's3', 'v0', 0x80),         # sltiu v0,s3,0x80
        BR(5, 'v0', 'zero', c + 8, done),  # bnez v0,done
        NOP,
        I(0x24, 's4', 'v0', 0),          # lbu v0,0(s4)
        BR(4, 'v0', 'zero', c + 0x14, done),  # beqz v0,done
        NOP,
        SLL('s3', 's3', 8),
        OR('s3', 's3', 'v0'),
        I(9, 's4', 's4', 1),             # addiu s4,s4,1
    ])
    put(done, [J(2, BACK), NOP])
    # 폰트 캐시: 텍스처 한 변 상한 256 -> 512, 블록 0x20 x 32KB -> 0x10 x 128KB
    for a, old, new in [(0x2b27c8, 0x28a30100, 0x28a30200), (0x2b27d8, 0x24020100, 0x24020200),
                        (0x25f3a0, 0x24040020, 0x24040010), (0x25f3a8, 0x24050100, 0x24050400)]:
        assert struct.unpack_from('<I', b, a - BASE)[0] == old
        struct.pack_into('<I', b, a - BASE, new)
    # FONT_allocmesha: 정점 버퍼를 문자열 바이트 수 x 256 -> x 128 (글리프당 실제 사용량 0x80).
    # 한글은 2바이트 = 1글리프라 x 256 이면 버퍼가 두 배가 되어 경기 HUD 폰트 힙이 바닥난다.
    assert struct.unpack_from('<I', b, 0x2d1368 - BASE)[0] == 0x00122200   # sll a0,s2,8
    struct.pack_into('<I', b, 0x2d1368 - BASE, 0x001221c0)                  # sll a0,s2,7
    return bytes(b)
