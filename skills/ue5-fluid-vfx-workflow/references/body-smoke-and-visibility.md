# 身体浓烟、世界烟迹与可见性

用于从移动角色身上持续产生烟雾、离体后独立扩散，以及排查“范围或目盲存在，烟却看不到”。案例为百目炉渣 V19–V21，2026-10-02。V21 资产保存和 Editor 玩法模块构建已完成，用户尚未反馈修复后的实际画面；本页记录方法和已读配置，不将其写成已验收效果。

## 出生跟随，离体独立

- 身体骨骼／socket 只驱动新的出生位置。世界空间发射器在 Particle Spawn 保存出生位置和初始漂移，在 Particle Update 使用这份快照与粒子年龄；持续读取移动身体坐标会把旧烟也拖着走。
- 多个出生位置可用稳定粒子种子选择。FPSGAME `SetVariablePosition` 对应 Niagara Position 类型，漂移用 Vector3f；不要把位置与方向互换。位置、半径、寿命和发射率在激活前设置。
- 保存出生属性与更新属性需要两个独立的 Set Parameters 模块。项目 `assignments()` 按 metadata 缓存模块名称；连续调用时须给出生捕获模块独立标记，避免第二次调用覆盖第一个模块。V21 保留 `Slag.BodyCaptureModule`。
- 死亡／停止发射将速率设为零，保留已有粒子模拟至结束。过早 `DeactivateImmediate` 会清掉整个烟迹；多团烟的生命周期与角色所有权分别管理。

## 范围扩大后的显示链

玩法区域仍生效只能证明区域判断在运行，不能证明 Niagara 已激活或实际有粒子。按实际引用、激活与参数、发射栈、Renderer 绑定、坐标与边界、材质密度／Alpha 查对应层；不要仅凭区域触发断言唯一根因。

UE 5.8 案例读取资产后发现：作者写 `bInterpolatedSpawning=false` 没有改变真正的 `InterpolatedSpawnMode`。本例改用 `RunUpdateScript`，出生运行更新但不插值出生参数；`NoInterpolation` 和 `Interpolation` 有不同用途，不能把本例设置推广到所有系统。参与开方的归一年龄限制到 0–1，避免出生阶段无效数值。

`UNiagaraComponent::SetSystemFixedBounds` 接收组件局部空间。世界烟迹的包围盒要按 Niagara 组件的实际 Transform 转换；只有组件与 Actor 变换一致时才可直接用 Actor 的逆变换。边界包含残留烟迹、长大后的 Sprite 尺寸和上浮范围。引擎的运行系统边界可以覆盖发射器模板固定边界，不能看到模板 ±100 cm 就认定它一定导致消失。本例 CPU 发射器改为 Dynamic，运行侧仍提供有界烟迹范围。

## 粒子寿命与浓度不是同一条曲线

- 短暂爆燃图集通常自身已经逐帧消散。延长粒子寿命不会让图集密度保持；再乘年龄侵蚀与 Alpha，会在要求保留期间提前变淡。
- 持续浓烟可复用同一 Mantaflow 密度图集的较浓区段，保留翻卷，用独立粒子包络控制出生与最终消散。本例复制成怪物专属材质，没有全局改动共享余烟材质。
- 保留软边、图集格内采样边界、真正密度通道和深度交界淡化。黑色烟雾通过透明覆盖遮挡背景；加发光或加粒子不能替代密度和边界修复。
- 本例参数为线性范围 ×1.5、8 秒保持后 1.5 秒消散、每秒 8 粒、总寿命 9.5 秒约 76 粒；这些是案例调参，不是通用预算。粒子 Alpha 0.65，图集浓区段约 0.035–0.485，效果仍待用户体验。

## 证据与入口

NullRHI 或没有 Niagara 世界调度／渲染准备的 commandlet 世界里，组件不激活、SimCache 为空，不能证明真实 PIE 发射失败。无界面可以制作、编译和保存资产；参数读回、资产保存、粒子数据和实际画面分别记录。默认不追加游戏、截图或性能测试。

工程入口（相对 `D:/FPS3D/FPSGAME`）：

- `Source/FPSGAME/Monsters/SlagBlackMist.*`：出生坐标、范围、世界烟迹与浓烟核心；`SlagMistViewComponent.*`：雾内糊屏与状态控制。
- `SourceAssets/HundredEyedSlagMeshy20260930/SmokeVisibilityFixV21/author_visible_body_smoke.py`、`PersistentBodySmoke.hlsl`：当前烟雾作者与密度。
- `WorldSmokeV19/author_world_smoke.py` 的 `blind_material()`、`blind_view.hlsl`：当前目盲材质重建；它仍需要 V17 的密度噪声，不按旧版本号归档。
- `Docs/Monsters/hundred-eyed-slag-smoke-visibility-v21-20261002.md`：配置发现、保存与构建范围。

当前资源路径以运行源码为准；UE 包、图集、源模型与导入回执留在本机，公开源码恢复边界另见本次发布文档。
