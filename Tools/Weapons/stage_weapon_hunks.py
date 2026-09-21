"""Stage only this work's hunks when a file also carries parallel uncommitted work.

Several files here mix one work stream's changes with another session's in-flight work
(the shared gunsmith catalog, the weapon FX component, the melee modifier applier).
Plain `git add <path>` would publish their unverified changes and `git add -p` needs a
terminal, so this selects hunks by explicit markers and writes a patch that
`git apply --cached` can stage.

- `--drop-contains <substr>`: keep everything except hunks whose changed lines match.
- `--keep-contains <substr>`: keep ONLY hunks whose changed lines match (use when a
  parallel session rewrote most of the file and only your own lines belong in the commit).

Always review the printed KEEP/DROP report and `git diff --cached` before committing.

Usage:
  py Tools/Weapons/stage_weapon_hunks.py --file <path> [--file <path> ...]
      --drop-contains <substring> [--keep-contains <substring> ...] --write <patch>
  git apply --cached <patch>
"""
import argparse
import re
import subprocess


def split_hunks(path):
    diff = subprocess.run(['git', 'diff', '-U3', '--', path], capture_output=True, text=True,
                          encoding='utf-8', errors='replace').stdout
    if not diff.strip():
        return None, []
    parts = re.split(r'(?m)^(?=@@ )', diff)
    return parts[0], parts[1:]


def changed_lines(hunk):
    return [line for line in hunk.splitlines()
            if (line.startswith('+') or line.startswith('-')) and not line.startswith(('+++', '---'))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', action='append', required=True)
    parser.add_argument('--drop-contains', action='append', default=[])
    parser.add_argument('--keep-contains', action='append', default=[])
    parser.add_argument('--write', required=True)
    args = parser.parse_args()

    patch = []
    kept = dropped = 0
    for path in args.file:
        header, hunks = split_hunks(path)
        if header is None:
            print('SKIP  no working-tree change: ' + path)
            continue
        keep = []
        for hunk in hunks:
            lines = changed_lines(hunk)
            drop_hit = next((marker for marker in args.drop_contains
                             for line in lines if marker in line), None)
            keep_hit = next((marker for marker in args.keep_contains
                             for line in lines if marker in line), None)
            first = (lines[0].strip() if lines else '')[:78]
            where = hunk.splitlines()[0][:58]
            if drop_hit or (args.keep_contains and not keep_hit):
                dropped += 1
                print('DROP  %-24s %s | %s' % (drop_hit or 'keep-only', where, first))
            else:
                kept += 1
                keep.append(hunk)
                print('KEEP  %-24s %s | %s' % (keep_hit or '', where, first))
        if keep:
            patch.append(header + ''.join(keep))

    with open(args.write, 'w', encoding='utf-8', newline='') as handle:
        handle.write(''.join(patch))
    print('kept_hunks=%d dropped_hunks=%d patch=%s' % (kept, dropped, args.write))


if __name__ == '__main__':
    main()