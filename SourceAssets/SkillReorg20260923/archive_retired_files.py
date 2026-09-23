"""Archive the retired MainPlaza scaffolding to trash/ with the §4 record.

WORKFLOW.md §4 requires: original path, target, size, SHA-256, reason and the retained
replacement for every retired file, verified absolute paths, and a read-back after moving.
§4 also says not to judge a file retired by its date or candidate name -- so each entry below
names the concrete reason it is retired and what supersedes it.

Two categories only:
  * superseded failure dumps -- the failure they record was already diagnosed, fixed and written
    up in Docs/; the authoritative record is the sibling receipt JSON, not the raw traceback;
  * scaffolding for a REJECTED approach, or a one-off repair already folded into its source.
    Probes that informed a KEPT decision (probe_lod_api.py, probe_optimize_api.py) are NOT
    retired: they are the evidence trail for the API names the kept scripts depend on.

Explicitly NOT touched: merge_plaza.py, build_main_plaza.py, apply_plaza_optimization.py.
Those three were modified by a different, currently active session whose own plan document lists
this directory in its scope; they are not mine to retire.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'SourceAssets' / 'MainPlaza20260922'
TRASH = ROOT / 'trash' / 'main-plaza-scaffolding-20260923'
HERE = Path(__file__).parent

RETIRED = [
    ('plaza_build_error.txt', '已被取代的失败转储',
     'set_lod_count 不存在导致的 AttributeError；API 已改用 StaticMeshEditorSubsystem.set_lods，'
     '结论写入 Docs/Skills 与本轮 performance references。权威记录见 plaza_build_receipt.json'),
    ('plaza_asset_lods_error.txt', '已被取代的失败转储',
     'StaticMeshReductionOptions 结构体传参错误的 traceback；正确用法已落地并写入 perf references。'
     '权威记录见 plaza_asset_lods.json'),
    ('plaza_geometry_cost_error.txt', '已被取代的失败转储',
     "StaticMesh.get_static_materials 不存在的 AttributeError；已改用 get_editor_property('static_materials')。"
     '权威记录见 plaza_geometry_cost.json'),
    ('plaza_verify_v5_error.txt', '已被取代的失败转储',
     "校验脚本尾部的 NameError（switched 作用域）；已在 verify_plaza_v5.py 内修复。"
     '权威记录见 plaza_verify_v5.json'),
    ('pavilion_torches_error.txt', '已被取代的失败转储',
     '当时编辑器打开的是 L_Dungeon_Randomized 触发的保护性中止（护栏正常工作）；'
     '两个脚本此后已加安全切图逻辑，火把已建成。权威记录见 pavilion_torches.json'),
    ('probe_merge_api.py', '被否决方案的一次性探测',
     '只为已判定不需要的"整边合并"方案做 API 探测；结论见 '
     'Docs/Performance/plaza-geometry-regression-20260922.md（16:16 数据显示合并无必要）'),
    ('probe_merge_options.py', '被否决方案的一次性探测',
     '同上：为整边合并读取 MergeStaticMeshActorsOptions 字段，方案已否决'),
    ('restore_editor_map.py', '一次性修复工具，问题已在源头修掉',
     '用于修回校验脚本异常退出后遗留的地图；verify_plaza_v5.py 已把切回逻辑移入 run()，不再需要'),
    ('editor_map_restore.json', '随 restore_editor_map.py 一并退役', '同上'),
]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    TRASH.mkdir(parents=True, exist_ok=True)
    records, skipped = [], []
    for name, reason, replacement in RETIRED:
        src = SRC / name
        if not src.exists():
            skipped.append(name)
            continue
        dst = TRASH / name
        if not str(src.resolve()).startswith(str(ROOT.resolve())):
            raise RuntimeError('refusing to move outside the repo: %s' % src)
        size, digest = src.stat().st_size, sha256(src)
        shutil.move(str(src), str(dst))
        back = dst.exists() and not src.exists() and sha256(dst) == digest
        records.append(dict(original=str(src.relative_to(ROOT)).replace('\\', '/'),
                            archived=str(dst.relative_to(ROOT)).replace('\\', '/'),
                            bytes=size, sha256=digest, reason=reason,
                            replacement=replacement, readback_ok=back))
    return dict(task='main-plaza-scaffolding-20260923', retired=records, skipped=skipped)


if __name__ == '__main__':
    result = main()
    (HERE / 'trash_record.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                            encoding='utf-8')
    print('RETIRED %d files -> trash/main-plaza-scaffolding-20260923/' % len(result['retired']))
    bad = 0
    for r in result['retired']:
        if not r['readback_ok']:
            bad += 1
        print('  %-32s %7d B  readback=%s' % (Path(r['original']).name, r['bytes'],
                                              r['readback_ok']))
    if result['skipped']:
        print('already absent: %s' % ', '.join(result['skipped']))
    print('readback failures: %d' % bad)
