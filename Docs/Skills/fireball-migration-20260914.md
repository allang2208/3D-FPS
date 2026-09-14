# 火球迁移方案与接入（2026-09-14）

本文保留基础迁移阶段的实现记录；后续慢燃核心、外焰及左手 V3 以 [发布与恢复说明](skills-magic-publication-20260914.md) 和其链接记录为准。本轮公开范围不包含下述混合玩法代码。

依据原 game-dev 的 fireball 配置、BoltSkillSystem、FireballSystem 与 Phaser 火球表现制作。使用上轮选定的 Epic Niagara Examples 本地素材，在 `/Game/Skills/Fireball` 创建专用副本，保留原包。

## 玩法与所有权

- Q 首次凝聚、再次朝准星发射；保留最多 30 秒悬浮。一次仅一颗；命中、撞墙、到达射程时爆炸一次。结束后冷却 20 秒，开始凝聚消耗 50 MP。
- 最高 20 级；中心伤害向下取整：`80 + 10L + 魔攻 × (2 + 0.5L) + 智力 × (2.5 + 0.75L)`。球形范围内由中心 100% 衰减至边缘 50%，掩体遮挡爆炸伤害。魔法不进入枪械/符文剑要害修炼入口。
- 以原角色约 120 单位、UE 人体约 180 厘米换算，暂定 1 原单位 = 1.5 厘米：飞速 2400 cm/s，射程 1800 cm，半径 `(80 + 5L) × 1.5 cm`。统一配置可调整。
- 修炼：每个有效命中 +4，每个击杀另 +12，一次命中至少两个额外 +10，一次击杀至少两个额外 +10。空放、重复组件和召唤物不刷经验；最高级不继续积累。
- `UFPSFireballComponent` 归玩家所有，`AFPSFireballProjectile` 持有本次施法参数快照与表现；销毁/切场/死亡回收。单机运行，不宣称多人复制。
- UColdSteelStatusModel 负责扣蓝、冷却、经验和存档。旧存档补入 1 级火球，重载不恢复未结束的飞行实体，已扣魔法保留并进入该次冷却。

## 界面与输入

2026-09-14 后续快捷栏迁移已将固定 Q 改为可拖动绑定；Q 是旧档／新档初始位置，实际使用当前绑定键。交互与七槽混放规则记录在本机 `Docs/UI/skill-quickbar-plan-20260914.md`，该混合玩法记录不在本次发布范围。

- 沿用 ColdSteelSkillPage 的列表、详情、当前/下一级对照与独立修炼卡片；加入全部/主动/魔法筛选。说明按内容宽度换行，数值与短标签横排。
- 底部既有 Q 槽显示新图标、悬浮/飞行状态、冷却秒数；详情说明 Q 两段施放。消耗品 1–4 与 E 交互保留。
- UI 只读 Model 和玩家技能状态，返回焦点遵循现有页面；面板开启时不穿透 Q 施法。图标 UPROPERTY 保留，Slate 引用在 ReleaseSlateResources 释放。
- 火球凝聚与发射已追加单左臂程序化骨骼动画，依据用户后续提供的两张托掌／翻掌照片制作；运行时动作层、占用规则和可编辑源见 [火球左手动作阶段](fireball-left-hand-20260914.md)。

## 特效制作

- 凝聚和飞行主体：Epic 火球循环纹理/材质，紧凑火核、外焰与余烬。
- 后续已从 `NS_Fire` 的 `FlamesOnly` 增加独立球面火舌与余烬层，当前默认主体为 `NS_FireballBurningCore`，详见 [表面燃烧接入](fireball-surface-flames-20260914.md)。
- 短拖尾：改造 NS_RocketTrail。
- 爆炸：改造 NS_Explosion_Small，削减碎石、相机震动与后处理，补原技能橙红冲击波；墙面/地面按命中法线，空爆不强贴地。
- 冷钢图标为本次新生成素材；最终路径与来源记录保留在 SourceAssets/Fireball20260914。

## 交付边界

完成必要资产制作、导入和编译；遵循用户规则，不主动运行游戏、截图、渲染预览或回归测试。原项目尚未迁移的法杖加工、链式施法、火系饰品灼伤等系统不在本次火球基础迁移中。

## 制作记录

后续左手占用与施法阶段调整见 [火球左手动作阶段](fireball-left-hand-20260914.md)；收到两张参考图后，已接入共用的左臂程序化骨骼动画并交付可编辑源。

- 新增 `Skills/FireballTypes`、`FireballDamage`、`FPSFireballComponent`、`FPSFireballProjectile` 和 `ColdSteelFireballModel`；角色挂载组件，控制器接入 Q，配置与存档技能版本升至 6。
- `ColdSteelSkillPage` 接入列表、效果对照和修炼卡片；`ColdSteelFireballHUD` 维护 Q 槽图标与实时状态。新图标已复制至 `Content/ColdSteelData/Skills/fireball_cold_steel.png`，恢复脚本已登记新来源。
- `Tools/Skills/build_fireball_assets.py` 创建并保存六项资源：`MI_FireballCore`、`NS_FireballCore`、`NS_FireballTrail`、`NS_FireballExplosion`、`M_FireballShockwave`、`S_FireballImpact`。原始小爆炸含 Explosion、GroundDust、NE_PostProcess、Decal_Light_Flash、Debris、SparkDebris；专用副本保留 Explosion，去除其余层。打包目录加入 `/Game/Skills/Fireball`。
- 资产导入日志 `Saved/Fireball-Assets-20260914.log` 记录脚本成功执行、三个 Niagara 编译 `valid=1`，六个保存标记齐全。命令进程最终返回 1，来自启动时已有的 GameFeatureData 配置错误及 127.0.0.1:8000 端口占用；不作为实机通过结论，也未为本任务修改这些配置。
- 原始规则快照、音频 MP3／导入 WAV、生成图及提示词、来源清单均位于 `SourceAssets/Fireball20260914`。
- 必要原生构建完成：`FPSGAMEEditor Win64 Development -ModuleWithSuffix=FPSGAME,914051500`，结果 `Succeeded`，退出码 0，构建耗时 108.51 秒（不含等待共享构建锁）。日志：`Saved/Fireball-ColdSteel-Build-20260914.log`，生成 `Binaries/Win64/UnrealEditor-FPSGAME-914051500.dll`。构建中其余已有文件的弃用 API／浮点转换警告保留，未扩展修改范围。
- 没有启动 PIE／游戏、运行检查或测试，也没有进行渲染验收。用户保存并重启已打开的编辑器后，可在游戏中按 Q 凝聚、再次按 Q 发射；技能页查看效果、修炼和等级进度。实际观感与玩法交由用户测试。
