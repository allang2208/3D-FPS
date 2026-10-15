# M66 V14 握拳砸地

用户要求将 V13 张掌砸地改为握拳，并同步攻击范围。继续原 M66、V10 模型/蒙皮、V08 横扫、背孔黑烟和 135 点物理伤害/6 秒冷却。

## 握拳制作

参考 `ue5-fps-arms-animation/references/unarmed-idle.md` 的掌语义空间拳形与 `door-guard-native-binding.md` 的完整骨链规则。具体姿态源为 `SourceAssets/StaffQuickCombat20261001/FixV2/fist-profile-v2.json`。使用掌前向、桡侧、手背三轴适配 M66 的五指和原生四段链，保留骨长、绑定和权重；不把人手局部 Euler 直接复制给异形骨架。

- 0.20–0.88 s 四指收拢，0.42–1.10 s 拇指较晚从外侧扣合。
- 落击与回弹保持闭拳，2.35–3.25 s 松拳，3.50 s 回到原准备姿态。
- 保留 V13 的整身时序与完整腕臂辅助骨；围绕肩部小幅适配落拳并补充屈膝支撑，以实际闭拳蒙皮表面拟合地面。
- 编辑源为 `Authoring/M66_fist_slam_v14.blend`，导出为 `Export/A_M66_FistSlam_V14.fbx`。原 V13 保留恢复。

## 命中合同

以实际闭拳表面拟合 24 个内部球心，半径由最远表面点加 1.5 cm 余量生成，本版为 20 cm（原张掌为 32 cm），写入 `Records/fist_contact_definition.json`。在 UE 按原生参考骨架的对应坐标转换球心，沿新动画手腕生成 1.48–1.72 s 的 17 个采样帧。起手可达性和服务器连续扫掠共用这份数据，不保留张掌指尖轨迹，也不另加远距离震地伤害。

延续现有服务器权威、单动作单目标去重、墙体遮挡、冰墙接触、眩晕/冻结/击飞/死亡取消攻击。330 cm 是起手上限，仍须实际拳路可以触达；原停距 270 cm。客户端显示同一攻击类型与开始时钟，不能独立结算伤害。

## 接入状态

2026-10-15 09:19 已通过后台 commandlet 实际导入动画，并保存共用骨架及原 `BP_M66RigPreview`。进程 13940 正常退出，退出码 0；回执为 `Records/motion_import.json`、`Records/character_install.json` 和 `Records/install-20261015-091911/`。原角色已改用 `/Game/Monsters/IncineratorBossM66/FistSlamV14/A_M66_FistSlam_V14`，保存了 17 帧、每帧 24 个拳面球心和 20 cm 判定半径。

此次不修改原生 C++，使用已有 V13 动作切换和命中机制，无需新增 DLL 构建。通过 F6 原 M66 入口重新生成即可体验。未运行游戏、渲染或联机测试，由用户体验。
