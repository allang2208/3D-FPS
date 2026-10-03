# 2011 蝮蛇防滑纹：纵向握把侧面，2026-10-03

按用户要求将 VIP 防滑纹从握把中段短覆片改为左右两侧自上而下延伸的长覆片。前后边缘从原厂握把侧面取样，鳞纹沿纵向向下排列；使用细鳞纹、浅起伏、石墨黑与原有细金属边，不扩大蝮蛇徽记。

## 部件边界

- 覆片仅从 `2011pv frame_12` 的 polymer 握把侧面制作，不使用任何 `919 2011 15rnd mag` / `mag empty` 弹匣几何。
- 上沿位于握把肩部下方；下沿沿原握把外侧大面真实斜向底边裁切，预留约 1.2 mm。排除原厂底部扩口和突起卡扣，去掉第一版纵向方案伸向底部的外扩覆边。
- 握把左右两侧分别贴合原侧面；弹匣、底板和底部扩口保持独立，不制作跨部件覆盖。
- 保留原安装坐标、WPN_root 绑定逆变换及既有材质资产路径。所有枪体与三款通用防滑纹不变。

## 制作源与接入

`author_grip.py` 生成可编辑 Blender、FBX 与 2048px 私有 PBR 贴图，`author_icon.py` 从真实覆片制作灰度图标源。`import_assets.py` 通过项目后台桥更新原 VIP 网格、三张 ViperQuiet 私有贴图及专属图标；沿用原细腻材质图与金属母版，不重建共享母版。

主网格仍为 `/Game/Weapons/PitViper2011/VipGrip20261002/SM_PitViper2011_VipViperGrip`；表面仍为 `/Game/Weapons/PitViper2011/SurfaceRefine20261003/Materials/M_PV2011_ViperQuiet`。

专属图标 `Icons/ue_pit_viper2011_reargrip_pit_viper_vip_scales.png` 使用内置 imagegen 制作，输入为本次真实模型灰度图和现有四角铆钉框；完整提示词记录在 `icon_delivery.json`。这是 UI 资产制作，不是游戏验收截图。

旧 VIP 及握把重建制作入口已指向当前长覆片；后续静纹表面制作复用当前物理尺寸的贴图，避免恢复原来的 42 mm 短贴片。描述更新仅修改此配件的文字。

属性保持用户设置：蝮蛇防滑纹腰射随机散布 −15%；SI 配件属性不变。

未启动 UE 图形编辑器或游戏；未执行测试、回归和验收渲染。实际落盘状态以 `import_receipt.json` 为准，交由用户自行查看游戏效果。
