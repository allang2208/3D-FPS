# 火球飞行火焰与拖尾方向（2026-09-14）

用户反馈火球飞出后仍向上燃烧，要求飞行中的火焰完全沿轨迹后方延伸。

后续悬浮主体已改为 [慢速燃烧版本](fireball-slow-burn-20260914.md)，保留本文的世界空间拖尾与速度方向规则。下文的 AerodynamicCore 是该后续版本的作者源。

## 调整

- 当前主体改为 `NS_FireballAerodynamicCore`，由已有 `NS_FireballBurningCore` 创建专用副本。`User.Flight=0` 保留凝聚、脱手悬浮时的短距离上窜；发射时设为 1，球面火舌与余烬移到后半球，并沿局部 -X 向后延展，取消向上抬升。
- `AFPSFireballProjectile::UpdateFlightFX` 将 Actor 的 +X 对准真实速度方向，因此水平、斜向、向上和向下发射使用同一规则。外焰截面逐渐收拢到飞行轴线。
- 当前拖尾改为 `NS_FireballVelocityTrail`。移除原拖尾的环境运动、力、速度求解和生成位置模块，改为世界空间的实际移动线段生成。每帧把扫掠移动前后的位置传入 Niagara；粒子在这条线段内分布，不只挤在帧末端点。
- 拖尾粒子出生时记录速度反方向，随后按此方向以 65 cm/s 短距离后移。移除重力、浮力、风和噪声力；已生成粒子不再跟随火球／相机旋转。
- 拖尾寿命 0.10–0.14 秒；生成率为速度除以 10 cm、上限每秒 480 个，随寿命缩小淡出。保持现有火焰循环材质、碰撞遮挡、爆炸和伤害逻辑。
- Core／Trail 的 Niagara tick 排在飞行 Actor 更新之后，使用当帧位置和速度。命中时继续沿原流程关闭主体并停止拖尾生成。

这是按运动方向约束的游戏粒子表现，没有加入流体模拟。火球实体的速度、射程、伤害和脱手规则不变。

## 接入与作者源

- `Source/FPSGAME/Skills/FPSFireballComponent.cpp`：新 CoreAsset／TrailAsset 默认引用。
- `Source/FPSGAME/Skills/FPSFireballProjectile.h/.cpp`：飞行阶段参数、真实移动线段及更新时序。
- `Tools/Skills/build_fireball_flight.py`：创建并编译两个专用 Niagara；`build_fireball_assets.py` 已追加完整重建调用。
- `SourceAssets/FireballFlight20260914/authoring.json`：作者参数与来源，沿用本地已取得的 Epic Niagara Examples 素材及其许可。
- 资产制作完成，两套 Niagara 编译均为 `valid=1`，脚本执行并保存成功。日志：`Saved/Fireball-Velocity-Trail-Assets-20260914.log`。进程返回 1 来自原有 GameFeatureData 及 127.0.0.1:8000 端口占用启动错误。
- 必要原生构建已完成：`FPSGAMEEditor Win64 Development`，模块后缀 `914102900`，`Succeeded`，退出码 0；生成 `Binaries/Win64/UnrealEditor-FPSGAME-914102900.dll`。日志：`Saved/Fireball-Velocity-Trail-Build-20260914.log`。
- 批处理构建锁发生排队饥饿后，仅终止本任务尚未进入 UBT 的等待包装进程，改用引擎随附 .NET 10 直接调用 UnrealBuildTool，保留 `-WaitMutex` 串行互斥、模块后缀 `914102900` 和 `-NoHotReloadFromIDE`；没有中断其他构建。
- 首次链接遇到 `WeaponVolumeAudit.cpp.obj` 仍引用旧版双参数 `PlayMechanicalSound`，当前声明／实现已为带默认第三参数的新签名。仅移除该旧编译目标文件后重新构建，没有修改相应源码。构建工具随后因模块配置变化重建依赖并成功链接。

按用户规则，未运行游戏、测试、截图或渲染。交由用户重启 UE 后自行测试。
