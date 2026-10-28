#!/bin/bash
# 사용: nav.sh 출력이름 키... (W/A/S/D 방향, K=X, L=O, I=세모, J=네모, R=START, 숫자=대기초)
E="powershell -ExecutionPolicy Bypass -File $(dirname $0)/emu.ps1"
out=$1; shift
declare -A V=([W]=57 [A]=41 [S]=53 [D]=44 [K]=4B [L]=4C [I]=49 [J]=4A [R]=0D)
for k in "$@"; do
  if [[ $k =~ ^[0-9]+$ ]]; then sleep $k; else $E kpost ${V[$k]},600 >/dev/null; sleep 1.5; fi
done
$E pshot "D:/ps2/트리플플레이베이스볼_북미판/work/shots/${out}.png"
