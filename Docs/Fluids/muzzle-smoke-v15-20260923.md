# 枪口烟雾 V15：逐发喷烟、连射扩散与热烟

日期：2026-09-23。用户反馈 V14 枪口烟雾仍不够理想，本轮检索 GitHub 与 COD 官方公开资料后，调整现有 Niagara 实现。

## 检索与参考边界

- [TomLooman/SimpleFPSTemplate](https://github.com/tomlooman/SimpleFPSTemplate)：UE C++ FPS 基础模板，可参考枪械组织方式，但没有找到可直接接入的完整高质量枪口烟雾模块；项目采用 Unreal Engine EULA，并非可以不看授权直接复制的通用 MIT 资产包。
- [id-Software/DOOM-3 的 Weapon.cpp](https://github.com/id-Software/DOOM-3/blob/master/neo/game/Weapon.cpp)：包含 `smoke_muzzle`、`continuousSmoke` 与烟雾开始时间等枪械烟雾生命周期处理；是旧引擎实现，且[代码采用 GPL](https://github.com/id-Software/DOOM-3/blob/master/README.txt)，本轮只作为结构参考，没有复制代码或素材。
- [COD 官方 MW4 多人玩法介绍](https://www.callofduty.com/blog/2026/08/call-of-duty-modern-warfare-4-next-highlights-multiplayer-gameplay-systems) 的 VFX Masking：强调保留枪口特效强度，同时保护瞄准点周围的视野，并针对光学瞄具调整遮挡。本轮参考这项公开设计，未获取 COD 内部实现，未提取游戏素材，也未进行视频逐帧匹配。

本轮搜索未找到适合直接替换当前 UE 5.8 项目的成熟开源枪口烟雾套件；这不等于 GitHub 上不存在其他可用项目。采用项目自制 Mantaflow 密度图集、现有 Epic 来源 Niagara 模板与新写的表现逻辑。

## 修改

旧系统主要依赖连续发射。速度先取 `User.SmokeForwardSpeed`，随后与 `User.SmokeScale` 相乘，导致原本 95 cm/s 的设置在 0.28 尺寸下变成约 26.6 cm/s；提高透明度不能解决运动过缓的问题。

V15 将速度与尺寸分开，并用两个 Niagara 系统形成三个阶段：

| 阶段 | 制作参数 | 目的 |
| --- | --- | --- |
| 每发喷烟 | 每发 3 张烟片；步枪 280 cm/s、手枪 210 cm/s、消音状态 180 cm/s；寿命 0.30–0.46 秒 | 枪口在开火瞬间产生短促、前冲、逐渐扩张的烟团 |
| 连射扩散 | 26–36 粒子/秒；65 cm/s；寿命 0.50–0.75 秒 | 在世界空间留下能看见的烟雾层，转枪时不会随镜头转动 |
| 停火热烟 | 按热量从 4–11 粒子/秒逐渐衰减；6 cm/s；寿命 0.90–1.30 秒 | 单发余烟较短，连续开火后余烟更持久、更缓慢上升 |

- 停火后热烟发射窗口按热量取 0.30–1.60 秒，窗口结束后让已有烟片自然散尽。
- 喷烟烟片沿速度方向拉长；扩散烟保持面向相机的非定向烟片。
- 密度图集以相邻帧插值采样，抬升较薄的密度细节；持续层使用浅灰色，而不是接近纯白。
- 改为轻微世界空间漂移，不再固定向相机右侧偏移。
- 新增 `User.SightProtection` 动态材质参数；腰射、机瞄/普通 ADS、光学瞄具分别使用 0.28、0.68、0.82 的局部保护权重。只在小范围准星区域降低透明度，外围仍保留烟雾。
- 喷烟与枪口火焰共用现有最多 24 个 Niagara 组件池；停火、换枪和 EndPlay 沿用该池清理逻辑。连续烟维持一个持久组件。
- 没有新增实时体积求解器或动态灯光；性能数据未测量。
- 枪口位置、射线、伤害、后坐力、枪口火焰和弹壳逻辑保持原接口。

## 源码与资产

- `Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp/.h`：逐发喷烟、热量窗口、连续烟参数与资产引用。
- `Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h`：两套 V15 系统的预加载引用。
- `Tools/Fluids/author_muzzle_smoke_v15.py`：创建并保存材质、逐发系统和连续系统。
- `SourceAssets/MuzzleSmokeV1520260923/SmokeDensity.hlsl` 与 `SmokeSightline.hlsl`：图集采样与瞄准点保护。
- `/Game/Weapons/GunplayFX/M_MuzzleSmokeLayeredV15`
- `/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeShotV15`
- `/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV15`
- 共享 `/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14`，保留旧版资产。

用户自行体验时可用 `fps.Smoke.Intensity 1.2` 将两层系统烟雾透明度一起提高 20%；默认值为 `1`，范围限制为 `0–2`。该设置不改变粒子数量。

## 交付范围

资产保存清单见 `SourceAssets/MuzzleSmokeV1520260923/assets.json`，完整落盘和构建记录见同目录 `delivery.json`。本轮只做必要资产制作、保存和构建，不主动启动编辑器界面或游戏，不进行实机、视觉或性能验收。观感由用户测试。

资产制作 commandlet 返回 0，三个新资产已保存。常规 `FPSGAMEEditor Win64 Development` 构建成功，`UnrealEditor-FPSGAME.dll` 已链接落盘；最终日志为 `Saved/BuildEditor/build-20260923-223734.log`。未启动游戏，不能将构建成功等同于观感验收。

为完成原生构建，本轮另做以下最小编译修正，未调整相关玩法数值：

- `ColdSteelProfileRuntime.cpp`：两处击杀回血/回蓝调用用 `CurrentPawn.Get()` 传递 Actor，弱指针条件改为 `IsValid()`。
- `CombatStatusFormula.cpp`：删除对头文件中已不存在的 `RenewalStacks`、`RenewalTime` 的残留清零语句。
- `FPSCombatHealthComponent.cpp`：将不存在的 `FColor::Gold` 换为明确的金色 `FColor(255, 215, 0)`。
- `PKMOutgoingBeltDynamics.cpp`：将弹链节距常量 `Pitch` 改名为 `OutgoingLinkPitch`，避免 Unity 编译时与引擎头文件参数同名；数值保持不变。

早先失败的构建日志保留在 `build-20260923-222455.log`、`build-20260923-223444.log`；其余共享接口更新不计入本轮烟雾功能修改。
