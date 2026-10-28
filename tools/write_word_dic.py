#!/usr/bin/env python3
"""Write a word list as Microsoft Word custom dictionaries (.dic).

Word expects one word per line, UTF-16 LE with a BOM and CRLF line endings.
Word can have at most 10 custom dictionaries active at once (one of them is
usually the default CUSTOM.DIC), so the list is split into a fixed number of
parts rather than parts of a fixed size.

Usage: write_word_dic.py forms.txt bad.txt out_prefix parts

bad.txt is the `hunspell -l` output for forms.txt: words in it are dropped,
and so are hyphenated words containing one of them (hunspell reports the
parts of hyphenated words separately).
"""

import sys


def main(forms_path, bad_path, prefix, parts):
    with open(bad_path, encoding="utf-8") as f:
        bad = {l.strip() for l in f if l.strip()}
    words = []
    with open(forms_path, encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if not w or w in bad:
                continue
            if "-" in w and any(p in bad for p in w.split("-")):
                continue
            words.append(w)
    words.sort()
    size = -(-len(words) // parts)
    for i in range(parts):
        chunk = words[i * size:(i + 1) * size]
        name = f"{prefix}-{i + 1:02d}.dic" if parts > 1 else f"{prefix}.dic"
        with open(name, "w", encoding="utf-16-le", newline="\r\n") as out:
            out.write("﻿")
            out.write("\n".join(chunk))
            out.write("\n")
        print(f"{name}: {len(chunk)} words", file=sys.stderr)
    print(f"total: {len(words)} words", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
