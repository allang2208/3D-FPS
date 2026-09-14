# 火球技能（2026-09-14）

当前实现：`D:/FPS3D/FPSGAME/Docs/Skills/fireball-migration-20260914.md`。原配置快照及图标、特效、音频来源保存在 `SourceAssets/Fireball20260914`。

- 主动魔法沿用技能列表、详情对照与修炼卡片；全部／主动／魔法筛选均包括火球。新冷钢图标由 `skills.json` 选择，恢复脚本 `Tools/UI/prepare_cold_steel_skill_icons.py` 同步维护。
- 当前 Q/E/X/1–4 混合快捷栏支持绑定火球和交换槽位，E 优先交互、无交互目标时使用绑定技能。显示技能图标、发射提示、飞行状态和冷却；UI 不直接扣蓝或结算伤害。
- `FPSFireballComponent` 管理玩家施法状态与资产；`FPSFireballProjectile` 保存施法参数快照、飞行和爆炸表现；`ColdSteelFireballModel` 管理扣蓝、冷却及合并经验事务。魔法伤害类型与枪械／符文剑要害经验分开。
- 火球最高 20 级，50 MP，结束后 20 秒冷却；30 秒悬浮上限。原 2D 世界单位按 1.5 cm 转换；配置、效果对照与实战参数读取同一入口。
- 命中 +4、击杀另 +12；单次多目标命中／击杀各另 +10。一次爆炸的角色经验和技能经验合并保存，保存成功后发升级提示。存档版本 6，旧档补入技能，未结束火球重载后保留扣蓝并转入冷却。
- 使用 Epic Niagara Examples 的项目专用副本，并以用户导入的 Free Spline VFX 火焰纹理制作外焰，原包保留；冲击波遵循世界深度遮挡。当前已接入程序化左臂层及对应可编辑 Blend/FBX，依据手势照片制作，不宣称精确还原原 2D 第 8 帧动作。
- 2026-09-14 用户确认左手 V3 基本达到预期。完整流程转 [技能／魔法标准](../../ue5-skill-magic-workflow/SKILL.md)，手臂细节转 [施法与完整骨段](../../ue5-fps-arms-animation/references/casting-arm-volume.md)。此认可不扩大为全套 UI、武器分支和 VFX 的新回归结果；默认仍由用户测试。
