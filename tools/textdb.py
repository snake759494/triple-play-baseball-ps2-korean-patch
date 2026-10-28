"""ZFETEXT.ENG / ZIGTEXT.ENG: u32 오프셋 표 + NUL 종료 문자열"""
import struct


def read(b):
    n = struct.unpack_from('<I', b, 0)[0] // 4
    offs = struct.unpack_from('<%dI' % n, b, 0)
    return [b[o:b.index(b'\0', o)] for o in offs]


def write(strs):
    n = len(strs); pos = n * 4; offs = []; body = bytearray()
    for s in strs:
        offs.append(pos + len(body)); body += s + b'\0'
    return struct.pack('<%dI' % n, *offs) + bytes(body)
