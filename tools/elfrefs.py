"""ELF 안의 문자열 참조 탐색: 데이터 포인터(u32)와 코드의 lui/addiu 쌍"""
import struct

BASE = 0xff000
TEXT0, TEXT1 = 0x100000, 0x32aa6c
DATA0, DATA1 = 0x32ab00, 0x412b00


def scan(elf):
    """반환: {주소: [('d', 파일오프셋) | ('c', addiu주소, lui주소)]}"""
    refs = {}
    n = (TEXT1 - TEXT0) // 4
    ws = struct.unpack_from('<%dI' % n, elf, TEXT0 - BASE)
    last = {}   # reg -> (hi, lui 주소)
    clear_next = False
    for i, w in enumerate(ws):
        if clear_next:
            clear_next = False; pending = True
        else:
            pending = False
        a = TEXT0 + i * 4
        op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31; imm = w & 0xffff
        if op == 0x0f:   # lui
            last[rt] = (imm, a); continue
        if op == 0x09 and rs in last:   # addiu rt, rs, imm
            hi, la = last[rs]
            if a - la <= 0x200:
                t = ((hi << 16) + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xffffffff
                refs.setdefault(t, []).append(('c', a, la))
        # rt 덮어쓰기 추적(대략): 대부분 I형 명령의 목적지는 rt
        if op in (0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x20, 0x21, 0x23, 0x24, 0x25, 0x37):
            if rt in last and not (op == 0x09 and rs == rt): last.pop(rt, None)
            elif op == 0x09 and rs == rt and rt in last: last.pop(rt, None)
        elif op == 0:   # R형: rd
            rd = (w >> 11) & 31; last.pop(rd, None)
        if op in (2, 3) or (op == 0 and (w & 0x3f) in (8, 9)) or op in (4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17) or (op == 1):
            clear_next = True      # 분기/점프: 지연 슬롯까지는 유지
        if pending:
            last.clear()
    nd = (DATA1 - DATA0) // 4
    dw = struct.unpack_from('<%dI' % nd, elf, DATA0 - BASE)
    for i, w in enumerate(dw):
        if DATA0 <= w < DATA1:
            refs.setdefault(w, []).append(('d', DATA0 - BASE + i * 4))
    return refs
