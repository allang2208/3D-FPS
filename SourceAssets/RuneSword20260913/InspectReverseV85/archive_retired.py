"""Archive the retired V85 work (M-key comparison hook, V84 author folder, V85 iteration previews) into trash/.

Moves (never deletes), records original path / trash path / bytes / sha256 / reason / replacement in
trash/runesword-inspect-v85-20261102/archive-manifest.json.

  py -I archive_retired.py --dry
  py -I archive_retired.py
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(r'D:/FPS3D/FPSGAME')
T = ROOT / 'trash' / 'runesword-inspect-v85-20261102'
DRY = '--dry' in sys.argv


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


GROUPS = [
    ('SourceAssets/RuneSword20260913/InspectWrapV84',
     '顺时针 V84 被用户否定并撤回；正式资产早已从 BeforeV84 恢复为 V82。求解工具已并入 V85，目录整体退役。',
     'SourceAssets/RuneSword20260913/InspectReverseV85/（V85/R6 作者源）'),
    ('SourceAssets/RuneSword20260913/InspectReverseV85/Work',
     'V85/R2-R6 迭代预览：preview blend、逐帧渲染、拼图、日志、作者指标中间件；正式作者源与回执在目录上层。',
     'InspectReverseV85/ 上层正式文件；预览可用 preview.sh / r6run.sh 重新生成；Work/v82_poses_*.npz 保留，供拼接版重新作者'),
    ('SourceAssets/RuneSword20260913/InspectReverseV85/CompareV82',
     'M 键 V82 对比钩子的安装、读档与长柄重烘脚本；对比结束，钩子已从 C++ 移除。长柄重烘能力由 import_inspect_v85 同目录保留的收尾说明覆盖。',
     'import_inspect_v85.py（导入并做首尾待机衔接）'),
]
FILES = [
    ('SourceAssets/RuneSword20260913/InspectReverseV85/import_receipt_v85_r1.json', 'V85 R1 旧回执', 'import_receipt_v85.json'),
    ('SourceAssets/RuneSword20260913/InspectReverseV85/import_receipt_v85_r2.json', 'V85 R2 旧回执', 'import_receipt_v85.json'),
    ('SourceAssets/RuneSword20260913/InspectReverseV85/import_receipt_v85_r3.json', 'V85 R3 旧回执', 'import_receipt_v85.json'),
    ('SourceAssets/RuneSword20260913/InspectReverseV85/import_receipt_v85_r4.json', 'V85 R4 旧回执', 'import_receipt_v85.json'),
    ('SourceAssets/RuneSword20260913/InspectReverseV85/import_receipt_v85_r5.json', 'V85 R5 旧回执', 'import_receipt_v85.json'),
    ('SourceAssets/RuneSword20260913/InspectReverseV85/import_receipt_v85_r6.json', 'V85 R6 旧回执（1.58 s 版）', 'import_receipt_v85.json'),
]
entries = []


KEEP = ('v82_poses_Standard.npz', 'v82_poses_LongGrip.npz')  # V82 bake consumed by author_inspect_r6.py


def move(src, why, replacement_):
    s = ROOT / src
    if not s.exists():
        print('MISSING', src)
        return
    files = sorted(f for f in s.rglob('*') if f.is_file()) if s.is_dir() else [s]
    for f in files:
        if f.name in KEEP:
            continue
        rel = f.relative_to(ROOT)
        dst = T / rel
        entries.append(dict(original=rel.as_posix(), destination=dst.relative_to(ROOT).as_posix(),
                            bytes=f.stat().st_size, sha256=sha(f), reason=why, replacement=replacement_))
        if not DRY:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dst))
    if s.is_dir() and not DRY:
        for d in sorted((x for x in s.rglob('*') if x.is_dir()), reverse=True):
            try:
                d.rmdir()
            except OSError:
                pass
        try:
            s.rmdir()
        except OSError:
            print('LEFT (not empty):', src)


for src, why, repl in GROUPS:
    move(src, why, repl)
for src, why, repl in FILES:
    move(src, why, repl)
T.mkdir(parents=True, exist_ok=True)
manifest = T / 'archive-manifest.json'
total = sum(e['bytes'] for e in entries)
if not DRY:
    manifest.write_text(json.dumps({'task': 'runesword inspect V85/R6 closeout', 'retired': entries,
                                    'count': len(entries), 'bytes': total}, indent=1), encoding='utf-8')
print('ARCHIVED', len(entries), 'files', total, 'bytes', '(dry)' if DRY else str(manifest))
