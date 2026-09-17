"""Stage only this session's hunks when a file also carries parallel work.

Several files in this repo hold uncommitted changes from more than one working
session at once (a shared character file is the usual case). `git add <path>`
would publish other people's in-flight changes, and plain `git add -p` is not
available in an unattended run, so this classifies hunks by marker and emits a
patch that `git apply --cached` can stage on its own.

Review the classification before applying anything. Anything the markers cannot
separate (a hunk where two sessions touched adjacent lines) has to be split by
hand and passed with --manual; keep those bodies self-contained against the
index version of the file, or the staged tree will not compile.

Usage:
  python Tools/AssetPipeline/stage_session_hunks.py --file a.cpp [--file b.h]
         [--exclude '@@ -1317,3 +1465,103 @@'] [--manual mine.hunk] [--write out.patch]
  git apply --cached out.patch
"""
import argparse
import re
import subprocess

# Every line this session added carries one of these markers.
MARKERS = (
    'ClipRecoil', 'ClipPosition', 'ClipRotation', 'ClipADS', 'ClipWave',
    'ADSRotationScale', 'RecoilProfile', 'CameraShake', 'fps.Camera.Shake',
    'FeedbackScale = 1.0f', 'ShakeDecay = 3.0f',
    '0.11f * AKMSource::FeedbackScale', '0.34f * AKMSource::FeedbackScale',
    'Lerp(13.0f, 19.0f', 'Lerp(13.0f,19.0f', 'FOVPunch = FMath::Lerp(1.2f',
    '1.2f*Dual.CameraGain', '0.11f * RecoilLoad', '0.11f*RecoilLoad',
    'Amplitude base of the whole shot camera layer', 'Trauma is squared when rendered',
    'Single live dial for the strength of the shot camera layer',
    'increasing random tumbling as the automatic burst continues',
    'A defined first pulse followed by smaller settled pulses, rather than',
    'Godot ADS convergence is applied once to the common gun/camera pulse',
)

HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def hunk_start(header):
    match = HUNK.match(header)
    return int(match.group(1)) if match else 0


def is_mine(hunk):
    return any(line.startswith('+') and not line.startswith('+++')
        and any(marker in line for marker in MARKERS) for line in hunk)


def split(path):
    diff = subprocess.run(['git', 'diff', '-U0', '--', path], capture_output=True, text=True,
                          encoding='utf-8', errors='replace').stdout
    header, hunks, current = [], [], None
    for line in diff.splitlines():
        if line.startswith('@@'):
            if current is not None:
                hunks.append(current)
            current = [line]
        elif current is None:
            header.append(line)
        else:
            current.append(line)
    if current is not None:
        hunks.append(current)
    return header, hunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', action='append', required=True)
    parser.add_argument('--exclude', action='append', default=[],
                        help='hunk header substring to drop from the staged set')
    parser.add_argument('--manual', help='file holding hand split hunk(s) to include')
    parser.add_argument('--write')
    args = parser.parse_args()
    out = []
    for path in args.file:
        header, hunks = split(path)
        kept, dropped, mine = [], 0, 0
        for hunk in hunks:
            if any(token in hunk[0] for token in args.exclude):
                dropped += 1
                continue
            if is_mine(hunk):
                kept.append(hunk)
                mine += 1
            else:
                dropped += 1
        print('%s: %d hunks -> keep %d, leave %d for the other session(s)'
              % (path, len(hunks), mine, dropped))
        for hunk in kept:
            added = [l[1:].strip() for l in hunk if l.startswith('+')]
            print('   keep %s | %s' % (hunk[0][:40], added[0][:70] if added else ''))
        if args.manual:
            with open(args.manual, encoding='utf-8') as handle:
                body = handle.read().splitlines()
            manual, current = [], None
            for line in body:
                if line.startswith('@@'):
                    if current is not None:
                        manual.append(current)
                    current = [line]
                elif current is not None:
                    current.append(line)
            if current is not None:
                manual.append(current)
            for hunk in manual:
                print('   manual %s' % hunk[0][:40])
            kept += manual
        kept.sort(key=lambda hunk: hunk_start(hunk[0]))
        # Dropping and hand splitting hunks invalidates the new-side line numbers
        # of everything after the edit; recompute them from the real deltas or
        # git apply rejects the patch.
        offset = 0
        for hunk in kept:
            match = HUNK.match(hunk[0])
            removed = sum(1 for l in hunk if l.startswith('-') and not l.startswith('---'))
            added = sum(1 for l in hunk if l.startswith('+') and not l.startswith('+++'))
            old_start, old_count = int(match.group(1)), removed
            tail = hunk[0].split('@@', 2)[2] if hunk[0].count('@@') >= 2 else ''
            hunk[0] = '@@ -%d,%d +%d,%d @@%s' % (old_start, old_count, old_start + offset, added, tail)
            offset += added - removed
        if args.write:
            out.append('\n'.join(header + [l for hunk in kept for l in hunk]) + '\n')
    if args.write:
        with open(args.write, 'w', encoding='utf-8', newline='') as handle:
            handle.write(''.join(out))
        print('wrote', args.write)


if __name__ == '__main__':
    main()
