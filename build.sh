#!/usr/bin/env bash
# Build Armenian custom dictionaries for Microsoft Word from the Hunspell
# dictionary `hy` (source: araktransfer) packaged by wooorm/dictionaries.
#
# Requirements: bash, curl, python3, hunspell, zip.
# Output: dist/hy-AM-full.zip and dist/hy-AM-compact.zip
set -euo pipefail

# Pinned revision of wooorm/dictionaries; bump to pick up upstream changes.
REV=8cfea406b505e4d7df52d5a19bce525df98c54ab
BASE=https://raw.githubusercontent.com/wooorm/dictionaries/$REV/dictionaries/hy
PARTS=${PARTS:-9}

root=$(cd "$(dirname "$0")" && pwd)
work=$root/build
dist=$root/dist
rm -rf "$work" "$dist"
mkdir -p "$work/src" "$work/full" "$work/compact" "$dist"

for f in index.aff index.dic license; do
  curl -sSfL -o "$work/src/$f" "$BASE/$f"
done

# Upstream index.aff declares 171 rules for SFX VD but has 172. Hunspell then
# misparses the file and rejects e.g. plain plurals (կարգադրիչներ), so fix the
# count before using it.
sed -E 's/^(SFX[[:space:]]+VD[[:space:]]+Y[[:space:]]+)171[[:space:]]*$/\1172/' \
  "$work/src/index.aff" > "$work/src/hy.aff"
cp "$work/src/index.dic" "$work/src/hy.dic"

build() {
  local name=$1; shift
  local dir=$work/$name
  python3 -I "$root/tools/expand_hunspell.py" "$@" \
    "$work/src/hy.aff" "$work/src/hy.dic" > "$dir/forms.txt"
  hunspell -d "$work/src/hy" -i utf-8 -l < "$dir/forms.txt" | sort -u > "$dir/bad.txt"
  python3 -I "$root/tools/write_word_dic.py" \
    "$dir/forms.txt" "$dir/bad.txt" "$dir/hy-AM-$name" "$PARTS"
  cp "$work/src/license" "$dir/LICENSE-araktransfer.txt"
  (cd "$dir" && zip -q -9 "$dist/hy-AM-$name.zip" hy-AM-*.dic LICENSE-araktransfer.txt)
}

build full
build compact --no-prefixes

ls -lh "$dist"
