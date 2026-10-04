# 山岳符文

唐刀限定，槽位 `blade_2`，ID `mountain_rune`，金色专属卡片。

- 全部近战攻击伤害 +10%：使用 `all_attack_damage_mult=1.1`，覆盖属性、附加伤害与快速近战的独立公式；不增加法术伤害。
- 所有该武器攻击的击退距离 ×1.5：普攻／重击／上挑沿用武器击退，快速近战、旋风、冲刺斩各自包含技能附加距离。原值为零仍为零；不改变击飞高度、击倒时长、弹反击退或韧性控制门槛。
- 韧性伤害 ×1.5：沿用攻击快照的通用削韧倍率，继续与抗性、虎啸、龙威及其他改造组合结算。
- 祥云符文当前已是攻速 +10%；安装脚本按目标值写 `1.1`，不累加为 +20%。

## 制作与接入

三峰主印、层岩刻纹、矿脉与朝刀尖收束的山脊，土黄／琥珀微光。使用当前三种刀面母材质的独立副本，包含游龙接缝修正版，保留原 PBR、祥云及通用符文。新增 mode 7，复用既有投射空间与无 Tick 的材质动画。

`prepare_artwork.py` 仅从 imagegen 原稿提取 alpha 作为线性遮罩，保留全部原始图案。`import_background.ps1` 经现有资产互斥导入、保存，随后 `catalog_extension.py` 合并目录、材质绑定与旋风材质映射。重运行只更新本配件，保留其他配件与物品存档。

`Icons` 为 imagegen 制作的中性灰阶山岳浮雕金属框菜单图；`Artwork` 为原始透明纹样与材质遮罩，实战土黄色由 HLSL 给出。

生成提示：图标以现有四角铆钉金属框为参考，中心为三峰山岳及层岩浮雕，无字、无武器、灰阶；遮罩为纵向山岳印记、层叠岩脉、渐细尖峰、透明背景，最终采用不带光晕的黑色刻纹 alpha。

来源：内置 image_gen 本轮原创；边框参考项目既有 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png`。保存路径见 `Records/artwork.json`，未引入第三方模型或图像。

## 交付状态

源码及作者脚本已落盘。8 项 UE 资产（遮罩、菜单图、三套刀面材质及其旋风版本）已在后台实际导入并保存，目录及材质绑定已登记；回执为 `Records/import_receipt.json`。Game 和 Editor 的 Win64 Development 构建均成功，正式 EXE／DLL 已链接落盘；日志为 `Records/build-game-retry.log` 和 `Records/build-editor.log`。未主动打开编辑器、运行游戏或自动测试，由用户验收。

必要构建中仅附带修正 `M4MuzzleVisual.cpp` 的局部 `Mesh` 变量遮蔽角色成员问题，改名为 `SuppressorMesh`，未改变枪口行为。
