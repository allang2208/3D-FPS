# 201 ADS 右侧衣袖拉伸修复

> 发布说明：此页保留当时制作记录；本机模型、回执与图片不公开，已退役资料从 trash 恢复。当前恢复入口见 [201 发布记录](../../../Docs/Weapons/lmg201-publication-20261001.md)。

2026-09-29，用户明确要求检查并调整截图中的右侧异常。工程：`D:/FPS3D/FPSGAME`。

## 原因与证据

截图右侧贯穿画面的金属长片来自 `ChainmailSharedSway20260929/PKM/SK_PKM_ChainmailShirt` 的右侧肩部／上臂衣袖。使用当前 201 压缩 `aim` 姿态，加入该衣袖后离线复现同样的右侧轮廓；枪体、裸手和手套单独蒙皮未出现该异常。

201 与 PKM 共用的手臂骨骼参考变换相符，实际参与衣袖蒙皮的骨骼没有缺失。问题位于衣袖权重：部分腋下顶点的旧 `spine_04` 权重约 0.60–0.76，现用 201 裸臂对应区域已使用锁骨及上臂 twist 骨。躯干与肩臂运动不一致，将旧衣袖拉成长片。不能据此重做腕部动作或隐藏整条手臂。

## 已保存的修改

- 新建 201 原生 191 骨骼的衣袖资产：`/Game/Characters/ModularOutfit20260924/LMG201ADS34/SK_LMG201_Chainmail_ADS34`。
- 仅修正右侧肩部／上臂 2,068 个顶点的蒙皮，以现用 201 裸臂对应侧、对应解剖区域的三角面做重心插值。沿用最多 8 个影响骨骼并归一化。
- 保持原衣袖顶点位置、三角形、UV、材质、内衬和摆动遮罩；保存后读回顶点位置最大差为 0，三角拓扑一致。左袖、远端小臂、腕口与手套未改。
- 衣袖 LOD 已随新权重重新生成并保存；保留现用共享小幅摆动，无新增布料模拟。
- `Content/ColdSteelData/modular_outfits.json` 中，当前 Cover10 视模使用独立 `LMG201` 装备 profile。锁子甲指向新衣袖，其余现有物品和露指皮肤保留原有 PKM 家族路径，避免新增 profile 后丢失已有装备。
- 枪械网格、所有动作、握点、瞄准线和镜头位置未改；PKM 原衣袖及旧 201 枪械资产未删除。没有修改 C++，无需模块构建。

## 本次检查范围

`collect_live.py` 在工作开始时读取到游戏未运行，没有启动 PIE。使用当前资产和压缩瞄准姿态进行本次 ADS 问题的离线蒙皮与同视角诊断。新资产保存后通过 `read_saved.py` 读回实际顶点／骨骼权重再投影：原右侧屏幕边缘区域有 51 个衣袖顶点，修复后为 0。

这是针对截图问题的离线检查，不是实机截图或全动作验收；未自动启动游戏，其他动作未追加回归。配置在 BeginPlay 读取，下一次进入游戏会使用新衣袖。

诊断图中蓝色为衣袖，棕色为手套；仅显示用于区分问题来源的网格，不包含独立挂载的前后瞄具／脚架，正式游戏中这些部件未移除。

| 修复前（复现右侧长片） | 保存后读回 |
| --- | --- |
| before（本机历史资料：`SourceAssets/LMG20120260927/ADS34/ads_cloth_before.png`） | after（本机历史资料：`SourceAssets/LMG20120260927/ADS34/ads_cloth_after.png`） |

## 交付文件

- `delivery.json`：资产及配置保存回执、SHA256、保留范围。
- `sources.json`、`201_weights.json`、`shirt_weights.json`：本次当前骨架、姿态与原始蒙皮来源。
- `author_sleeve_fit.py`、`weight_edits.json`、`fit_report.json`：局部权重制作与具体改动。
- `install.py`：原生骨架派生、LOD、保存与配置接入。
- `installed_weights.json`、`fit_projection_report.json`：保存后实际网格读回及 ADS 对照。
- `LMG201_Chainmail_ADS34_Editable.blend`、`SK_LMG201_Chainmail_ADS34.fbx`：可编辑源和交换格式。
- `Before/modular_outfits.json`：本轮接入前的配置备份，不用于整体覆盖并行改动。

后续重新制作 201 衣袖时，以当前 Cover10 原生手臂权重为拟合来源，保留本次装备映射；不要重新发布旧 PKM 衣袖权重覆盖该修复。
