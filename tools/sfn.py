import struct
import numpy as np
class SFN:
    def __init__(s,b):
        s.raw=b
        s.hdr=bytearray(b[:0x20])
        s.size,s.ver,s.n,s.flags=struct.unpack_from('<IHHI',b,4)
        s.asc,s.desc=struct.unpack_from('<bb',b,0x12)
        s.goff,s.koff,s.toff=struct.unpack_from('<III',b,0x14)
        s.glyphs=[]
        for i in range(s.n):
            c,w,h,u,v,adv,xo,yo,pad=struct.unpack_from('<HBBHHbbbB',b,s.goff+i*12)
            s.glyphs.append([c,w,h,u,v,adv,xo,yo,pad])
        s.extra=b[s.goff+s.n*12:s.toff]   # name etc
        t=s.toff
        s.ttype,s.tw,s.th=struct.unpack_from('<IHH',b,t)
        s.thdr=b[t:t+16]
        px=np.frombuffer(b,np.uint8,s.tw*s.th//2,t+16)
        img=np.zeros((s.th,s.tw),np.uint8)
        img.reshape(-1)[0::2]=px&15; img.reshape(-1)[1::2]=px>>4
        s.img=img
        s.kern=b[s.koff:] if s.koff else b''
        s.tail=b[t+16+s.tw*s.th//2:s.koff] if s.koff else b[t+16+s.tw*s.th//2:]
