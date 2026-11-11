#!/bin/sh
# 8 段并行下载大文件
# 用法: sh pdl.sh <URL> <输出文件名> [段数]
URL="$1"; OUT="$2"; N="${3:-8}"
TOTAL=$(curl -sSIL -m 40 "$URL" | tr -d '\r' | awk 'tolower($1)=="content-length:"{v=$2} END{print v}')
[ -z "$TOTAL" ] && { echo "取不到长度"; exit 1; }
DIR="$OUT.parts"; mkdir -p "$DIR"; rm -f "$DIR"/p*
SIZE=$(( (TOTAL + N - 1) / N ))
i=0
while [ $i -lt $N ]; do
  S=$(( i * SIZE )); E=$(( S + SIZE - 1 )); [ $E -ge $TOTAL ] && E=$(( TOTAL - 1 ))
  ( f="$DIR/p$i"; : > "$f"; want=$(( E - S + 1 ))
    while :; do have=$(wc -c < "$f" 2>/dev/null || echo 0)
      [ "$have" -ge "$want" ] && break
      curl -sS -L -m 900 -r "$((S + have))-$E" "$URL" >> "$f" 2>/dev/null; sleep 2
    done ) &
  i=$(( i + 1 ))
done
wait
: > "$OUT"; i=0
while [ $i -lt $N ]; do cat "$DIR/p$i" >> "$OUT"; i=$(( i + 1 )); done
echo "完成 $(wc -c < "$OUT") / $TOTAL"
