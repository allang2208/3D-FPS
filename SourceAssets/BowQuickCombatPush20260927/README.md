> 2026-09-27 整理：此版被 V7 替代。旧 `Export/` 已移到 `trash/melee-bow-iterations-20260927/SourceAssets/BowQuickCombatPush20260927/Export/`；作者脚本、Blend、接触拟合及回退备份仍保留。历史导入脚本的旧导出路径不再是当前重导入口。当前版本与恢复边界见 [发布记录](../../Docs/Weapons/melee-bow-publication-20260927.md)。

# 弓快速近战 V3：上方 30 cm 抓握、水平前推

按用户 2026-09-27 的新方向制作：右手抓住左手沿弓身上方 30 cm 的位置，然后双手把弓转为横向水平并向前推击。

动作仍为 0.90 秒：0–0.14 秒右手接近、合拢；0.14–0.22 秒双手转为横持并短暂后收；0.22–0.32 秒向玩家正前方快速推击；0.32–0.44 秒继续前送并制动；之后回收，0.62 秒起松开右手，0.90 秒恢复原左手持弓待机。水平推击区间不叠加左右下扫，弓长轴垂直于玩家前向；该区间源旋转保持相机 X 轴 -90°，不由三次插值产生水平角过冲。

右手使用完整 V7 抓握关系，沿上方弓身的真实弯曲中心线适配：相对原握位的高度差 30 cm，前后方向适配量约 -3.897 cm。手、弓和部件共同运动；肩肘向横持位置配合，保留原生骨长、蒙皮和完整手指抓握。当前整体持弓偏移沿用 `0,32,-12`。

运行时同步修改：

- `BowQuickCombatMotion.h` 保存 30 cm 的握点间距，命中位置使用两手之间的弓身。
- `BowWeaponComponent.cpp` 的探针改为横持弓中段，避免继续从下扫时的下弓臂发出。
- 推击占用期间渐隐原下蹲持弓侧倾及搭箭对位，避免水平动作叠加成斜持；收势时恢复。
- `FPSQuickCombatComponent.cpp` 的弓动作镜头改为后收、前送、回弹，保留原判定时点的快速近战震动。

制作源：`author_push.py` 生成 `generated_push_v3.py`、`Bow_QuickCombat.blend`、240 Hz FBX 和制作参数。导入目标沿用 `/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat`。旧 V2 动作资产保存在本目录 `Before/`，旧作者源保留在 `BowQuickCombat20260927/`。

`run_background.ps1` 等待当前 UE/构建作业结束，通过既有互斥完成后台导入与 Editor 构建。资产保存结果见 `import-receipt.json`，本轮构建结果见 `Saved/BowQuickCombatPush20260927/build-editor.log`。没有主动启动编辑器、游戏、预览、渲染或测试；新动作由用户实测。

本轮已完成资产保存及 FPSGAMEEditor 后台编译、链接，构建结果为 Succeeded。未运行新动作的游戏测试。
