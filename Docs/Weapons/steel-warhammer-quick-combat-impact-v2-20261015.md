> 当前快速近战已替换为 [锤头直刺 V3](steel-warhammer-quick-combat-head-thrust-v3-20261015.md)。本文横柄前顶方案已被用户否定，保留作历史恢复记录。

# 双手战锤快速近战：前顶强化 V2

按用户要求加大双手横柄前顶幅度、加快出手并自然回收。总时长仍为 0.5 秒，命中仍为 0.15 秒，继续使用原快速近战数值、查询参数和服务器结算。

## 动作修改

- 蓄势收柄到 0.075 秒，随后在 75 毫秒内迅速前送。原版出手段为 85 毫秒。
- 命中时整体前移从 14 cm 增为 21.5 cm；0.175 秒惯性顶点从 15.5 cm 增为 24 cm。蓄势后到接触的前顶行程为 27 cm，接触时仍有 2 m/s 的前进速度，随后迅速制动并连续回收。
- 保留原待机握点、握距和五指姿态；双手与柄身作为同一组变换。沿用柄身压平 11°、顶点 12°，不增加腕部扭转来制造摆幅。
- 肩带随前后位移承担 60% 的轴向行程，并随前顶下沉。命中时肩带基础偏移为前移 12.9 cm、下移约 4.32 cm；顶点前移 14.4 cm、下移 5.5 cm。额外行程由肩部带动，双手相对肩部的伸展量接近 V1。
- 肩带与握柄使用同一条连续速度、加速度的位置曲线，避免两层错时回收。大小臂使用原生骨长、肘部弯曲和前臂渐进扭转分配，手腕跟随实际握柄，低位肩部设计用于保持中央视野。
- 接触后的前进速度连续减到零，顶点不插入静止帧段；随后在 0.5 秒内回到原待机。
- 镜头前送从 1.25 cm 调至 1.8 cm，俯仰带动从 0.55° 调至 0.70°；保留既有命中反馈与总恢复时钟。

## 文件和接入

- 源目录：`SourceAssets/SteelWarhammer20261014/QuickCombatImpactV2/`。
- 源文件：`author_quick_combat.py`、`Warhammer_QuickCombat_Editable.blend`。
- 导出：`Export/A_Warhammer_QuickCombat.fbx`，300 fps。
- 正式资产继续使用 `/Game/Weapons/SteelWarhammer20261014/QuickCombatV1/A_Warhammer_QuickCombat`，装备和输入入口不变。
- 运行时节拍和镜头：`Source/FPSGAME/Production/WarhammerQuickCombatMotion.h`。
- 接触点由新作者脚本按两手之间的柄身表面重写 `WarhammerQuickCombatMarker.h`；查询半径保持 32 cm，伤害、体力和改造保持原值。
- 修改前正式资产、运行时头文件、V1 作者脚本和导入脚本保存在 `Before/`。完成后 V1 制作和导入入口转发到 V2，防止误导入旧动作。

## 交付记录

实际制作、导入保存、正式构建及完成记录分别写入 `authored.json`、`import_receipt.json`、`build_receipt.json`、`delivery.json`。仅这些实际回执代表对应步骤完成。

本轮动画已通过现有编辑器互斥桥导入、完成动画编译并保存，回执版本为 `ShaftCheckImpactV2_20261015`。编辑器没有未保存包，按已有授权结束 PIE 并正常退出后，`FPSGAMEEditor` 和 `FPSGAME` 两个正式目标均构建成功，exit 0、`Result: Succeeded`；分别耗时 31.88 秒和 23.45 秒。新版入口与交付回执已落盘。

按用户规则，仅后台制作、导入保存和必要编译；不启动编辑器或游戏，不追加渲染、测试或验收。实际动作、关节外观、视野遮挡和手感由用户体验。
