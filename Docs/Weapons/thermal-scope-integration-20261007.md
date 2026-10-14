# 热成像瞄准镜接入 · 2026-10-07

用户在确认此前仅保存模型后，要求继续完成游戏接入。本次沿用原始原创模型，补充运行网格、枪匠目录、瞄准与倍率、热源遮罩和共享改造图标。没有引入 ThermoForge 插件或复制第三方代码、资产。

## 玩家操作与状态

- 在枪匠「瞄具」中选择传说级红色卡片「热成像瞄准镜」，ID 为 `thermal_scope`。
- 每次新装备或新安装默认 1.5×；瞄准时滚轮依次切换 1.5×、3×、8×，到端点停止。该输入被消费，不同时切枪。
- 松开再瞄准、同一装备的档案刷新保留当前倍率；换枪或重新安装回到 1.5×。倍率是本次装备的表现状态，不单独写进存档。
- 已安装配件通过现有 `gunsmith_parts.optic` 随物品实例保存、读取、转移；没有新增平行存档格式。
- 电子矩形窗口固定为显示面 34.4:28 的宽高比，倍率仅改变主相机 FOV，分划中心继续对应相机射线。使用现有 ScopeOverlay 与 HUD 隐藏机制。
- 退出瞄准、换弹、菜单、武器重建和优先级中断撤销热成像；角色结束时释放镜头后处理与热轮廓。

## 安装与显示资产

原始五个模型、八份材质保留。新运行资产目录为 `/Game/Weapons/ThermalScope20261006/Runtime`，按 Common、HK416、M16、M1911、G18、DW715、PitViper 七种接口保存镜体组合和独立旋钮，共 14 份网格。

当前枪匠目录共 16 款：M4A1、AKM、QBZ-191、M1911、Pit Viper 2011、G18、Dan-Wesson 715、RSH-12、ASH-12、M16A2、A762、SVD、PKM、201、HK416、M4 Super90；全部通过公共 `optic` 选项接入。

镜体组合包含原镜身、原夹轨座、原显示面及必要的枪型转接件；旋钮只显示一份，并通过 `ZoomPivot` 挂点旋转。Common 供已有标准导轨或独立桥架的步枪、机枪、SVD、RSH-12、Super90 使用；RSH-12 与 Super90 采用其已测量导轨的中性安装偏移。M16 保留提把鞍座；三种手枪与 Dan Wesson 保留实际枪面接触结构；HK416 按其既有组件坐标系变换。201 保持固定后机匣挂接，PKM 保持机匣盖挂接，自动手枪继续跟随套筒。

运行入口为 `ThermalScopeVisual.cpp`，复用主手、双持配件复制、地面物品与枪匠预览的既有装配路径。`ColdSteelIconResources.cpp` 加入同一资源列表。

改造图标从原始模型渲染形状参照，再使用 imagegen 配合已认可金属框制作一张共享母图；运行 PNG 为 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/optic_thermal_scope.png`。不逐枪复制图标。

## 热目标与成本

- 怪物由 `MonsterCombatComponent::BeginPlay` 注册，骨骼副本使用 Leader Pose 同步动作，只写 CustomDepth，Stencil=240；不修改本体的隐身透明材质。因此 M27 隐身身体仍有热轮廓。
- 火把、火球及其短时爆燃、陨星火焰及落地燃烧区域、焰甲光环从实际效果生产点注册，Stencil=241。半透明火焰使用受噪声遮罩修饰的热体积表示。普通发光物体和灯光不自动标成热源。
- 后处理将环境压为冷暗灰，怪物为白热主体及黄橙边，火源为白黄核心及橙边。分划由独立 Slate 层绘制。
- 遮罩每像素比较目标深度和场景深度，实体墙保留遮挡；火焰体积额外从观察者到真实来源做遮挡射线，避免体积越过墙面造成漏光。
- 只在本地热成像 ADS 开启时生成代理；退出即释放。注册表每 0.2 秒处理一次，250 米范围内优先近处，最多 96 个怪物和 32 个火源。没有逐帧全世界 Actor 扫描，也没有新增 SceneCapture。
- 火球爆燃热源最多维持 0.85 秒，后续冷烟不会持续标成高热火球；持续火源随其实际组件激活、可见和销毁状态变化。

## 制作与交付记录

- 作者源与安装来源：`SourceAssets/ThermalScopeRuntime20261007/authoring.json`，对应 14 份 FBX、Blender 源文件。
- 制作与导入：`Tools/Weapons/ThermalScope20261006/author_runtime.py`、`render_icon.py`、`import_runtime.py`、`thermal_scene.hlsl`。
- 实际保存结果：`SourceAssets/ThermalScopeRuntime20261007/install-receipt.json`。以其中 `complete` 与逐项 `saved` 为落盘依据。
- Editor 构建：`Saved/BuildEditor/build-20261007-215407.log`，成功。
- Game 构建：`SourceAssets/ThermalScopeRuntime20261007/build-game.log`，成功；构建系统报告目标已是最新。
- 后台导入日志：`SourceAssets/WeaponSurface20260930/logs/import_runtime.20261007-220151-183.log`，正常结束，实际保存 14 份网格、3 份热成像材质、1 份图标纹理，共 18 个资产，回执 `complete=true`。

本次没有启动 UE 图形编辑器或游戏，没有运行 PIE、自测、回归、验收截图。图标渲染属于正式图标制作，不是游戏效果验收。运行视觉、逐枪实际贴合和操作体验由用户测试；构建和保存成功不等同于游戏内已验收。

## 镜内效果未应用修复 · 2026-10-07

用户反馈镜内没有热成像效果。已有游戏日志记录 201 安装 `thermal_scope`，但旧实现没有记录相机后处理是否启用，不能从模型出现推断热成像已经运行。

`ScopeOpticalPresentation.cpp::UpdateThermalPresentation` 原来以 `IsGameThreadShaderMapComplete()` 作为添加相机后处理和启用热目标的共同前提。UE 5.8 的 `MaterialShared.cpp::SetGameThreadShaderMap` 将完整变体集合与可渲染资源分别处理；`PostProcessMaterial.cpp::GetMaterialShaders` 在实际绘制时通过 `TryGetShaders` 请求所需变体。先等待全部变体再注册后处理，可能让这一请求始终无法发生。

现改为使用实际材质资源的 shader map 和 `IsValidForRendering()`，交由后处理渲染器请求当前 pass。异步加载失败会记录材质路径；相机后处理的启用、停用各记录一条 `ThermalScope` 日志。没有改动开镜条件、倍率、颜色方案或热目标规则。

后台落盘记录：

- Editor 构建成功：`Saved/BuildEditor/build-20261007-223251.log`。
- Game 构建成功，目标已是最新：`SourceAssets/ThermalScopeRuntime20261007/build-game-effect-fix.log`。
- `compile_runtime_materials.py` 通过带 RHI 的无界面 commandlet 编译并保存 `M_ThermalScene`、`M_ThermalBody`、`M_ThermalFire`；材质编译日志没有报告编译错误。此次仅提交这三份材质的后台编译，不把完整变体等待重新放进游戏运行条件。
- 材质编译日志：`SourceAssets/WeaponSurface20260930/logs/compile_runtime_materials.20261007-223826-025.log`；逐项保存回执：`SourceAssets/ThermalScopeRuntime20261007/EffectFix/material-build.json`；修改前资产保存在同目录 `BeforeMaterials-*` 中。

本次没有启动 UE 图形编辑器或游戏，没有进行 PIE、截图或运行验收。以上修复和编译记录不代替游戏内效果确认，仍由用户测试。

## 身体碎点与轮廓清晰度优化 · 2026-10-07

用户确认热成像已经出现，但怪物身体内部有大量亮暗碎点、持续闪动，随后授权继续实施优化。现有配置与游戏日志均使用 `r.CustomDepthTemporalAAJitter=0`；旧着色器却在同一个 UV 上直接比较未抖动的 CustomDepth 与抖动的 SceneDepth，再用 1 cm 的硬阈值切断热色。邻域描边还把这些遮挡断点当成轮廓，强化了颗粒感。

本轮改动集中于 `Tools/Weapons/ThermalScope20261006/thermal_scene.hlsl`：

- 使用实际深度缓冲区的像素中心、视口偏移与分辨率，并依据本帧投影抖动对齐场景深度采样。目标表面的局部逆深度平面用于计算同一条观察射线上的目标深度，避免只移动 UV 后仍因最近点采样造成身体自遮挡。
- 选择邻域中更连续的一侧估算平面，避开四肢与躯干、相邻目标之间的深度跳变。遮挡容差随局部斜率变化，限定在 1.25–3 cm；改用连续过渡。四个场景采样分别判断遮挡后再合成覆盖率，不把墙面和后方物体的深度直接插值。
- 先识别 Stencil=240/241，再对热覆盖率做四点插值。Stencil 编号保持离散，不对编号进行线性过滤，也不对整张场景做模糊。
- 暖色细边只依据热类别边界生成，不再围绕遮挡孔洞绘制。身体保留白热主体，并从目标自身深度重建温和的体积明暗；隐身怪物不会借用身后墙体或环境的光照。移除逐像素扫描线。
- 沿用单相机、原有后处理位置、倍率、热代理和墙体遮挡流程。没有增加 SceneCapture、历史帧缓冲、全局抗锯齿修改或 C++ 类型改动。本轮不提前实施 TSR 前移方案。

更新入口 `update_thermal_presentation.py` 只替换现有 `M_ThermalScene` 的 Custom 节点源码，完成材质编译后保存这一份资产。原导入脚本仍读取同一份 `thermal_scene.hlsl`，后续重导不会恢复旧算法。源码与资产备份、实际保存回执集中在 `SourceAssets/ThermalScopeRuntime20261007/Clarity/`。

接入时 UE 图形编辑器已关闭，现有桥自动选择带 RHI 的无界面 commandlet，正常退出并实际保存 `M_ThermalScene.uasset`。材质编译日志没有报告编译错误；未修改原生源码，不需要 Editor/Game 原生重编译。本批日志：`SourceAssets/WeaponSurface20260930/logs/update_thermal_presentation.20261007-230245-179.log`；保存回执：`SourceAssets/ThermalScopeRuntime20261007/Clarity/material-save-20261007-230533.json`。

运行效果与开销尚未实测；此次不启动游戏、PIE 或验收截图，由用户确认移动中身体连续性、四肢边缘及墙后遮挡。
