"""Offline diagnosis from preserved capture, source snapshot and current source.
No engine process is launched and no gameplay state is changed.
"""
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import json
import re
import zipfile

OUT = Path(__file__).parent
REVIEW = OUT.parent
PROJECT = Path('D:/FPS3D/FPSGAME')
RUN = REVIEW / 'Listen-20261103-114146'
host = (RUN / 'host.log').read_text(encoding='utf-8', errors='replace')
observer = (RUN / 'observer.log').read_text(encoding='utf-8', errors='replace')
files = [
    'Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyAppearance.cpp',
    'Source/FPSGAME/Characters/FPSPlayerHeadAnimInstance.cpp',
    'Source/FPSGAME/Characters/FPSBodyAssetPreloader.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyMotion.cpp',
    'Source/FPSGAME/Production/ThunderHammerRecall.cpp',
    'Source/FPSGAME/Development/ThunderHammerClosureAudit.cpp',
]
def sha(data):
    return hashlib.sha256(data).hexdigest()
source_rows = []
with zipfile.ZipFile(REVIEW / 'source-config-recovery.zip') as archive:
    for name in files:
        before = archive.read(name)
        current = (PROJECT / name).read_bytes()
        source_rows.append({
            'path': name,
            'review_snapshot_sha256': sha(before),
            'current_sha256': sha(current),
            'identical_bytes': before == current,
            'identical_text': before.decode('utf-8-sig').replace('\r\n', '\n') == current.decode('utf-8-sig').replace('\r\n', '\n'),
        })

shots = []
for time, frame, name in re.findall(r'\[2026\.11\.03-(\d\d\.\d\d\.\d\d:\d\d\d)\]\[\s*(\d+)\].*Tracing Screenshot "(remote_\d+)"', observer):
    shots.append({'screenshot': name + '.png', 'log_utc': time, 'engine_frame': int(frame)})
phase = re.search(r'\[2026\.11\.03-(\d\d\.\d\d\.\d\d:\d\d\d)\].*THUNDER_CLOSURE_PHASE phase=14 ', host).group(1)
phase_time = datetime.strptime(phase, '%H.%M.%S:%f')
head_wait = [line for line in observer.splitlines() if 'Waiting for skinned assets' in line and 'SKM_Jason_head' in line]
result = {
    'updated': datetime.now().astimezone().isoformat(),
    'method': 'Existing real-UDP capture/logs and source trace, compared with preserved review source snapshot. No new runtime test.',
    'source_comparison': source_rows,
    'capture_run': RUN.name,
    'screenshot_timeline': shots,
    'recall_phase_start_utc': phase,
    'earliest_script_input_utc': (phase_time + timedelta(seconds=2)).strftime('%H:%M:%S.%f')[:-3],
    'input_time_boundary': 'Script uses Age > 2; actual input event timestamp was not separately logged.',
    'production_recall_flight_seconds': 1.0,
    'production_catch_attach_seconds': 0.1,
    'head_asset_wait_log': head_wait,
    'observer_bootstrap_disabled': 'fps.body.AsyncPreload=0' in (RUN / 'launch-observer.json').read_text(encoding='utf-8-sig'),
    'confirmed_cause': 'InitializeBody exposes the separate body mesh before ApplyAppearance async completion. Head components are created only in that completion callback; no initial-appearance readiness barrier or complete fallback presentation covers the gap.',
    'corrections': [
        'Empty hands before recall are intentional. Stage 14 waits two seconds before input; production flight is one second plus catch handoff. These screenshots do not establish abnormal weapon loading delay.',
        'The blurred object in remote_008 occurs in the recall interval and does not establish a detached head. Head misalignment is unproven; only missing head is confirmed.',
    ],
    'unresolved': [
        'No functional fix applied in this diagnosis.',
        'The existing log cannot split head wait time into async queue, I/O, groom/material and skinned-asset preparation costs.',
        'Preload-disabled, uncooked offscreen capture does not establish production-default or packaged cold-join duration.',
    ],
}
(OUT / 'diagnosis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'sources_unchanged': sum(row['identical_text'] for row in source_rows), 'sources_compared': len(source_rows), 'screenshots': len(shots), 'phase_14': phase, 'input_no_earlier_than': result['earliest_script_input_utc'], 'head_wait': head_wait}, ensure_ascii=False))
