# 龙息体积喷流 V8 制作记录

2026-10-14。V7 的火球／篝火派生粒子效果再次被用户否定。本轮按用户指定的 RedefineFX Niagara Fluids 课程路线重做龙息；认可的原始火球和篝火不修改。

参考来源：

- https://redefinefx.com/blast/ 第 6 课 Flamethrower。
- https://www.youtube.com/watch?v=qHjbt3VCNig 作者公开单课，11 分 23 秒。已读取公开介绍和章节：粒子源、流体、火焰、质量、碰撞、颜色、速度比例。当前工具未取得可读字幕或完整视频画面，不声称逐帧复刻课程参数。
- https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-fluids-reference-in-unreal-engine 引擎气体网格、粒子注入、运动补偿及温度／密度渲染。
- 用户真实喷火器参考 BV1tT411x7oP：连续密实的根部、向前输送、末端翻卷，烟位于外围与后段。

制作目标：以三维网格保存温度、密度与速度，体积渲染作为可见火焰主体。源粒子仅向流体注入数据，不绘制火焰卡片。采用一份有界、可移动的局部流体域，随技能射程设置尺寸；中心热流集中、外围逐步展开。白黄高温核心、橙红外焰和少量暗烟分开控制。

保持玩法：法杖限定，90 度前方扇形，0.5 秒伤害节拍，等级射程 5–15 米，以及原有遮挡、资源和修炼结算。视觉模拟不作为命中或伤害的权威。停止施法即停止注入，短暂余焰只负责显示。

执行范围：后台资产制作、必要源码修改／构建和实际资产保存。没有启动游戏、模拟验收、截图或性能采样；最终观感和运行表现由用户试玩确认。资产与构建是否完成以 delivery.json 及构建日志为准。

授权边界：使用随引擎安装的 Epic Niagara Fluids 模板及本项目自制参数，不领取或分发课程工程，不更改厂商母版。Epic 模板沿 UE 授权，并非宣称为 CC0 或 MIT。

## 本轮产物与状态

- `Content/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume.uasset` 已在 2026-10-14 13:20 保存。制作 commandlet 使用 DX12 / SM6，完整 Niagara 编译 `valid=1`，退出码 0；日志 `Saved/DragonBreathVolumeV8_20261014/author3-sm6.log`。日志的两项旧 Paragon 地图资产注册警告不属于本次改动。
- `Source/FPSGAME/Skills/FPSDragonBreath.cpp` 已改为新资产引用，传入网格尺寸／质量／单元尺寸，设置移动域中心和方向，视觉尾焰延长至 0.65 秒。伤害、耗蓝、技能成长、修炼和复制状态结构未改。
- `FPSGAME Win64 Development` 必要构建已完成，日志 `Saved/DragonBreathVolumeV8_20261014/game-build2.log`。首次全项目构建遇到其他模块当时的 `Catalog` 未定义错误；再次构建时该位置已由既有工作更新为 `Definitions`，本任务没有改动该文件。
- 用户保存并关闭编辑器后，`FPSGAMEEditor Win64 Development` 正式构建已完成：`Target is up to date`、`Result: Succeeded`，日志 `Saved/DragonBreathVolumeV8_20261014/editor-build-final.log`。新版资产、源码和 Editor 模块已落盘，最终回执为 `delivery.json`；未自动启动编辑器。
- 无游戏、PIE、截图、渲染验收或性能测试。实际火焰观感、移动时表现与 GPU 开销由用户试玩确认。

重建：在 `AuthorHost/DragonBreathAuthor.uproject` 下运行 `Tools/Skills/build_dragon_breath.py`，使用 `-run=pythonscript -d3d12 -sm6 -RenderOffscreen -AllowCommandletRendering -unattended -multiprocess`。修改已加载的 V8 资产时须按项目规则沿当前编辑器接入或先由用户关闭编辑器，不同时写同一个包。

本次恢复副本：`trash/DragonBreathVolumeV8_20261014/FPSDragonBreath.cpp` 与 `build_dragon_breath.py`；旧版 V7 运行资产和材质仍在原路径。

后续：用户反馈喷射方向与不可见问题后，2026-10-14 14:44 已在相同运行路径保存 V8 R1。详见相邻 `VolumeV8R1_20261014/repair-notes.md` 和 `delivery.json`；本文件保留 V8 首次交付事实，不能将它的初始参数作为当前参数。
