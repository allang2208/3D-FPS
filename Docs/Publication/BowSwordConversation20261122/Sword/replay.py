"""Replay the sword's source on the matching production revision, preserving local end-of-line style."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def transform(source, patch, reverse=False):
    result = []
    lines = source.splitlines(keepends=True)
    cursor = 0
    expects = sends = context = 0
    offset = re.compile(rb"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    for line in patch.splitlines(keepends=True)[2:]:
        match = offset.match(line)
        if match:
            if context and (expects or sends):
                raise ValueError("incomplete hunk")
            m = [int(x or 1) for x in match.groups()]
            start, expects, sends = (m[2], m[3], m[1]) if reverse else (m[0], m[1], m[3])
            start = start - 1 if expects else start
            if start < cursor or start > len(lines):
                raise ValueError("invalid hunk position")
            result.extend(lines[cursor:start])
            cursor = start
            context = 1
            continue
        mark, value = line[:1], line[1:]
        if mark not in (b" ", b"+", b"-") or not context:
            raise ValueError("unexpected patch line")
        if mark == b" " or mark == (b"+" if reverse else b"-"):
            if cursor == len(lines) or value != lines[cursor]:
                raise ValueError("context differs")
            cursor += 1
            expects -= 1
        if mark == b" " or mark == (b"-" if reverse else b"+"):
            result.append(value)
            sends -= 1
    if not context or expects or sends:
        raise ValueError("incomplete patch")
    result.extend(lines[cursor:])
    return b"".join(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--write", action="store_true", help="write files after every selected input matches")
    parser.add_argument("--only", action="append", metavar="SOURCE_PATH", help="restrict to an exact production path")
    args = parser.parse_args()
    root = args.project.resolve()
    if not (root / "FPSGAME.uproject").is_file():
        parser.error("expected the project root containing FPSGAME.uproject")
    entries = json.loads((HERE / "runtime.json").read_text(encoding="utf8"))["files"]
    selected = set(args.only or [entry["path"] for entry in entries])
    if selected.difference(entry["path"] for entry in entries):
        parser.error("unknown source path")
    prefix = "Docs/Publication/BowSwordConversation20261122/Sword/"
    ready, rejected, installed = [], [], 0
    for entry in entries:
        if entry["path"] not in selected:
            continue
        path = root / entry["path"]
        raw = path.read_bytes() if path.is_file() else None
        canonical = None if raw is None else raw.replace(b"\r\n", b"\n")
        current = digest(canonical) if canonical is not None else None
        if current == entry["after"]:
            installed += 1
            continue
        if current != entry["before"]:
            rejected.append(entry["path"])
            continue
        if entry["delivery"] == "unit":
            data = (HERE / entry["source"].removeprefix(prefix)).read_bytes().replace(b"\r\n", b"\n")
        else:
            patch = (HERE / entry["patch"].removeprefix(prefix)).read_bytes().replace(b"\r\n", b"\n")
            data = transform(canonical, patch)
        if digest(data) != entry["after"]:
            raise ValueError("result digest differs for " + entry["path"])
        if raw is not None and b"\r\n" in raw:
            data = data.replace(b"\n", b"\r\n")
        ready.append((path, raw, data))
    print(f"{installed} already installed; {len(ready)} ready; {len(rejected)} different revisions")
    if rejected:
        print("\n".join(rejected))
        return 1
    if args.write:
        for path, original, data in ready:
            actual = path.read_bytes() if path.exists() else None
            if actual != original:
                raise RuntimeError("file changed since preflight: " + str(path))
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".sword-replay.tmp")
            with temporary.open("xb") as output:
                output.write(data)
            temporary.replace(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
