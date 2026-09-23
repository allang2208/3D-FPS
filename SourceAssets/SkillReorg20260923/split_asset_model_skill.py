"""Skill reorganisation, step 2: split asset-model-workflow/SKILL.md by reuse surface.

The entry file was 21,025 chars of which 81.6% was dated case notes. The placement rule used
here is REUSE SURFACE, not length:

  * stays in SKILL.md   -- needed for every model-generation task (the 1-4 procedure, the
                           form/precision routing, the read-image rule, pointers already short)
  * moves to references/ -- technique that applies to a CLASS of future tasks; loaded on demand
  * the entry keeps a TRIGGER TABLE saying when to read which reference

Content is moved verbatim: every relocated section is asserted to exist byte-for-byte in its new
reference file, and each new reference carries a backlink to the Docs record that is its
canonical source. No case content is deleted or rewritten here.

Run: py -3.11 SourceAssets/SkillReorg20260923/split_asset_model_skill.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / 'skills' / 'asset-model-workflow'
SKILL = SKILL_DIR / 'SKILL.md'
REFS = SKILL_DIR / 'references'
HERE = Path(__file__).parent

ANY_HEAD = re.compile(r'^#{1,2}\s')

MOVES = [
    dict(
        target='blender-hardsurface-checklist.md',
        title='# Blender 程序化硬表面建模自检与网格修复',
        heads=[r'^##\s*Blender 程序化硬表面建模的自检判据',
               r'^##\s*从零重建网格后必验硬边',
               r'^##\s*白模光滑、着色后扭曲的处理'],
        trigger='做 Blender 程序化硬表面建模、用 `from_pydata` 堆封闭实体、从零重建网格，或排查"白模正常但着色后扭曲"',
        backlink='Docs/Gameplay/blast-furnace-model-20260923.md',
    ),
    dict(
        target='mesh-scaling.md',
        title='# 缩放已有网格到目标尺寸（不重建几何）',
        heads=[r'^##\s*缩放已有网格到目标尺寸'],
        trigger='要把别人给好的模型改成工程尺寸、而不重做几何',
        backlink=None,
    ),
    dict(
        target='python-material-authoring.md',
        title='# 用 Python 造材质／材质实例：实战踩坑表',
        heads=[r'^##\s*用 Python 造材质'],
        trigger='用无头 Python 建/改材质、材质实例、Niagara 材质，或材质"能编译但没接对"',
        backlink='Docs/Building/fountain-water-20260918.md',
    ),
    dict(
        target='in-editor-asset-authoring.md',
        title='# 在运行中的编辑器里做资产',
        heads=[r'^##\s*在运行中的编辑器里做资产'],
        trigger='必须进编辑器操作（活物理、视口相关、只有编辑器能做的资产操作）时',
        backlink='skills/ue5-auto-assistant/references/editor-open-development.md',
    ),
]

TRIGGER_TABLE_HEADING = '## 触发表：什么时候读哪份 references'
POLICY_TAG = '## 1. 参考与三视图先行'


def split():
    text = SKILL.read_text(encoding='utf-8')
    lines = text.splitlines()
    report = dict(moved=[], triggers=[], written=[])
    remaining = list(lines)

    for spec in MOVES:
        chunks, keep = [], []
        i = 0
        while i < len(remaining):
            line = remaining[i]
            if any(re.match(h, line) for h in spec['heads']):
                j = i + 1
                while j < len(remaining) and not ANY_HEAD.match(remaining[j]):
                    j += 1
                chunks.append('\n'.join(remaining[i:j]).rstrip())
                i = j
                continue
            keep.append(line)
            i += 1
        if not chunks:
            report['moved'].append(dict(target=spec['target'], sections=0, chars=0,
                                        status='SKIPPED: heading not found'))
            continue

        body = '\n\n'.join(chunks)
        header = [spec['title'], '']
        if spec['backlink']:
            header += ['> 正本／相关记录：`%s`。本文件只保留可复用技法，任务过程与数值以正本为准。' %
                       spec['backlink'], '']
        header += ['> 本文件由 `asset-model-workflow/SKILL.md` 按「复用面」拆出；入口只留触发表指针。', '']
        (REFS / spec['target']).write_text('\n'.join(header) + body + '\n', encoding='utf-8')

        report['moved'].append(dict(target=spec['target'], sections=len(chunks),
                                    chars=len(body),
                                    verified_in_new_file=(body in
                                                          (REFS / spec['target']).read_text(encoding='utf-8'))))
        report['triggers'].append('| %s | [%s](references/%s) |' %
                                  (spec['trigger'], spec['target'], spec['target']))
        remaining = keep

    table = [TRIGGER_TABLE_HEADING, '',
             '入口只保留每次都要用的流程与不变量。下面这些是**对一类任务**都有效的技法，',
             '遇到对应情形再读，不要预先全部加载：', '',
             '| 什么时候读 | 读哪份 |', '| --- | --- |'] + report['triggers']
    table += ['', '任务过程、数值与验收记录属于「那一次」，在 `Docs/` 里；上面每份 references 都标了正本链接。', '']

    anchor = next((k for k, l in enumerate(remaining) if l.startswith(POLICY_TAG)), None)
    if anchor is None:
        raise RuntimeError('anchor heading %r not found' % POLICY_TAG)
    out = remaining[:anchor] + table + remaining[anchor:]
    new_text = '\n'.join(out) + ('\n' if text.endswith('\n') else '')
    SKILL.write_text(new_text, encoding='utf-8')

    report['skill_before'] = len(text)
    report['skill_after'] = len(new_text)
    report['skill_links_before'] = text.count('](')
    report['skill_links_after'] = new_text.count('](')
    return report


if __name__ == '__main__':
    result = split()
    (HERE / 'split_asset_model.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                 encoding='utf-8')
    print('SKILL %d -> %d chars  (-%d, est. tokens -%d)   links %d -> %d'
          % (result['skill_before'], result['skill_after'],
             result['skill_before'] - result['skill_after'],
             round((result['skill_before'] - result['skill_after']) / 3.2),
             result['skill_links_before'], result['skill_links_after']))
    for m in result['moved']:
        print('  -> %-38s %d 节 %6d 字符  新文件逐字校验=%s'
              % (m['target'], m['sections'], m['chars'], m.get('verified_in_new_file')))
