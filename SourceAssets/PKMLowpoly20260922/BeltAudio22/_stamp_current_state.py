"""Put the true current state at the top of every PKM reload audio record.

The bodies of these files are the history of five rounds; rather than rewrite them and
lose that history, each one gets a dated banner saying what is actually installed now,
what was rejected, and where the retired attempts went.  `RESTORE_20260928.md` stays the
authority.
"""
from pathlib import Path

BASE = Path(r'D:/FPS3D/FPSGAME/SourceAssets/PKMLowpoly20260922/BeltAudio22')
TRASH_REL = 'trash/pkm-reload-debgm-attempts-20260928'

BANNER = """> **当前状态（2026-09-28 收尾，以 `ReloadTailRepair20260928/RESTORE_20260928.md` 为准）**
>
> 已装内容：**开盖 / 合盖 = 9-25 重建版**，**其余六条 = 原始剪辑（未处理，BGM 原样保留）**，
> 放栓推进未动。用户要求撤销 09-28 的 v1 / v2 / v3 三轮。
>
> **五轮全部未通过：** 9-25（尾音重建）、09-28 v1（5 条尾音）、v2（9 条尾音）、
> v3（整条 cue 前瞻门限）都被用户否决或从未验收；另有一轮 09-28 13:40 的
> `LMG20120260927/ReloadAudio14`（非本对话所写）改的是 C++ 引用，**至今未提交**。
>
> **v1 / v2 / v3 的脚本、输出、图表与 v3 还原前快照已退役到 `%s/`**，
> 含逐文件 SHA-256：`%s/RETIRED.json`。退役不等于删除，文件都还在。
>
> **下一步不该再是尾音 / 门限 / 滤波。** 参考视频是成品混音，BGM 与机械声录在同一个文件、
> 在时间和频段上都重叠，没有分轨；五种做法都撞在这面墙上。剩下的诚实选项是
> **不再从这段视频里剪，改用干净素材重做接触音**。

---

""" % (TRASH_REL, TRASH_REL)

TARGETS = ['README.md', 'BGM_FINDINGS.md', 'ReloadTailRepair20260928/TAIL_REPAIR_FINDINGS.md']
MARK = '> **当前状态（2026-09-28 收尾'

for rel in TARGETS:
    p = BASE / rel
    text = p.read_text(encoding='utf-8')
    if MARK in text:
        print('  already bannered: %s' % rel)
        continue
    p.write_text(BANNER + text, encoding='utf-8')
    print('  bannered: %s  (%d -> %d bytes)' % (rel, len(text), len(BANNER + text)))

print('\nrecords now all point at RESTORE_20260928.md and the trash manifest.')