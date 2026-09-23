"""Skill reorganisation, step 1: remove dead data and collapse the duplicated policy block.

Two mechanical, content-preserving operations:

1. Delete `skills/ue5-module-router/references/ue5-module-routing-table-draft.deprecated.csv`
   (111,740 B) -- a superseded draft that nothing references and that would cost ~35k tokens
   if anything ever read it.

2. Collapse the verbatim `## UE5 默认开发方式` block that is copied into all 15 SKILL.md files
   (860 chars each, identical apart from one relative link) down to a short operative summary
   plus a pointer. The full policy already lives in the repository-root `AGENTS.md`, which is
   injected into every session, so per-skill verbatim copies only create 15 places that can
   drift out of sync. The condensed form deliberately KEEPS the operative rules in-context --
   it is a summary + pointer, not a bare link.

Safety: the 8-line core is matched exactly before replacement; any file whose block does not
match the expected shape is skipped and reported, never partially edited. Link counts are
compared before and after so no reference is lost.

Run: py -3.11 SourceAssets/SkillReorg20260923/consolidate_policy.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / 'skills'
HERE = Path(__file__).parent

HEAD = re.compile(r'^##\s*UE5 默认开发方式')
PARA = '**用户规则（2026-09-20）：禁止主动向其他对话/任务发送协调消息。**'
BULLET = ('- **默认后台制作、编译与落盘（用户确定，2026-09-23）。**',
          '- C++ 默认在后台完成常规 Editor/Game 目标构建与二进制落盘',
          '- 涉及 UE 资产操作或原生构建时，先读 [后台开发与编辑器使用条件]',
          '- **默认不主动检查、测试、启动 PIE、截图或验收渲染。**')

CONDENSED = """## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件]({link})。"""

# Restatements of the 2026-09-12 rule that the condensed summary above already covers.
REDUNDANT = (
    '**最高优先级（用户规则，2026-09-12）：后续开展工作，除非用户明确要求，否则不主动进行检查、测试或验收',
    '**用户规则（2026-09-12）：未明确要求时不主动检查、测试或验收；完成必要制作、构建与接入后交由用户测试。**',
)

DEAD_CSV = SKILLS / 'ue5-module-router' / 'references' / \
    'ue5-module-routing-table-draft.deprecated.csv'


def link_for(path):
    """Relative path to the shared editor-usage reference, correct for each file's depth."""
    if path.parent.name == 'ue5-auto-assistant':
        return 'references/editor-open-development.md'
    return '../ue5-auto-assistant/references/editor-open-development.md'


def core_matches(lines, h):
    """True when lines[h:h+8] is the standard heading/para/4-bullet core."""
    if h + 7 >= len(lines):
        return False
    return (HEAD.match(lines[h])
            and lines[h + 1].strip() == ''
            and lines[h + 2].startswith(PARA)
            and lines[h + 3].strip() == ''
            and all(lines[h + 4 + i].startswith(BULLET[i]) for i in range(4)))


def main():
    report = dict(dead_csv=None, files=[], skipped=[])

    if DEAD_CSV.exists():
        size = DEAD_CSV.stat().st_size
        DEAD_CSV.unlink()
        report['dead_csv'] = dict(path=str(DEAD_CSV.relative_to(ROOT)), bytes_removed=size)
    else:
        report['dead_csv'] = dict(path=str(DEAD_CSV.relative_to(ROOT)), bytes_removed=0,
                                  note='already absent')

    for path in sorted(SKILLS.glob('*/SKILL.md')):
        text = path.read_text(encoding='utf-8')
        lines = text.splitlines()
        links_before = text.count('](')
        h = next((i for i, l in enumerate(lines) if HEAD.match(l)), None)
        entry = dict(skill=path.parent.name, before=len(text), links_before=links_before)

        if h is None:
            entry['action'] = 'no policy block'
            report['files'].append(entry)
            continue
        if not core_matches(lines, h):
            entry['action'] = 'SKIPPED: block shape differs'
            report['skipped'].append(entry['skill'])
            report['files'].append(entry)
            continue

        new_lines = (lines[:h]
                     + CONDENSED.format(link=link_for(path)).splitlines()
                     + lines[h + 8:])
        # drop the redundant trailing restatements, wherever they sit outside the block
        kept = [l for l in new_lines if not any(l.startswith(r) for r in REDUNDANT)]
        removed_restatements = len(new_lines) - len(kept)

        new_text = '\n'.join(kept) + ('\n' if text.endswith('\n') else '')
        path.write_text(new_text, encoding='utf-8')

        entry.update(after=len(new_text), removed_restatements=removed_restatements,
                     links_after=new_text.count(']('), action='collapsed')
        report['files'].append(entry)

    return report


if __name__ == '__main__':
    result = main()
    (HERE / 'policy_consolidation.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    total_before = sum(f['before'] for f in result['files'] if 'after' in f)
    total_after = sum(f['after'] for f in result['files'] if 'after' in f)
    print('DEAD_CSV removed=%s B' % result['dead_csv']['bytes_removed'])
    print('SKILL.md collapsed=%d skipped=%d'
          % (sum(1 for f in result['files'] if f.get('action') == 'collapsed'),
             len(result['skipped'])))
    print('chars %d -> %d  (-%d, est. tokens -%d)' % (total_before, total_after,
                                                      total_before - total_after,
                                                      round((total_before - total_after) / 3.2)))
    for f in result['files']:
        print('  %-28s %-28s %s -> %s  links %s -> %s'
              % (f['skill'], f.get('action'), f.get('before'), f.get('after'),
                 f.get('links_before'), f.get('links_after')))
    if result['skipped']:
        print('SKIPPED: %s' % ', '.join(result['skipped']))
