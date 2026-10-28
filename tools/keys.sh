#!/bin/bash
# 사용: keys.sh 출력이름 키... (짧게 눌러 메뉴 반복 입력 방지. W/A/S/D 방향, K=X, L=O, I=세모, R=START, 숫자=대기초)
E="powershell -ExecutionPolicy Bypass -File $(dirname $0)/emu.ps1"
out=$1; shift
declare -A V=([W]=57 [A]=41 [S]=53 [D]=44 [K]=4B [L]=4C [I]=49 [J]=4A [R]=0D [B]=08)
$E kpost 10,100 >/dev/null; sleep 1   # 첫 입력이 씹히는 문제 방지
for k in "$@"; do
  if [[ $k =~ ^[0-9]+$ ]]; then sleep $k; else $E kpost ${V[$k]},150 >/dev/null; sleep 2; fi
done
$E pshot "D:/ps2/트리플플레이베이스볼_북미판/work/shots/${out}.png" >/dev/null
