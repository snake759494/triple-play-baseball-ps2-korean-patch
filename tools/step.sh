#!/bin/bash
# 사용: step.sh 출력이름 키1 키2 ... (키마다 따로 보내고 2초씩 대기, 마지막에 캡처)
d=$(dirname $0); out=$1; shift
for k in "$@"; do
  if [[ $k =~ ^[0-9]+$ ]]; then sleep $k; else $d/nav.sh _tmp $k 1 >/dev/null; fi
done
$d/nav.sh $out 0
