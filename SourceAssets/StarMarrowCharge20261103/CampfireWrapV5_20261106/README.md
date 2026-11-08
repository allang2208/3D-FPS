# 星髓长锋：篝火蓝焰与贴剑环绕 V5

2026-11-06。用户在火甲火舌版本之后要求改用当前篝火火焰，保留蓝色、增强随机与环绕、提高帧数并贴合武器。本版替代 V4 随机火舌，继续保留密集贴刃火床。

## 实现

- 供体由 `ColdSteelCampfire.cpp` 当前引用的 `/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire` 的 `Fire` 渲染器取得。只复制实际绑定材质，不改篝火资产。
- 新材质 `/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103/CampfireWrapV5/M_StarMarrowCampfireBlue` 保留篝火原纹理、发光、透明度幂函数及单次曝光补偿；最终发光沿用剑火蓝色映射。
- 原篝火使用普通 TextureSample，单开 Niagara 帧混合不能插值纹理。副本将该采样替换为带混合的 SubUV 采样，原 RGB/Alpha 下游连接保持；8×8 图集按每粒子 48–60 帧/秒播放，起始帧不同、末帧钳制、不随机跳帧。
- `WeaponFireballTongues` 改为单层局部环绕火舌，移除重叠的 `WeaponFireballCurls`。每粒子的轴向位置、起始角度、正反向速度、大小、透明度和播放速度只在出生时随机并保存；后续按连续年龄更新。
- 根部沿剑身扁平椭圆截面环绕，沿用原贴刃层的宽度与尖端收窄轮廓，厚度取实际星髓剑身网格 Bounds。随现有 `User.WeaponEnd`、`User.BladeSide` 逐帧更新，火根不积分世界速度；挥剑速度只影响火舌倾斜。接触淡化从篝火的 4 cm 适配为剑面的 0.45 cm，保留深度遮挡。
- `WeaponFireballCore` 的 24 组贴刃火焰、`MotionFireballFlame` 挥动残焰、`WeaponEmbers` 余烬保持；伤害、充能、动画、HUD、音效和运行时 C++ 不变。

## 开销与帧序列

- 发射器从 5 层减为 4 层。
- 随机火舌基础生成率从 44+16=60 个/秒减为 30 个/秒，寿命 0.55–0.85 秒，理论峰值约 27 个随机火舌；距离 Detail 继续降低远端生成率。
- 含保留的挥动残焰及余烬，总标称峰值从 78 减为 48 个/秒。24 组持续贴刃粒子不计入此每秒生成率。
- 出生随机值缓存，取消火舌每次更新的随机哈希重复计算；无新增灯光、碰撞、组件或全局 Tick。帧间混合增加相邻帧纹理采样，减少发射器与粒子是开销设计，不能等同于已测得 FPS 提升。

## 保存与恢复

执行 `SourceAssets/StarMarrowCharge20261103/run_asset_task.ps1 -Script 'CampfireWrapV5_20261106/install_campfire_wrap.py'`，由现有互斥桥或无界面 commandlet 完成材质、Niagara 编译和指定包保存。

活动系统路径仍为 `NS_StarMarrowDenseBladeFire`，无需 C++ 构建或修改预载路径。`DenseFlowV3/install_dense_flow.py` 和根目录重建链已改为应用 V5；V4 目录仅保留历史来源，不作为当前重建入口。

修改前系统包保留在 `Before/NS_StarMarrowDenseBladeFire.uasset`。实际资产保存以本目录 `install-receipt.json` 及父目录 `install_campfire_wrap-process.json` 为准。

未运行游戏、测试、截图或性能采集；观感、贴合和实际 FPS 由用户自行确认。
