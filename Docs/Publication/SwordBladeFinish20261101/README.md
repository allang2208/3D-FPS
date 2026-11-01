# 符文长剑材质与整段覆盖发布

本次将“剑身Ⅰ／剑身Ⅱ”显示为“剑身／符文”，增加独立“剑身材质”栏。先开放符文长剑，其他剑保留空位；内部 `blade_1`、`blade_2` 与 `gunsmith_parts` 保存键不变。材质同时覆盖剑身和归属护手的剑根承接面，观察者按复制的材质模式重建 MID，恢复原厂和仅换材质也会更新。

| 材质 | 类型 | 效果 | 代价 |
| --- | --- | --- | --- |
| 原厂材质 | 原厂 | 无 | 无 |
| 折叠纹钢 | 通用 | 物理伤害+10%；攻击体力消耗-5% | 无 |
| 玄铁 | 通用 | 格挡体力消耗-20%；韧性伤害+15% | 无 |
| 秘银 | 通用 | 近战攻击速度+10%；攻击体力消耗-10% | 物理伤害-5% |
| 大马士革钢 | 特殊 | 暴击率+10%；暴击伤害+20% | 攻击体力消耗+10% |
| 陨铁 | 特殊 | 物理伤害+15%；韧性伤害+25% | 近战攻击速度-10% |

大马士革的两个暴击增益只进入实际武器的近战命中快照，G 飞剑计算武器输入时排除材质栏。公开源码按本次功能裁剪共享文件，其余任务的代码和暂存状态保留。`FPSPlayerBodyTypes.h` 同时补入基线 `FPSBodyRuneVisual` 已经使用的四个斩马刀字段声明，不扩展其他战斗逻辑。

## 制作源与恢复

保留以下作者目录的脚本，所有引擎命令默认使用当前本机路径；在另一台机器执行前调整项目和 UE 路径。没有在本次整理中重新执行它们。

1. [通用材质配方](../../../SourceAssets/SwordBladeMaterials20261031/install_materials.py)：建立原厂、折叠纹钢、玄铁、秘银的参数与四路 PBR 输入。
2. [大马士革配方](../../../SourceAssets/DamascusBladeMaterial20261031/install_materials.py)、[陨铁配方](../../../SourceAssets/MeteoricIronBladeMaterial20261031/install_materials.py)：依次扩充模式 4、5。
3. [全段遮罩烘焙](../../../SourceAssets/SwordBladeFullSurface20261101/bake_mask.py)、[剑根接入](../../../SourceAssets/SwordBladeFullSurface20261101/install_materials.py)：原生表面映射、剑身及护手刻纹遮罩打包，再接入覆盖参数。
4. [最终数值配方](../../../SourceAssets/SwordBladeMaterialStats20261031/install_stats.py)：按上表设置数值。旧 `install_catalog.py` 是初始化配方，会重置先前栏位选项；现有工程以提交中的目录为准，不能在数值接入后再单独运行旧目录初始化。

本机已保存的运行包为 `/Game/Weapons/AzureRunesword20260913/M_AzureRunesword`、`NativeRuneGold20260922/M_AzureRunesword_NativeGold` 和 `BladeFinishes20261031/T_RuneSword_FullBladeFinishMask`。符文、湿润、发光及 Substrate 输出保留。

未核准原资产再分发，因此公开库不含这些 UE 包、贴图、图标、Meshy 模型和密集 UV 映射。恢复需要合法的原生符文剑及本机 `SourceAssets/RuneSwordVisualPolish20260922/surface_mapping.npz`、`T_RuneSword_NativeMask.png`、`T_RuneSword_GuardNativeMask.png`；图标脚本另需各配方目录里的原始设计图。本机现役素材和最终输出均保留，详细路径及 SHA-256 见 [资源依赖](local-assets.json)。这次发布不是完整 Content 备份。

## 已有证据与未覆盖范围

[定向证据摘要](validation-evidence.json)来自 2026-11-01 本机完整工作区，整理发布没有启动 UE、重新构建或重跑游戏测试。Editor 构建成功；1344 个组合／恢复原厂场景有 24480 项断言，0 失败；保存材质回读 31 项，0 失败；本机真实 UDP 的 7 个阶段全部通过，三个进程正常退出。每端配置 60 ms 延迟、3% 丢包，不是实测 RTT。

组合夹具与 UDP 夹具包含此前的金银符文、双曜星环和星陨天枢完整本机改造目录及资产。它们的其他玩法不随本次材质提交发布；公共检出只有本次材质增量，不能把历史本机结果视为公开快照从零构建或全功能运行通过。夹具库存由隔离档案设置，没有验证改造台上传事务、攻击 RPC、专用服务器、公网连接、服务器重启存档或最终渲染画面。

实现与完整场景说明见 [整段剑身材质记录](../../Weapons/sword-full-blade-finish-20261101.md)。可复用规则进入 [模块剑材质](../../../skills/ue5-weapon-workflow/references/modular-sword-materials.md)和 [装备复制](../../../skills/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)，个人 SKILL 与工程镜像同步。

## 归档

93 个旧构建／重复日志、一次性启动器、已完成测试的 UserDir 和保存前备份移入本机 `trash/SwordBladeFinish20261101`，共 1693010 字节，逐文件移动前后 SHA-256 一致。原路径、目标、原因和保留替代物见 [归档清单](archive-manifest.json)。正式制作脚本、最终材质、表面映射依赖、关键成功日志及真实网络结果保留；失败尝试不计为通过。
