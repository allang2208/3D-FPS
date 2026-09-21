# 闪电与锁定连锁（2026-09-20）

入口记录：项目 `Docs/Skills/lightning-migration-20260920.md`；当前状态为已制作接入、必要构建完成，未运行 PIE 或实机验收。

- 原 `lightningStrike` 是锁定连锁：目标数 `1 + floor((L-1)/5)` 包含首目标；每跳找最近可见且未命中的敌人，不重复、不隔墙。3D 适配明确区分相机瞄准容差、有效射程和跳跃距离。
- 原闪电本轮保留魔攻＋智力公式、30 MP 和 12 秒冷却；不要把火球／冰锥后续单独调整的平衡数据误套进来。实际数值以 `skills.json` 与 `LightningStats` 为准。
- 排队不扣费；有效起手提交一次资源并开始冷却；释放接触帧复查原锁定目标，失效保留已提交成本。临时左手冲突沿用共享手势，长期占手沿用拒绝提示。此类锁定法术不套用悬浮弹道预览。
- 连锁命中、击杀、多目标与暴击修炼按整次事件合并。感电增加持续时间与层数，达到阈值清空并过载；过载敌我以施法者为准，不复制原目标阵营筛选导致的反向伤害，不递归感电或重复刷技能经验。
- 使用现有 `/Game/_SplineVFX/NS/NS_Spline_ElectricLightning`，专用副本 `/Game/Skills/Lightning/NS_LightningChain`。源码 Actor 以 spline 为 root、Niagara 附在下面，原 spline DI 从 attach root actor 获取组件。保留原包，先读输入再改副本。
- 形状只生成一次，0.5 秒保持＋0.25 秒淡出。CPU ribbons 与 GPU Detail 都需要正确边界；运行期统一清理。原发射器 Infinite duration mode 会隐藏 Loop Duration，不能在隐藏时写该输入。作者入口 `Tools/Skills/build_lightning_assets.py`。
- 详情与释放共用 `LightningStats`；补齐分类、当前／下级效果、修炼、升级通知、混合快捷栏、冷却及缺蓝、F6 调级、旧档补项和图标恢复。
- 图标、原音频转码与 provenance 在 `SourceAssets/Lightning20260920`。本机原包与音频许可不等于公开再分发授权；不默认运行测试或验收。

## 电弧不可见修复经验

用户反馈首轮有伤害／音效但无可见电弧。原 `ScaleColor002` 的 RGB 输入实际是 `VectorFromFloat(User._Brightness)`，删除它会断开 Actor 的发光与淡出控制。当前两条 ribbon 使用明确的 `ScaleColor`，从 `Initial.Color` 乘以 `_Brightness`，避免每帧累乘；运行期恢复源资产 50 倍发光。固定形状只关闭空间 Jitter，不要把材质和电火花的 MainPowerSpeed／DetailSpeed 同时归零。修复后的实机可见性仍待用户复测，不把编译或 shader 导出当作视觉通过。

## 主角端粗、目标端细（已撤回）

原版 `_redraw` 外圈半径 30→5、内芯 11→2。曾尝试两条 ribbon 沿弧收细至外圈 60→10 cm、亮芯 22→4 cm，并更换配色与增加 Chaikin 平滑；用户随后明确认为上一版更好，该整轮调整已撤回。当前恢复原包 1–8 倍随机宽度乘 `_Width`、先前紫色与 HSV 变化、10 段固定折线、默认密度 50，保留更早的发光／淡出与电火花运动修复。不要把已否决的渐细方案当作默认标准重新接入。
