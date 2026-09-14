# 火球表面燃烧（2026-09-14）

用户要求确认本地库中的火焰燃烧效果，并给现有火球增加燃烧表现。

后续已按用户反馈调整飞行方向：发射后取消向上抬升，外焰与拖尾沿速度后方延展；新的当前资产及规则见 [飞行拖尾方向](fireball-velocity-trail-20260914.md)。以下为悬浮燃烧基础版本的制作记录。

## 选用资产

本次读取了当前工程的 Epic Niagara Examples `FX_Misc/NS_Fire`，其中有 `FlamesAndEmbers`、`Smoke`、`Lights`、`BaseLight` 和 `FlamesOnly`。选用 `FlamesOnly` 的 CPU 发射器及 `Materials/MI_Flames` 的噪声火舌材质／动态材质动画。工程中也已有 Realistic Starter VFX Vol 2 的 `P_Fire_Small`、`P_Fire_Big`；本次沿用当前 Niagara 管线，没有引入这套 Cascade 粒子。

原 `NS_Fire` 是环境燃烧：依赖静态网格采样，包含环境风力、烟及多盏灯。专用副本移除这些环境模块，围绕火球生成短命火舌与少量余烬。许可与库获取记录沿用 [原资产选择记录](fireball-asset-selection-20260914.md)；第三方素材与纹理不公开再分发。

## 当前接入

- 运行时火核改为 `/Game/Skills/Fireball/NS_FireballBurningCore`，从当前 `NS_FireballCore` 复制，保留已有循环球核。
- 新材质 `/Game/Skills/Fireball/MI_FireballSurfaceFlames`：使用原 `MI_Flames`，降低高亮增益和扭曲幅度，调整软交界。
- `FireballSurfaceFlames`：每秒 32 个，寿命 0.32–0.48 秒；由半径 11.5 cm 附近沿球面翻动并短距离上窜，渐入渐出。
- `FireballSurfaceEmbers`：每秒 7 个，寿命 0.38–0.56 秒；细小、短距离散出，避免形成持续遮挡的烟幕。
- 新发射器均为局部空间，共用现有 Core 组件的凝聚缩放、近镜隐藏与爆炸停播；不会留在收回的手上。脱手悬浮位置、发射流程、命中伤害及原拖尾／爆炸资产不变。
- 仅更新 `FPSFireballComponent.cpp` 的默认 CoreAsset 引用；蓝图中若人工指定了其他 CoreAsset，仍保留其显式覆盖。

原火核被正在运行的编辑器占用，第一次保存失败（Windows 32）。随后将结果另存为新的 `NS_FireballBurningCore`，完成保存及引用接入，没有关闭用户编辑器或替换原包资产。

## 作者源与构建

- `Tools/Skills/build_fireball_flames.py`：创建专用材质、两层球面发射器及运行资产。基础生成器 `build_fireball_assets.py` 已追加调用，重建完整火球时会同时生成燃烧版本。
- `SourceAssets/FireballBurn20260914/read_sources.py` / `source-inputs.json`：制作所用的源发射器、模块和材质参数读取记录。
- `SourceAssets/FireballBurn20260914/authoring.json`：来源、输出路径与初始数值。
- 资产制作日志 `Saved/Fireball-Surface-Flames-20260914.log`：脚本执行成功、Niagara 编译 `valid=1`，资产保存完成。命令进程返回 1 来自工程启动时已有的 GameFeatureData 配置错误，不代表实机测试结果。
- 原生接入构建完成：`FPSGAMEEditor Win64 Development -ModuleWithSuffix=FPSGAME,914101800 -WaitMutex -NoHotReloadFromIDE`，`Succeeded`，退出码 0，生成 `UnrealEditor-FPSGAME-914101800.dll`。日志：`Saved/Fireball-Surface-Flames-Build-20260914.log`。
- 必要构建遇到当前命中特效模块的 C2487／C3535：仅将 `FPSImpactFXSubsystem.h` 中并列 `static constexpr` 声明拆开，并为 Decals／Voices 的 `TObjectPtr` 取值补 `.Get()`，保留该模块的玩法与数值。

未运行游戏、测试、截图或渲染。火焰密度、亮度和近景观感由用户在重启 UE 后自行测试。
