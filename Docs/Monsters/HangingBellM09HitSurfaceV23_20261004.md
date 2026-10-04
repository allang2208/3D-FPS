# M09 V23：薄膜受击与头部必定暴击

用户要求：薄膜状组织也算命中；下方眼冠头部为弱点，击中必定暴击；完成后回查遗漏或 bug。

## 实际接入

- 新建并已保存 `/Game/Monsters/HangingBellM09/V23/PA_M09_HitSurface`。保留原身体碰撞，六片膜组织各增加四段骨骼随动凸包，共 24 段；从实际蒙皮顶点取形，边界包含相邻骨骼的权重过渡并增加 1 cm 余量。
- 活体运行时使用上述受击资产。薄膜按普通部位结算伤害，仍可按玩家原有概率随机暴击。
- `eye_crown` 及其子骨骼接入 `ColdSteelSkills::IsCriticalHit`。枪械、弓箭、近战和使用共同弱点入口的直击法术采用既有暴击公式与反馈；不另设固定的额外倍率，不把爆炸波及自动视作头部命中。
- 死亡前切回原 `V04/SK_M09_PhysicsAsset`，客户端状态同步也刷新对应资产。新增薄膜碰撞为运动学查询体，不加入尸体关节和布娃娃预算。
- 未重导入网格或动画。保留 V22 的六个材质槽绑定、V18 抓击、V20 的 120 度/秒转身及双倍移动速度。

## 回查处理

1. 原 `M09Physics.cpp` 明确跳过薄膜骨骼，导致这些组织没有射击碰撞；增加独立活体受击资产解决，同时保留原尸体制作逻辑。
2. 原 `TakeDamage` 对眼冠另乘 1.5 倍，且没有正式暴击回执。移除该局部倍率，由共用管线结算一次，避免接入弱点后双重叠加。
3. 联网权威命中记录包含 Actor、BoneName 和命中点，但不包含 Component。弱点入口允许缺省组件，仍拒绝非空且不属于怪物网格的组件。
4. 致死伤害后，弹道系统仍会查询命中类型用于反馈。弱点几何分类不因目标已死亡而丢失；实际伤害与击杀奖励仍由原有死亡状态门控。
5. 抓击、凝视和天花板探测已经排除自身，新增薄膜不会阻挡自己的攻击或支撑检测。相关攻击参数未修改。

## 构建、保存和专项检查

后台 Editor 和 Game 目标均构建成功。实际资产保存收据：`SourceAssets/HangingBellM09Meshy20261003/HitSurfaceV23/Records/authored.json`。

本次按用户明确要求运行 `M09HitSurfaceAudit`：隔离物理世界，不进入地图 BeginPlay、不初始化玩家存档子系统、不启动图形编辑器或游戏。覆盖薄膜收拢、展开、抓击三个姿态的简单/复杂射线与世界扫掠，实际眼冠射线与扫掠、头部在各攻击状态的弱点分类、武器和直接魔法伤害回执、死亡物理资产切换及材质槽引用。结果见同目录 `audit.json` 和 `audit.log`。

2026-10-04 16:18（北京时间）专项检查完成：363 项通过，0 项失败，commandlet 退出码 0。检查范围内未发现其他未处理问题。

这属于后台命中与结算专项检查，不代表视觉表现、实战手感或双端联网验收。实际游戏体验由用户测试。

## 维护入口

- `Source/FPSGAME/Monsters/M09HitSurface.cpp`：受击资产生成与弱点判定。
- `Source/FPSGAME/Monsters/HangingBellM09.h/.cpp`：资产加载、活体/死亡切换和移除重复倍率。
- `Source/FPSGAME/Skills/ColdSteelSkillRules.cpp`：共用弱点入口。
- `Tools/HangingBellM09/author_hit_surface_v23.py`：生成并只保存 V23 受击物理资产。
- `Tools/HangingBellM09/Build-HitSurfaceV23.ps1`：等待已有构建或 DLL 占用结束后增量构建。
- `Source/FPSGAME/Monsters/M09HitSurfaceAuditCommandlet.h/.cpp`：本次专项检查。

修改前备份位于 `SourceAssets/HangingBellM09Meshy20261003/HitSurfaceV23/Before/`。
