"""릴리즈 xdelta 를 해시 검사 후 적용.
사용: python tools/apply_release.py --xdelta xdelta3.exe --source "Triple Play Baseball (USA).bin" --patch Triple_Play_Baseball_PS2_KO_v1.0.xdelta --output "Triple Play Baseball (Korean).bin"
"""
import argparse, hashlib, json, os, subprocess, sys

MAN = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'release_manifest.json'), encoding='utf-8'))

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()

def check(p, size, digest, what):
    if os.path.getsize(p) != size: sys.exit('%s 크기 불일치: %d (기대 %d)' % (what, os.path.getsize(p), size))
    print(what, '해시 확인 중...', flush=True)
    if sha256(p) != digest: sys.exit('%s SHA-256 불일치' % what)

a = argparse.ArgumentParser()
a.add_argument('--xdelta', default='xdelta3')
a.add_argument('--source', required=True)
a.add_argument('--patch', required=True)
a.add_argument('--output', required=True)
o = a.parse_args()
if os.path.exists(o.output): sys.exit('출력 파일이 이미 있습니다: ' + o.output)
check(o.source, MAN['source_bin_size'], MAN['source_bin_sha256'], '원본 BIN')
check(o.patch, MAN['asset_size'], MAN['asset_sha256'], 'xdelta')
subprocess.run([o.xdelta, '-d', '-s', o.source, o.patch, o.output], check=True)
check(o.output, MAN['output_bin_size'], MAN['output_bin_sha256'], '결과 BIN')
print('완료:', o.output)
