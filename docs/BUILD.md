# 재빌드 방법

필요한 것: Python 3.10+ (numpy, Pillow, scipy, pycdlib), xdelta3.

## 준비

저장소 루트에 다음 파일을 둡니다(저장소에는 포함되지 않음).

- `Triple Play Baseball (USA).bin`: 해시가 README 표와 일치하는 원본(MODE2/2352)
- `NanumSquareNeo-aLt.ttf` ~ `NanumSquareNeo-eHv.ttf`: 나눔스퀘어 네오 5종
- `Galmuri11.ttf`, `Galmuri11-Bold.ttf`: 갈무리11

## 빌드

```
python tools/build.py      # -> Triple Play Baseball (Korean).bin / .cue
xdelta3 -e -0 -S none -A -s "Triple Play Baseball (USA).bin" "Triple Play Baseball (Korean).bin" Triple_Play_Baseball_PS2_KO_v1.0.xdelta
```

## 번역 수정

`translation/src/*.txt`는 한 줄에 `키|번역`입니다. `#`으로 시작하는 줄은 주석입니다.

| 파일 | 키 | 내용 |
| --- | --- | --- |
| `zfetext.txt`, `zigtext.txt` | 문자열 번호 | 프런트엔드(ZFETEXT.ENG)·경기 중(ZIGTEXT.ENG) 문자열 |
| `felayout.txt` | 원문 | FELAYOUT.BIG 레이아웃의 고정 라벨 |
| `elf.txt` | 가상 주소(16진) | 실행파일 문자열. `G:시작-끝`은 여러 줄 문단 |
| `stadium.txt` | 구장 번호 | 도시, 팀, 설명(자동 줄나눔) |
| `first.txt`, `last.txt` | 원문 | 선수 이름·성 (한글 7자 이내) |

## 와이드 패치

`patches/*.pnach`는 손으로 만든 파일입니다. 실행파일 `SetPerspective` 코드가 바뀌면 주소를 다시 확인하세요(`docs/TECHNICAL.md`). 파일 이름의 CRC는 실행파일 전체를 32비트 단어로 XOR한 값입니다.

## 검증

`tools/emu.ps1`(PCSX2 백그라운드 실행·캡처·키 입력)과 `tools/nav.sh`, `tools/step.sh`를 썼습니다. PCSX2 경로와 캡처 폴더는 스크립트 안에서 직접 고쳐 쓰세요. PCSX2 2.2는 이 CUE를 열지 못할 때가 있어, 검증할 때는 `tools/bin2iso.py`로 만든 ISO를 열었습니다.
