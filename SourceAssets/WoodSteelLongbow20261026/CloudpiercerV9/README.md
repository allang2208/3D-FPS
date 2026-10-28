# 穿云弓体 · Cloudpiercer V9

高地长弓专属特殊改造，稳定 ID `highland_cloudpiercer`，安装槽 `riser`。

| 属性 | 效果 |
| --- | ---: |
| 最大飞行距离 | +45% |
| 暴击伤害加成 | +75% |
| 物理伤害 | +10% |
| 拉弓速度加成 | −35% |
| 体力消耗 | +55% |
| 持续拉弓耗体 | +55% |

字段沿用现有武器详情与改造面板。玩家说明统一使用“暴击伤害 +75%”；内部 `crit_damage_bonus=0.75` 仍按加法结算，不改为最终暴击伤害乘 1.75。最大飞行距离为箭矢飞行上限；体力消耗为单次出箭消耗，持续拉弓耗体为每秒消耗。

物理伤害 +10% 同时作用于基础物理与附加物理，魔法伤害部分不变。单独安装于基础高地长弓时，最大飞行距离为 69.6 m。拉弓速度沿用统一速度加法区；没有其他修正时满拉约 2.15 s，穿心箭基础蓄力门槛约 4.62 s。速度 −35% 不等于耗时 +35%；实际拉弓耗时由既有评估器计算。

外观采用深烟褐层压木、浅色层压边线和连续银钢双脊，中央收束于菱纹护片。保留握把、箭台、瞄具、上下弦挂点和原 11 骨骨架。89,242 三角面为独立弓体，不含外部改造件或动态弦；新增顶点从原模型最近三角面重心插值取得蒙皮权重。

- `HighlandLongbow_Cloudpiercer_Production.blend`：可编辑制作源。
- `Export/SK_HighlandLongbow_Cloudpiercer.fbx`：正式骨骼网格导出。
- `author_assets.py` / `authoring.json`：模型、材料与导出参数。
- `author_part_reference.py`：图标的实际部件输入场景。
- `bow_woodsteel_riser_highland_cloudpiercer.png`：标准灰阶金属框图标。
- `icon-prompt.txt`：内置 imagegen 使用的完整提示词。
- `import_assets.py` / `import-receipt.json`：四个专用材质、一个骨骼网格和一个图标纹理的后台保存。
- `install_catalog.py` / `catalog-receipt-*.json`：从执行时的最新目录定向接入。
- `completion.json`：本批最终资产、目录、构建及未测试状态。

包目录为 `/Game/Weapons/WoodSteelLongbow20261026/CloudpiercerV9/`。图标纹理位于现有 `FramedBows` 目录。材质复用原木纹 PBR，以顶点颜色红通道和反向金属遮罩限制胡桃木染色范围。

本批未启动交互编辑器或游戏，未执行玩法、画面或联机测试。构建状态以 `completion.json` 与对应日志为准。
