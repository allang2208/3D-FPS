"""Report/emit only the hunks whose ADDED lines carry this session's markers.

Generalizes Tools/AssetPipeline/stage_session_hunks.py (whose MARKERS are baked
in per weapon session): markers are passed via argv, and the default mode is a
KEEP/DROP report so a human can review classification before anything is staged.

Usage:
  python Tools/AssetPipeline/stage_marked_hunks.py --file a.cpp [--file b.h]
         --keep Smelting --keep Furnace [--write out.patch] [--context 3]

Apply staged output:
  git apply --cached --recount out.patch        # LF files
  # CRLF-in-worktree files may refuse to apply; fall back to constructing the
  # blob directly (tier 3 in skills/ue5-auto-assistant/references/parallel-repo-publish.md).

Hunks with no added lines (pure deletions) are reported KEEP so their removal
is reviewed too; blank-context hunks are never silently dropped.
"""
import argparse
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', action='append', required=True)
    ap.add_argument('--keep', action='append', required=True,
                    help='substring a + line must contain for the hunk to be ours')
    ap.add_argument('--write', help='emit kept-hunk patch here (default: report only)')
    ap.add_argument('--detail', action='store_true',
                    help='also print added/removed lines of every hunk for review')
    ap.add_argument('--base', default='HEAD', help='diff base (default HEAD)')
    ap.add_argument('--context', default='3')
    a = ap.parse_args()

    parts = []
    total_keep = total_drop = 0
    for f in a.file:
        r = run(['git', 'diff', a.base, '-U' + a.context, '--', f])
        if r.returncode != 0:
            print('ERROR diff %s: %s' % (f, r.stderr.strip()))
            sys.exit(2)
        lines = r.stdout.splitlines(keepends=False)
        head = []      # diff --git / --- / +++  (re-emitted once if any hunk kept)
        hunks = []     # list of (header, [body])
        i = 0
        while i < len(lines) and not lines[i].startswith('@@'):
            head.append(lines[i]); i += 1
        while i < len(lines):
            hdr = lines[i]; i += 1; body = []
            while i < len(lines) and not lines[i].startswith('@@'):
                body.append(lines[i]); i += 1
            hunks.append((hdr, body))
        keep_idx = []
        for k, (hdr, body) in enumerate(hunks):
            added = [ln for ln in body if ln.startswith('+') and not ln.startswith('+++')]
            hit = any(m in ln for ln in added for m in a.keep)
            # keep pure-deletion hunks too, but flag them
            verdict = 'KEEP' if (hit or not added) else 'DROP'
            print('%-70s hunk#%-3d %s %s' % (f, k, verdict, '' if added else '(pure deletion)'))
            print('    %s' % hdr)
            if a.detail:
                for ln in body:
                    if ln.startswith('+') and not ln.startswith('+++'):
                        marked = '  <<' if any(m in ln for m in a.keep) else ''
                        print('    +%s%s' % (ln[1:].rstrip()[:150], marked))
                    elif ln.startswith('-') and not ln.startswith('---'):
                        print('    -%s' % ln[1:].rstrip()[:150])
            if verdict == 'KEEP':
                keep_idx.append(k)
        total_keep += len(keep_idx); total_drop += len(hunks) - len(keep_idx)
        if a.write and keep_idx:
            parts.extend(head)
            for k in keep_idx:
                parts.append(hunks[k][0]); parts.extend(hunks[k][1])
    print('KEEP=%d DROP=%d' % (total_keep, total_drop))
    if a.write:
        with open(a.write, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(parts) + ('\n' if parts else ''))
        print('wrote %s' % a.write)


if __name__ == '__main__':
    main()
