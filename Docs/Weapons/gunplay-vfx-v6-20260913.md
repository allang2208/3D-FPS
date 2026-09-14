# Gunplay V6：曳光、枪口烟雾与步枪抛壳

烟火后续调整见 [V7：增强烟火与镜内动态火光](gunplay-vfx-v7-20260914.md)。本文保留 V6 的制作记录，曳光与抛壳继续沿用。

用户在 2026-09-13 继续确认“一起接入曳光和烟雾升级”。本轮已完成源码接入、Editor 原生构建及五项特效资产生成。没有启动游戏、运行测试、截图或渲染预览，效果由用户自行测试。

## 已接入的表现

- **曳光**：当前飞行段最长 75 cm、宽 0.30 cm。新材质呈现暖黄外缘、暖白亮芯、逐渐消失的尾部和柔和的尖端；启用 Responsive AA，保持深度遮挡和近表面淡出。每帧回收旧段，在实际命中点截断。继续使用现有 64 槽特效池和弹道数据，没有新增第二套弹道或改动伤害、速度、穿透及后坐力。
- **每发喷烟**：沿用已接受 V5 的烟量、颜色、0.50–0.80 秒寿命以及枪口 flipbook；提高初始前冲速度，缩小喷出锥角，再通过阻力减速。烟出生后保持世界空间，短促火光继续跟随枪口。
- **停火细烟**：换用库内 Epic wispy 材质与配套贴图，寿命 0.75–1.05 秒，朝世界上方并略带侧向漂移。热烟周期由 0.11 秒改为 0.16 秒，继续按热量和停火时间触发，减少同一位置反复堆烟团。
- **消音器**：新增独立烟雾尺寸参数，保留较小闪光的同时保持烟雾可见。组件在激活 Niagara 之前设置 `User.SmokeScale`；粒子尺寸和速度的实际绑定同时修改，避免仅设置未使用的参数。
- **步枪抛壳**：复用 Epic 弹壳模型与材质，尺寸、枢轴和初始方向适配枪身；从 `WPN_SOCKET_Eject` 出生，以枪身坐标向右、向上、向后抛出，一次性继承角色移动速度，加入随机翻滚和世界重力，沿用现有碰撞反弹及回收。
- **LPVO 1–6x**：开镜时停止生成弹壳并回收此前在飞的弹壳，退镜渐隐阶段保持隐藏。火光、烟雾和曳光保留；腰射恢复抛壳。不能用“倍率大于 1”替代这一规则，LPVO 的 1x 同样适用。

本轮采用第一阶段方案：现有特效池加新材质/烟雾资产。未引入 ECSProjectiles 或 Ricochet 插件，未把库内 `NS_BulletTracer` 直接替换进弹道流程。GitHub 参考与进一步批量 Niagara 渲染建议见[初始方案](gunplay-vfx-casing-20260913.md)。

## 新资产和可编辑源

五项生成资产位于 `/Game/Weapons/GunplayFX/`：

| 资产 | 作用 |
| --- | --- |
| `M_BallisticTracerSoftV2` | 项目自制柔边曳光材质 |
| `NS_FPS_MuzzleEpicV6` | 枪口火光及每发喷烟 |
| `NS_FPS_BarrelSmokeEpicV6` | 停火后的细烟 |
| `MI_MuzzleSmokeV6` | 每发烟雾材质副本 |
| `MI_BarrelWispyV6` | 停火细烟材质副本 |

步枪弹壳直接引用本机已有 `NiagaraExamples/FX_Weapons/MuzzleFlashes/Meshes/SM_BulletShell` 和 `MI_BulletShell_FX`。

原始 Epic 包与 V5 资产保留。烟雾素材沿用项目已记录的 Epic 授权，仅本机使用和恢复，不公开分发第三方原始或派生 uasset。曳光 HLSL 为本次项目编写，未复制 GitHub 代码。

- 原生入口：`Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp`。
- 生成器：`Tools/AssetPipeline/build_gunplay_presentation_v6.py`。
- 曳光源：`SourceAssets/GunplayVFX20260913/TracerSoft.hlsl`。
- 重建依赖：本机 Epic NiagaraExamples、现有 V5 两套系统、UE 5.8 NiagaraToolset 和项目 `RainAssetEditor`。

## 构建与交付记录

普通 Editor 原生构建通过：`Saved/BuildEditor/build-20260913-234322.log`，`Result: Succeeded`，生成普通 `UnrealEditor-FPSGAME.dll`。本轮没有关闭用户编辑器；构建开始时编辑器已由外部操作退出。其他任务在此期间补齐了先前缺失的源码声明，本轮没有修改 UI、地形、生产或脚步插件源码。

资产生成记录：`Saved/Logs/GunplayV6-Assets-20260913-d.log`。生成器记录五项 `GUNPLAY_V6_SAVED`、`GUNPLAY_V6_ASSETS_CREATED`，Python 脚本执行成功；两套 Niagara 资产编译完成。生成清单为 `Saved/GunplayVFX20260913/created-assets.json`。

该 commandlet 整体退出码仍为 1，末尾报告项目已有的 GameFeatureData 资产管理配置错误。首次生成时，类默认对象还报告了新资源尚未生成的警告；随后脚本已创建并保存这些资源。Python 对用户参数默认值文本的导入警告也记录在该轮日志中，生成器现已移除无效的默认值文本；游戏组件会在激活前明确传入烟雾尺寸。没有为了清空这些日志而修改其他系统，也没有再启动一个只用于验收的进程。

本记录不代表视觉效果、贴合度、抗锯齿效果或帧率已经实测。用户下次打开工程时会加载新模块和新资产；如有编辑器在资源生成前已被其他任务重新打开，需要重新打开工程以刷新当时缓存的默认对象。
