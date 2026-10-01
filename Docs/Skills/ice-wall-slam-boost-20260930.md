# 冰墙更快召降、近距震屏与烟尘加强

2026-09-30 用户在上一轮冰墙召降基础上要求加快法杖前冰块消失、加快墙体下落、附近玩家适当震屏，并加强落地烟尘。

## 释放与接触

`skills.json`、`FIceWallTuning`／`FIceWallCast` 默认值及读取器统一调整：升空消失由 0.16 秒缩到 0.08 秒，下落由 0.22 秒缩到 0.12 秒。升空高度 160 cm、墙体最大下落高度 360 cm，沿用顶棚限制、预览锁定、高／矮墙与法杖限制。跨阶段传递本帧剩余时间，避免短动画因每次切阶段多等一帧而变慢。

伤害、扫掠击退、首轮寒冷去重与光环节拍沿用上一轮落地事件；生命、宽度成长、资源、修炼和存档保持原口径。

## 屏幕抖动

新增 `IceWallLandingCameraShake.h/.cpp`，独立相机位移／旋转波形，持续 0.23 秒，末段快速衰减。基础峰值平移小于 1 cm、俯仰 0.32°、侧倾 0.15°；不写角色控制旋转、FOV 或屏幕调色。`bSingleInstance` 使重叠落地复用同类抖动。

`Land` 同刻调用 `ShakeNearbyPlayers`。距离取玩家脚部到冰墙最近的地面矩形边缘，包含高度差，宽墙两端同样可感受到；1 m 内最高强度，1–6.5 m 按平方衰减，6.5 m 外为零。高墙峰值倍率 0.85、矮墙 0.60，读现有 `fps.Camera.Shake` 开关／强度。只对当前世界本地玩家相机执行，不引入网络 RPC。

抖动与 Niagara 资源加载独立；表现预算减少烟雾时，仍可产生此次落地反馈。

## 加强烟尘

新运行资产 `/Game/Skills/IceWall/SlamV2/NS_IceWallLanding`，保留旧 V1。作者 `Tools/Skills/build_ice_wall_landing.py` 已转向 V2，组件软引用与 AlwaysCook 同步。

- 继续复用翻卷烟 `M_RollingImpactSmoke` 和冰锥 `MI_ColdMist`，原材质未改。
- 灰褐烟尘基尺寸由 64×50 增为 96×64 cm，Alpha 由 0.40 增为 0.56；快速外扩距离与速度提高，寿命为 0.85–1.15 秒，出生区保持贴地两侧。
- 一级烟尘由 4 增为 8 片，数量随墙宽成长但最多 48 片。寒雾一级由 4 增为 6 片、上限 28 片，基尺寸 76×40 cm、Alpha 0.34、寿命 1.10–1.45 秒。
- 单次落地仍一个池化系统，共享风、细节预算与接触面；低细节出生位置仍跨整面墙，粒径不随技能等级放大。烟尘高度保持低矮，矮墙顶面留给架枪。

## 落盘与构建

初始复用已有编辑器桥时，编辑器已被关闭，桥未找到可用节点，未创建资产；随后在无编辑器占用时执行后台 commandlet，V2 已编译保存，退出码 0，回执 `Saved/IceWallSlamBoost20260930/asset-authoring.json`。
Game／完整 Editor 已通过同一批次后台构建，退出码 0，`Result: Succeeded`，耗时 1733.55 秒。日志 `Saved/IceWallSlamBoost20260930/build-game-editor.log`，目标列表 `Saved/IceWallSlamBoost20260930/targets.txt`；使用 `-NoHotReloadFromIDE -DisableUnity -NoUBA -MaxParallelActions=4`。产物包含 `Binaries/Win64/FPSGAME.exe`、`Binaries/Win64/UnrealEditor-FPSGAME.dll` 及完整 Editor 所需插件／目标元数据。

本轮未启动游戏、PIE、渲染、截图或额外自测，观感与实机由用户测试。
