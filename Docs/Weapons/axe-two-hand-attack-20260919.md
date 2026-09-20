# 伐木斧：右上蓄势、向左挥砍 V1（2026-09-19）

后续用户反馈手腕扭曲、攻击过于线性，已继续制作 [V2 腕肘支撑与节奏优化](axe-two-hand-attack-v2-20260919.md)。本文保留 V1 的制作记录，不再代表最新作者参数。

用户要求参考剑类蓄力攻击，为伐木斧制作双手向右上方举起、随后向左挥砍的攻击。沿用 H3 横持待机、朝外刃向和毫米级抓握退让；本轮制作并接入 `Swing`、`HitRecover`，左键仍是一次点击完成一次采集挥击。

## 参考与改编

- 已阅读并查看符文剑 `ChargedErgoV43/ReviewV45/sheet_fp.png` 和蓄满第一人称图；源 `AzureRunesword_ChargedHoldV45.blend` 内的 HeavyCharge 为 480 fps、0–960 帧、2 秒，HeavyRelease 为 0–480 帧、1 秒，均非循环。原释放接触段为 0–0.075 秒。
- 作者脚本读取参考的抬举、蓄满、释放和回收姿态，记录于 `SourceAssets/AxeTwoHandAttack20260919/sword_reference.json`。采用侧上方抬举、保留屈肘、短停加载、快速释放与侧方回握的动作意图。
- 斧头的曲柄、双手握距和头部重量分布不同，因此重新设计工具弧线和时钟；不是把剑动画直接重定向到斧头，也没有新增按住蓄满才释放的输入机制。
- 右手靠近斧头控制刃向，左手靠柄尾提供牵引；不交换双手，不在挥砍中重新拟合握点。头部沿右上到前方再向左下运动，刃口方向沿扫掠切向。

## 运行时节奏

| 时间 | 动作 |
| --- | --- |
| 0–0.18 s | 从当前横持向右上抬起 |
| 0.18–0.26 s | 继续提高手部并向右后侧蓄势 |
| 0.26–0.30 s | 顶点短停 |
| 0.30–0.48 s | 加速向左斜横挥砍，挥动声沿既有时钟在 0.312 s 触发 |
| 0.48 s | 唯一采集提交点，命中声与原粒子仍由成功提交驱动 |
| 空挥 0.48–0.62 s | 顺势向左带出并减速 |
| 空挥 0.62–1.10 s | 经左下侧回收，再回到 H3 基础持握 |
| 命中 0.48–0.515 s | 手与斧头一同制动，停留约 35 ms |
| 命中 0.515–1.10 s | 轻微反向回弹、退开，再回到 H3 基础持握 |

命中与空挥共用同一个接触姿态。整个持握区间使用 `hand = WPN_root × grip_local`，手指、骨长和缩放保持 H3。肩肘按两骨关系求解；上臂从前臂方向传回旋转基准，向待机两端逐渐恢复原有轴向关系，辅助骨跟随完整骨段。

## 时钟接入

现有 `ProductionToolMotion.cpp` 使用固定作者时钟：Swing 0.68 秒、接触 0.24 秒、HitRecover 0.44 秒。新动作按这套规范导出 150 fps 动画，运行时继续使用既有分段映射，避免给矿镐引入第二套播放逻辑。

- 斧头定义改为 `swing_seconds = 1.10`、`contact_seconds = 0.48`。
- 作者前段 `0…0.24` → 实际 `0…0.48`；作者后段 `0.24…0.68` → 实际 `0.48…1.10`。
- `ColdSteelProductionTools.cpp::NormalizeProductionState` 对旧斧头同步这两个目录时序字段。只对斧头启用时序同步，矿镐、铲子原时序不变；物品身份、采集次数、产出、射线与体力消耗不变。
- 旧存档在下次载入时取得新时序；本轮没有直接修改用户存档。

## 文件与恢复

- 参数：`SourceAssets/AxeTwoHandAttack20260919/motion.json`。
- 制作：同目录 `build_attack.py`，输出 `Axe_TwoHand_Attack_Editable.blend` 和 `Export/A_Harvest_Axe_Swing.fbx`、`A_Harvest_Axe_HitRecover.fbx`。
- 导入：`Tools/Production/import_axe_two_hand_attack.py`，覆盖 `/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Swing` 与 `A_Harvest_Axe_HitRecover`。
- 替换前两条动画、工具目录和旧存档同步源文件保存在 `SourceAssets/AxeTwoHandAttack20260919/Before/`。
- H3 Idle 资产、模型和材质未改动。Walk / Equip 仍为旧单手动作，本轮没有处理移动/装备到双手持握的过渡。

完成制作、导出及必要原生编译；导入回执位于同目录 `import_receipt.json`。没有渲染、启动游戏、测试或验收，动作观感和采集手感由用户实机确认。编译记录：`Saved/BuildEditor/build-20260919-173219.log`。
