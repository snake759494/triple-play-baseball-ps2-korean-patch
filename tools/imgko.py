"""메뉴 라벨 이미지 한글화: 원본에서 채움(위/아래)·외곽선 색을 뽑아 같은 스타일로 다시 그린다"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import kfont

# 파일 -> {텍스처 이름: 한글}
LABELS = {
    'PRIME': {**{f'l1{v}_': '빠른 시작' for v in 'bdr'}, **{f'l2{v}_': '경기 모드' for v in 'bdr'},
              **{f'l3{v}_': 'EA 스포츠 소개' for v in 'bdr'}, **{f'l4{v}_': '옵션' for v in 'br'},
              'op1h': '로스터 옵션', 'op1n': '로스터 옵션', 'op2h': '경기 옵션', 'op2n': '경기 옵션',
              'op3h': '오디오 옵션', 'op3n': '오디오 옵션', 'op4h': '저장 / 불러오기 옵션', 'op4n': '저장 / 불러오기 옵션'},
    'GAMEMODE': {'BLCR': '빅 리그 챌린지', 'BLSB': '빅 리그 챌린지', 'PlfB': '포스트시즌', 'PlfR': '포스트시즌',
                 'SnGB': '단일 경기', 'SnGR': '단일 경기', 'ssnB': '시즌', 'ssnR': '시즌'},
    'BLC': {**{f'16{v}': '16인' for v in ('DS', 'HL', 'NT')}, **{f'ct{v}': '참가자' for v in ('DS', 'HL', 'NT')},
            **{f'ex{v}': '익스트림' for v in ('DS', 'HL', 'NT')}, **{f'of{v}': '공식' for v in ('DS', 'HL', 'NT')},
            **{f'oo{v}': '1대1' for v in ('DS', 'HL', 'NT')}, **{f'tr{v}': '토너먼트' for v in ('DS', 'HL', 'NT')}, 'tnmt': '토너먼트'},
    'GMRSLTS': {**{f'bs{v}': '타격 기록' for v in ('DS', 'HL', 'NT')}, **{f'dn{v}': '완료' for v in ('DS', 'HL', 'NT')},
                **{f'pg{v}': '오늘의 선수' for v in ('DS', 'HL', 'NT')}, **{f'ps{v}': '투구 기록' for v in ('DS', 'HL', 'NT')},
                **{f'pt{v}': '포인트' for v in ('DS', 'HL', 'NT')}, **{f'rw{v}': '보상' for v in ('DS', 'HL', 'NT')}},
    'PREGAME': {'GmSB': '경기 설정', 'GmSR': '경기 설정', 'PlbB': '플레이 볼', 'PlbR': '플레이 볼',
                'RstB': '로스터', 'RstR': '로스터', 'SlsB': '구장 선택', 'SlsR': '구장 선택', 'StsB': '통계', 'StsR': '통계'},
    'TITLES': {**{f'Crp{v}': '선수 만들기' for v in 'BGR'}, **{f'Def{v}': '수비' for v in 'BGR'},
               **{f'Gop{v}': '경기 옵션' for v in 'BR'}, **{f'Lgl{v}': '리그 순위권' for v in 'BGR'},
               **{f'Lnu{v}': '라인업' for v in 'BGR'}, 'MLBB': 'MLB 뉴스', 'MLBR': 'MLB 뉴스',
               **{f'Pfl{v}': '포스트시즌 순위권' for v in 'BGR'}, 'PlgB': '경기 하기', 'PlgR': '경기 하기',
               **{f'Prt{v}': '선발 로테이션' for v in 'BGR'}, **{f'Rsr{v}': '로스터 초기화' for v in 'BGR'},
               **{f'Rst{v}': '로스터' for v in 'BR'}, **{f'Rwd{v}': '보상' for v in 'BGR'},
               **{f'Sfa{v}': '자유계약 선수 영입' for v in 'BGR'}, 'SndB': '순위', 'SndR': '순위',
               **{f'Sts{v}': '통계' for v in 'BR'}, 'SveB': '저장', 'SveR': '저장',
               **{f'Svr{v}': '로스터 저장' for v in 'BGR'}, **{f'Trd{v}': '트레이드' for v in 'BGR'},
               **{f'awr{v}': '시상' for v in 'DHN'}, **{f'crd{v}': '제작진' for v in 'DHN'},
               **{f'wvc{v}': '비타민 C란?' for v in 'DHN'}},
    'INGAME': {'pchl': '투구 차트', 'tbat': '타격', 'tfel': '수비', 'tpit': '투구', 'trun': '주루'},
}
FONT = kfont.NANUM['eHv']
PLAIN = {('INGAME', 'pchl'), ('INGAME', 'tbat'), ('INGAME', 'tfel'), ('INGAME', 'tpit'), ('INGAME', 'trun')}


def style(a, plain=False):
    """원본 글자에서 (위 채움색, 아래 채움색, 외곽선색, 글자 bbox)"""
    from scipy.ndimage import binary_erosion
    al = a[..., 3] > (40 if plain else 200)
    ys, xs = np.nonzero(al)
    bbox = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    if plain:
        c = a[al][..., :3].mean(0); return c, c, c, bbox
    inner = binary_erosion(al, iterations=2)
    edge = al & ~binary_erosion(al, iterations=1)
    if inner.sum() < 10: inner = binary_erosion(al, iterations=1)
    iy = np.nonzero(inner)[0]; mid = (iy.min() + iy.max()) / 2
    rows = np.arange(a.shape[0])[:, None]
    top = a[inner & (rows <= mid)][..., :3]; bot = a[inner & (rows > mid)][..., :3]
    c_top = top.mean(0); c_bot = bot.mean(0) if len(bot) else c_top
    return c_top, c_bot, a[edge][..., :3].mean(0), bbox


def render(orig, text, plain=False, box=None):
    h, w = orig.shape[:2]
    ct, cb, co, (x0, y0, x1, y1) = style(orig, plain)
    if box: x0, y0, x1, y1 = box
    bh = y1 - y0; bw = x1 - x0
    out = np.zeros_like(orig)
    pad = 0 if plain else 1
    face = FONT if not plain else kfont.NANUM['cBd']
    limit = w - x0 - 2 - (0 if plain else int(bh * 0.25))
    px = 6
    while px < 60:   # 글자 높이를 원본 글자 높이에 맞춤(폭이 넘치면 줄임)
        bb = ImageFont.truetype(face, px + 1).getbbox(text)
        if bb[3] - bb[1] + pad * 2 > bh or bb[2] - bb[0] + pad * 2 > limit: break
        px += 1
    f = ImageFont.truetype(face, px)
    bb = f.getbbox(text)
    W = w * 2; m = Image.new('L', (W, h), 0)
    ImageDraw.Draw(m).text((x0 + pad - bb[0], y0 + pad - bb[1] + (bh - pad * 2 - (bb[3] - bb[1])) // 2), text, font=f, fill=255)
    if not plain:   # 원본처럼 기울임
        m = m.transform(m.size, Image.AFFINE, (1, 0.22, -0.22 * h, 0, 1, 0), Image.BICUBIC)
    fill = np.array(m).astype(float) / 255
    fill = fill[:, :w]
    if plain:
        out[..., :3] = ct; out[..., 3] = (fill * 255).astype(np.uint8)
        return out
    ol = np.array(Image.fromarray((fill * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5 if bh >= 16 else 3))).astype(float) / 255
    sh = np.zeros_like(ol); sh[2:, 2:] = ol[:-2, :-2]
    yy = np.clip((np.arange(h)[:, None] - y0) / max(1, bh), 0, 1)
    grad = ct[None, None, :] * (1 - yy[..., None]) + cb[None, None, :] * yy[..., None]
    rgb = np.zeros((h, w, 3)); alpha = np.zeros((h, w))
    # 그림자 -> 외곽선 -> 채움 순서로 합성
    for col, a_ in ((np.array([0, 0, 0]), sh * 0.6), (co, ol), (grad, fill)):
        col = np.broadcast_to(col, (h, w, 3))
        rgb = rgb * (1 - a_[..., None]) + col * a_[..., None]
        alpha = alpha * (1 - a_) + a_
    out[..., :3] = np.clip(rgb / np.maximum(alpha, 1e-6)[..., None], 0, 255).astype(np.uint8)
    out[..., 3] = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    return out
