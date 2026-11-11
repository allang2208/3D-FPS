"""Build HEAD-relative Integration patches for the shared hosts of KukriPairs20261111.

Each patch carries only this task's hunks: it runs `git diff HEAD -- <host>`,
then keeps the unified-diff hunks whose body contains one of the task markers.
Sibling sessions' unpublished layers in the same file never enter the patch, and
line endings stay exactly as git itself would emit them.

Usage:  python -I make_patches.py
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\FPS3D\FPSGAME")
OUT = ROOT / "Docs" / "Publication" / "KukriPairs20261111" / "Integration"

# host -> unique snippets that must appear inside a kept hunk body.
TARGETS = {
    "Source/FPSGAME/Weapons/Kukri/KukriWeaponComponent.h": [
        "IsLoneOffhand",
        "bLoneOffhand",
        "bMainHatchet",
        "bPendingOffhandDraw",
        "bDualDash",
        "DualEquipClip",
        "bSkillRiftMirrored",
        "bSkillRiftDual",
        "MainModules,OffhandModules",
        "PairChopCamera",
        "FlushPairedHeavyContacts",
        "RefreshOffhand(UColdSteelStatusModel* Profile,bool DrawNewOffhand",
    ],
    "Source/FPSGAME/Weapons/Kukri/KukriWeaponComponent.cpp": [
        "IsLoneOffhand",
        "KukriHatchetDualEquip",
        "HatchetPair",
        "SampleLeftHatchet",
        "bLoneOffhand",
        "DualEquipClip",
        "MainModules",
        "OffhandModules",
        "bOffhandHatchet",
        "bMainHatchet",
        "KukriDualDash",
        "PairChopCamera",
        "IsHatchetDualChop",
        "FlushPairedHeavyContacts",
        "bDualDash",
    ],
    "Source/FPSGAME/Weapons/Kukri/KukriStrike.cpp": [
        "IsHatchetDualChop",
        "PairChopCamera",
        "bChopRight",
        "bChopLeft",
    ],
    "Source/FPSGAME/Weapons/Kukri/KukriRift.cpp": [
        "ChopSides",
        "bChopRight",
        "bChopLeft",
        "RiftChopSides",
    ],
    "Source/FPSGAME/Weapons/Kukri/KukriArmsMeshComponent.h": [
        "MirroredWeaponToHandL",
        "MirroredWeaponRelative",
        "bMirrorRightToLeft",
        "bLeftHandOnly",
        "HiddenRight",
    ],
    "Source/FPSGAME/Weapons/Kukri/KukriArmsMeshComponent.cpp": [
        "MirroredWeaponRelative",
        "MirroredWeaponToHandL",
        "bLeftHandOnly",
        "bMirrorRightToLeft",
        "HiddenRight",
    ],
}

WHOLE_FILE = {
    "Source/FPSGAME/Weapons/Kukri/KukriWhirlwind.cpp":
        "HEAD predates a sibling session's staff-offhand / ClipTime / Pair layer; this task's lone whirlwind direction sits on it",
    "Source/FPSGAME/Weapons/Kukri/KukriDashAttack.cpp":
        "HEAD predates the network receipt layer; this task's pair chop hook sits on it",
}


def git_diff(host: str) -> str:
    p = subprocess.run(["git", "diff", "-U3", "HEAD", "--", host],
                       cwd=ROOT, capture_output=True)
    return p.stdout.decode("utf-8", errors="replace")


def split_hunks(diff: str):
    """Return (header_lines, [hunk_text, ...]) from a single-file unified diff."""
    lines = diff.splitlines(keepends=True)
    header, hunks, cur = [], [], None
    for line in lines:
        if line.startswith("@@"):
            if cur is not None:
                hunks.append("".join(cur))
            cur = [line]
        elif cur is None:
            header.append(line)
        else:
            cur.append(line)
    if cur is not None:
        hunks.append("".join(cur))
    return header, hunks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    for host, markers in TARGETS.items():
        diff = git_diff(host)
        if not diff.strip():
            report.append({"host": host, "status": "IDENTICAL_OR_MISSING"})
            continue
        header, hunks = split_hunks(diff)
        kept, dropped = [], 0
        for h in hunks:
            if any(m in h for m in markers):
                kept.append(h)
            else:
                dropped += 1
        if not kept:
            report.append({"host": host, "status": "NO_HUNKS_MATCHED",
                           "hunks": len(hunks)})
            continue
        name = host.replace("/", "__") + ".patch"
        (OUT / name).write_text("".join(header) + "".join(kept),
                                encoding="utf-8", newline="")
        report.append({"host": host, "patch": name,
                       "hunks_kept": len(kept), "hunks_dropped": dropped,
                       "markers": len(markers)})
    (OUT / "build-report.json").write_text(
        json.dumps({"targets": report, "whole_file": WHOLE_FILE}, indent=2),
        encoding="utf-8")
    for r in report:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
