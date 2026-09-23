"""Skill reorganisation, step 3: split ue5-fps-arms-animation/SKILL.md.

This skill already has a correct trigger table (`## 按问题读取`, 30+ trigger -> reference rows).
What it also has is a single level-2 block, `## 读参考动作先分辨"哪只手做什么"` plus its 14 dated
`###` lessons (~6.4k chars), that lives inline.

Those lessons were checked against every file in references/: **0 hits**. They are unique
accumulated experience, not duplicates of a reference -- which is exactly why the operation is a
MOVE and not a delete. They are also topically coherent (all about measuring before writing:
reach, fingertip distance, frustum clipping, local-vs-world vectors, reload visibility), so they
move as one unit.

The entry keeps its trigger table and gains one row pointing at the new reference.

Run: py -3.11 SourceAssets/SkillReorg20260923/split_fps_arms_skill.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / 'skills' / 'ue5-fps-arms-animation'
SKILL = SKILL_DIR / 'SKILL.md'
REFS = SKILL_DIR / 'references'
HERE = Path(__file__).parent

HEAD2 = re.compile(r'^##\s')
MOVE_HEAD = re.compile(r'^##\s*读参考动作先分辨')
TARGET = 'measure-before-writing.md'
TITLE = '# 先量后写：读参考动作与动手前的测量方法'
TRIGGER_ROW = ('- 复刻／迁移参考动作、或动手前要先量（可达性、指尖到目标、视锥+近平面穿模、'
               '局部 vs 世界向量、换弹可见性、重定向共轭）：[先量后写](references/%s)。' % TARGET)
ANCHOR = '## 读参考动作先分辨'          # the block itself; trigger row goes into 按问题读取
TRIGGER_ANCHOR = '- 手指扭曲、穿模、抓握、腕肘变形、重定时或冲击感'


def main():
    text = SKILL.read_text(encoding='utf-8')
    lines = text.splitlines()
    report = dict(target=TARGET)

    start = next((i for i, l in enumerate(lines) if MOVE_HEAD.match(l)), None)
    if start is None:
        raise RuntimeError('block heading not found')
    end = next((i for i in range(start + 1, len(lines)) if HEAD2.match(lines[i])), len(lines))
    block = '\n'.join(lines[start:end]).rstrip()

    header = [TITLE, '',
              '> 由 `ue5-fps-arms-animation/SKILL.md` 按「复用面」拆出：这些都是**对一类任务**',
              '> 有效的测量方法，不是某一次的过程记录；入口只留触发表指针。',
              '> 核对于 2026-09-23：这些条目在拆分前**只存在于入口**，references 里 0 命中，',
              '> 因此是独一无二的积累，搬迁而非删除。', '']
    (REFS / TARGET).write_text('\n'.join(header) + block + '\n', encoding='utf-8')

    report.update(sections=len(re.findall(r'^###\s', block, re.M)),
                  chars=len(block),
                  verified_in_new_file=(block in (REFS / TARGET).read_text(encoding='utf-8')))

    remaining = lines[:start] + lines[end:]
    # add the trigger row after the pose/contact row, inside the existing trigger table
    idx = next((i for i, l in enumerate(remaining) if l.startswith(TRIGGER_ANCHOR)), None)
    if idx is None:
        raise RuntimeError('trigger table anchor not found')
    remaining = remaining[:idx] + [TRIGGER_ROW] + remaining[idx:]

    new_text = '\n'.join(remaining) + ('\n' if text.endswith('\n') else '')
    SKILL.write_text(new_text, encoding='utf-8')

    report.update(skill_before=len(text), skill_after=len(new_text),
                  links_before=text.count(']('), links_after=new_text.count(']('))
    return report


if __name__ == '__main__':
    result = main()
    (HERE / 'split_fps_arms.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                              encoding='utf-8')
    print('SKILL %d -> %d chars (-%d, est. tokens -%d) links %d -> %d'
          % (result['skill_before'], result['skill_after'],
             result['skill_before'] - result['skill_after'],
             round((result['skill_before'] - result['skill_after']) / 3.2),
             result['links_before'], result['links_after']))
    print('moved %d ### lessons, %d chars, verbatim verified=%s'
          % (result['sections'], result['chars'], result['verified_in_new_file']))
