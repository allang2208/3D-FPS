# 保留的站立受击输入

2026-09-19 从混合 revision2 制作包中保留仍在使用的 Hit_Chest；只归档旧跑步不会撤回当前站立受击。

| 本机文件 | 作用 |
| --- | --- |
| A_M2M_HitChest.fbx | Mesh2Motion CC0 源动作导出 |
| A_Mutant3_R2_HitChest.fbx | UE 原生 IK 重定向到 Meshy 骨架后的动作 |
| A_Mutant3_Stagger.fbx | 当前 0.9 s 站立受击，0.1 s 反应、保持至 0.6 s、0.9 s 收势 |

完整可编辑动作在上级目录 `Mutant3_Meshy_GodotRunner.blend` 和固定输入 `Mutant3_Meshy_CombatBase.blend`。这份固定输入按当前完整源复制，保留原相对路径；跑步脚本只重新制作 Running / RunFast。

原始 Hit_Chest 制作算法留在归档的 `revision2/author_replacements.py`，代码也可从 Git 提交 `4c3ca2a583bd911230dd6180166f1817983c69f6` 取回。那份历史脚本会同时制作已被否定的 Jog 跑步，不要当作当前安装入口执行。需要重新从原始 Hit_Chest 改动作时提取受击分支，并保持当前两条跑步。

原路径、复制位置及散列见 [归档清单](../../../../Docs/AssetArchives/mutant3-animation-20260919.json)。上述二进制不公开提交，需保留本机资产备份；源动作许可见 [Mesh2Motion 许可](../../sources/LICENSE-CC0.MD)。没有追加游戏测试。
