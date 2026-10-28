#!/usr/bin/env python3
"""Expand a Hunspell dictionary (.dic + .aff) into a flat list of word forms.

The stock `unmunch` tool crashes on the Armenian dictionary (it uses
`FLAG long`, twofold suffixes and prefixes with continuation classes), so this
script does the expansion itself. It deliberately over-generates a little;
the result is then filtered through `hunspell -G` (see build.sh) so that only
forms Hunspell itself accepts end up in the output.

Usage: expand_hunspell.py [--no-prefixes] index.aff index.dic > forms.txt

--no-prefixes skips prefix rules (in the Armenian dictionary these are the
verb particles կ- and չ-), which roughly halves the output.
"""

import re
import sys
from collections import defaultdict


def split_flags(flags, mode):
    if mode == "long":
        return {flags[i:i + 2] for i in range(0, len(flags), 2)}
    if mode == "num":
        return set(flags.split(","))
    return set(flags)


class Affix:
    def __init__(self, kind, strip, add, cond, cont, cross):
        self.kind = kind
        self.strip = "" if strip == "0" else strip
        self.add = "" if add == "0" else add
        self.cont = cont
        self.cross = cross
        cond = cond or "."
        if kind == "SFX":
            self.cond = re.compile("(?:" + cond + ")$")
        else:
            self.cond = re.compile("^(?:" + cond + ")")

    def apply(self, word):
        if self.kind == "SFX":
            if not word.endswith(self.strip) or not self.cond.search(word):
                return None
            base = word[:len(word) - len(self.strip)] if self.strip else word
            return base + self.add
        if not word.startswith(self.strip) or not self.cond.search(word):
            return None
        return self.add + word[len(self.strip):]


def parse_aff(path):
    mode = "char"
    needaffix = forbidden = None
    ignore = ""
    cross = {}
    rules = defaultdict(list)
    kinds = {}
    with open(path, encoding="utf-8") as f:
        lines = [l.split() for l in f if not l.lstrip().startswith("#")]
    for parts in lines:
        if not parts:
            continue
        key = parts[0]
        if key == "FLAG":
            mode = parts[1]
        elif key == "NEEDAFFIX":
            needaffix = parts[1]
        elif key == "FORBIDDENWORD":
            forbidden = parts[1]
        elif key == "IGNORE":
            ignore = parts[1]
        elif key in ("PFX", "SFX") and len(parts) >= 4:
            flag = parts[1]
            if len(parts) == 4 and parts[2] in "YN" and parts[3].isdigit():
                cross[flag] = parts[2] == "Y"
                kinds[flag] = key
                continue
            strip, add = parts[2], parts[3]
            cond = parts[4] if len(parts) > 4 else "."
            cont = set()
            if "/" in add:
                add, c = add.split("/", 1)
                cont = split_flags(c, mode)
            rules[flag].append(Affix(key, strip, add, cond, cont, cross.get(flag, True)))
    return mode, needaffix, forbidden, ignore, rules, kinds


def expand(stem, flags, rules, kinds, needaffix, prefixes=True):
    out = set()
    if needaffix not in flags:
        out.add(stem)

    # Forms after suffixation: (word, flags that may still apply, needs-more-affix).
    suffixed = [(stem, flags, needaffix in flags, True)]
    for flag in flags:
        if kinds.get(flag) != "SFX":
            continue
        for a in rules[flag]:
            w1 = a.apply(stem)
            if w1 is None:
                continue
            need1 = needaffix in a.cont
            if not need1:
                out.add(w1)
            suffixed.append((w1, flags | a.cont, need1, a.cross))
            # Twofold suffixes: a suffix may carry further suffix flags.
            for f2 in a.cont:
                if kinds.get(f2) != "SFX":
                    continue
                for b in rules[f2]:
                    w2 = b.apply(w1)
                    if w2 is None:
                        continue
                    need2 = needaffix in b.cont
                    if not need2:
                        out.add(w2)
                    suffixed.append((w2, flags | a.cont | b.cont, need2, a.cross and b.cross))

    if not prefixes:
        return out

    # Prefixes, combined with the suffixed forms (cross product) and with
    # suffixes that the prefix itself enables through its continuation flags.
    for word, avail, _need, cross_ok in suffixed:
        for flag in avail:
            if kinds.get(flag) != "PFX":
                continue
            for p in rules[flag]:
                if word is not stem and not (cross_ok and p.cross):
                    continue
                w = p.apply(word)
                if w is None:
                    continue
                out.add(w)
                if word is stem:
                    for f2 in p.cont:
                        if kinds.get(f2) != "SFX":
                            continue
                        for b in rules[f2]:
                            w2 = b.apply(stem)
                            if w2 is not None:
                                w3 = p.apply(w2)
                                if w3 is not None:
                                    out.add(w3)
    return out


def main(aff_path, dic_path, prefixes=True):
    mode, needaffix, forbidden, ignore, rules, kinds = parse_aff(aff_path)
    seen = set()
    with open(dic_path, encoding="utf-8") as f:
        next(f)  # word count
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "/" in line:
                stem, fl = line.split("/", 1)
                flags = split_flags(fl.split()[0], mode)
            else:
                stem, flags = line.split()[0], set()
            if forbidden in flags:
                continue
            for w in expand(stem, flags, rules, kinds, needaffix, prefixes):
                if ignore:
                    w = w.translate({ord(c): None for c in ignore})
                if w and w not in seen:
                    seen.add(w)
    for w in sorted(seen):
        print(w)


if __name__ == "__main__":
    args = sys.argv[1:]
    use_prefixes = "--no-prefixes" not in args
    args = [a for a in args if a != "--no-prefixes"]
    main(args[0], args[1], use_prefixes)
