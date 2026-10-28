"""SFN(FNTS) 폰트에 한글 글리프 추가

글리프 표: 12바이트 [코드 u16, 폭, 높이, u u16, v u16, 전진폭 s8, x오프셋 s8, y오프셋 s8, 0]
엔진이 16비트 코드를 이진 탐색하므로 코드 오름차순으로 정렬한다.
텍스처는 4bpp 농도(0~15). 원본 그림은 그대로 두고 아래에 한글을 채운다.
"""
import os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sfn as sfnmod

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
T = lambda n: os.path.join(ROOT, n)
NANUM = {w: T(f'NanumSquareNeo-{w}.ttf') for w in ('aLt', 'bRg', 'cBd', 'dEb', 'eHv')}
GALMURI = T('Galmuri11.ttf'); GALMURI_B = T('Galmuri11-Bold.ttf')


def code_of(idx):
    """한글 글자 번호 -> 2바이트 코드 (선행 0x81~, 후행 0x80~0xFF)"""
    return ((0x81 + idx // 128) << 8) | (0x80 + idx % 128)


# 원본 폰트별 설정: (서체, 한글 높이(px), 기울임 비율, 픽셀체 여부, 굵게 번짐)
CFG = {
    'ARIAL10B': (GALMURI_B, None, 0.0, True),
    'ARIAL11': (GALMURI, None, 0.0, True),
    'TAHOMA11': (GALMURI, None, 0.0, True),
    'AUR11': (GALMURI_B, None, 0.18, True),
    'TAHOMA14': (NANUM['bRg'], 13, 0.0, False),
    'ARIAL20B': (NANUM['eHv'], 16, 0.0, False),
    'AURORA20': (NANUM['eHv'], 15, 0.2, False),
    'AURO20B': (NANUM['eHv'], 15, 0.2, False),
}


def render(font, ch, px, shear, pixel):
    S = px * 3
    im = Image.new('L', (S, S), 0)
    ImageDraw.Draw(im).text((px, px * 2), ch, font=font, fill=255, anchor='ls')
    if shear:
        im = im.transform(im.size, Image.AFFINE, (1, shear, -shear * px * 2, 0, 1, 0), Image.BICUBIC if not pixel else Image.NEAREST)
    a = np.array(im)
    if pixel:
        a = np.where(a >= 128, 255, 0)
    return a, px * 2   # 배열, 기준선 y


def build(name, raw, chars, fit256=False):
    """chars: [(idx, ch)] -> 새 SFN 바이트, 미리보기 이미지"""
    f = sfnmod.SFN(raw)
    ttf, h_target, shear, pixel = CFG[name]
    Hg = [g for g in f.glyphs if g[0] == ord('H')][0]
    cap, cap_top = Hg[2], Hg[7]
    base_y = cap_top + cap          # 원본 기준선(글리프 원점 기준)
    if pixel:
        px = 12 if 'Galmuri11' in ttf else 12
    else:
        px = 8
        while True:
            fnt = ImageFont.truetype(ttf, px + 1)
            bb = fnt.getbbox('한', anchor='ls')
            if bb[3] - bb[1] > h_target: break
            px += 1
    font = ImageFont.truetype(ttf, px)
    rend = []
    for idx, ch in chars:
        a, by = render(font, ch, px, shear, pixel)
        ys, xs = np.nonzero(a)
        if len(xs) == 0: continue
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        g = a[y0:y1, x0:x1]
        g = np.clip((g.astype(np.int32) * 15 + 127) // 255, 0, 15).astype(np.uint8)
        rend.append((code_of(idx), g, x0 - px, y0 - by))
    # 한글 기준선 위치: 원본 대문자 바닥과 맞추되 한글 바닥이 약간 내려가도록
    rowh = max(g.shape[0] for _, g, _, _ in rend) + 1
    def layout(W):
        # 원본 그림 오른쪽 빈 곳부터 채우고, 원본 아래로 내려간다
        side = f.tw + 1 if W - f.tw > 16 else None
        x, y = (side, 0) if side else (0, f.th + 1)
        place = []
        for code, g, xo, yo in rend:
            w = g.shape[1]
            if x + w > W:
                y += rowh; x = side if side and y + rowh <= f.th else 0
                if not side and y < f.th + 1: y = f.th + 1
                if x == 0 and y < f.th + 1: y = f.th + 1
            place.append((code, x, y, g, xo, yo)); x += w + 1
        return place, y
    if fit256:   # 경기 중 폰트: 256x256 안에 앞쪽(우선순위) 글자부터 들어가는 만큼
        W = 256
        place, y = layout(256)
        place = [p for p in place if p[2] + rowh <= 256]
        y = max(p[2] for p in place)
    else:
        lim = 512   # 폰트 캐시 상한(ELF 패치로 512)
        for W in (256, 512):
            place, y = layout(W)
            if y + rowh <= W or W == 512: break
        if y + rowh > lim:   # 넘치면 뒤쪽(우선순위 낮은) 글자를 뺀다
            dropped = [pl for pl in place if pl[2] + rowh > lim]
            place = [pl for pl in place if pl[2] + rowh <= lim]; y = max(pl[2] for pl in place)
            print(f'    {name}: 공간 부족으로 {len(dropped)}자 제외')
    H = (y + rowh + 3) & ~3
    img = np.zeros((H, W), np.uint8)
    img[:f.th, :f.tw] = f.img
    glyphs = [list(g) for g in f.glyphs]
    sp = 1 if cap < 16 else 2
    for code, gx, gy, g, xo, yo in place:
        h, w = g.shape
        img[gy:gy + h, gx:gx + w] = g
        xoff = max(0, xo)
        adv = w + xoff + (1 if pixel else sp)
        glyphs.append([code, w, h, gx, gy, adv, xoff, base_y + yo, 0])
    glyphs.sort(key=lambda g: g[0])
    return pack(f, glyphs, img), img


def pack(f, glyphs, img):
    H, W = img.shape
    gt = b''.join(struct.pack('<HBBHHbbbB', *g) for g in glyphs)
    toff = 0x20 + len(gt)
    pad = (-toff) % 16
    toff += pad
    flat = img.reshape(-1)
    px = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes()
    tex = struct.pack('<IHH', f.ttype, W, H) + f.thdr[8:16] + px
    body = bytearray(f.hdr) + gt + bytes(pad) + tex + f.tail
    struct.pack_into('<H', body, 0xa, len(glyphs))
    struct.pack_into('<III', body, 0x14, 0x20, 0, toff)
    struct.pack_into('<I', body, 4, len(body))
    return bytes(body)
