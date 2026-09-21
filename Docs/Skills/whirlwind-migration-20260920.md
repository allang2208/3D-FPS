# 大旋风：原 game-dev 风车迁移

后续动作与打击感强化见 [V5 风车参考与打击感](whirlwind-impact-v5-20260920.md)。本篇保留迁移及 V4 历史记录；当前 V5 资产、源与编译状态以新记录为准。

内部 ID 保留 `whirlwind`，显示名改为「大旋风」，仅战斗近战兵器可施放。当前符文剑、寒晶剑及普通/加长柄动画路径均已接入；生产斧镐、枪械与空手不能执行。可从技能页拖入 Q/E/X/1–4，不占用新的固定按键。

## 原项目依据与数值

原项目 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev`：

- `data/skills.json:skills.whirlwind`：等级1～20、伤害倍率1.5+0.1K、常驻力量+K、冷却10−0.2K秒、体力20+K、半径120+5K、近战附加半径80、击退250、眩晕2500ms、旋转800ms。
- `src/config/skill-formulas.js:getWhirlwindRadius`：近战附加半径与基础半径相加；原项目改造用额外距离，UE现有改造接口使用近战范围倍率。
- `src/entities/components/whirlwind-system.js`：近战攻击数值乘技能倍率并取整，每目标一次，直接击杀计数；旋转后520ms收势。
- `src/ui/skill-manager.js:addWhirlwindExp`：`命中人数×1 + (命中人数≥2 ? 3 : 0) + 击杀人数×15`；没有挥空施放经验。升级需求100×当前等级。

UE 沿用法术迁移的 `1原单位=1.5cm`，因此技能半径为 `(200+5K)×1.5cm`，再乘当前近战范围系数；击退3.75m，眩晕2.5秒。1级：倍率1.6、冷却9.8秒、消耗21体力、基础半径3.075m。20级：倍率3.5、冷却6秒、消耗40体力、基础半径4.5m。力量从等级派生，不在读取存档时累加。

原动作参考已实际查看 `tools/ai-gen/_scratch/player_whirlwind_20260824/weapon_preview_after/whirlwind_weapon_contact.png`。23帧先举剑、降低重心、转体横扫、回到举剑；历史视觉时长704ms，业务旋转800ms。本次按用户新的第一人称要求重建深度和持物姿态，不是二维帧的自动精确还原。

## 第一人称动作与命中

当前 V4 阶段：蓄势0.5s、横向旋转0.8s、收势0.52s，总长1.82s（480Hz采样资产1.820833s，运行时归一化映射）。蓄势分0–140ms回拉、140–340ms减速蓄住、340–500ms加速展开，使用共享节点速度的五次 Hermite 连续轨迹，中间不再整段停死，500ms横持节点带着速度接入横扫。前100ms从施放瞬间的实际骨骼姿态接入，并按剑柄约束双手；该时间包含在0.5s内。沿用 Manny 手臂、现有双手接触、前臂辅助骨及整臂连续求解器；武器不另烘焙身体旋转，避免与游戏镜头旋转重复叠加。

2026-09-20 用户反馈旋转方向相反并要求两圈，镜头/控制朝向现改为 **-720°**，相对首版反方向连续旋转两周，结束朝向回到起始朝向，不额外倒转。相机与横扫判定继续使用同一个有符号角度参数；0.8s旋转时长、停帧、动态模糊及同目标每次技能仅一次伤害/修炼不变。旋转期间禁止鼠标叠加视角输入；施放期间禁止移动和跳跃，中断保留已经转过的朝向。转角由运行时控制，横持姿态FBX无需重烘焙。

以同一技能时钟驱动姿态、连续环形扫掠、镜头及动态模糊；沿用近战世界遮挡与穿过多个敌人的命中查询。每目标一次伤害，继承共用暴击、武器精通、巧手与命中附效入口。确认命中后暂停动作与转向45ms，同次最多累计135ms，避免密集目标使技能长时间卡住。V2 用独立的背景模糊替换首版全画面运动模糊，停帧时强度归零，旋转峰值参数仍为0.65；结束/死亡/菜单/切装取消时恢复原相机设置。以上为实现参数，未进行实机手感判定。

施放实际开始时同一档案事务扣体力和提交冷却，冷却立即走表。空挥不加修炼；旋转结束汇总命中与直接击杀，取消只提交已经发生的结果一次。尸体、召唤物、禁止修炼标签及后续持续伤害击杀不计入本技能经验。旧档技能版本11→12只补 `whirlwind` 与默认冷却字段，保留原技能进度、装备及快捷栏。

## 接入与可编辑来源

- 数据：`Content/ColdSteelData/skills.json:whirlwind`。
- 原生：`Skills/WhirlwindTypes.h`、`Skills/ColdSteelWhirlwindModel.cpp`、`Weapons/RuneSwordWhirlwind.cpp`，以及现有技能/档案/技能页/快捷栏连接点。
- 普通柄：`/Game/Weapons/AzureRunesword20260913/A_RuneSword_WhirlwindV4`。
- 加长柄：`/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_WhirlwindV4`。
- 本机源：`SourceAssets/Whirlwind20260920/WindupV4/Whirlwind_Manny_Editable.blend`、`Export/A_RuneSword_WhirlwindV4.fbx`、`LongGripExport/A_RuneSword_WhirlwindV4.fbx` 与加长柄可编辑关键帧JSON（均在 WindupV4 下）。
- 作者脚本：WindupV4 下 `whirlwind_motion.py`、`author_whirlwind.py`、`author_long_grip.py`。动作重定时修改数据后重出FBX与加长柄，运行时仍按阶段比例映射。
- 前景保护材质：`/Game/Skills/Whirlwind20260920/M_WhirlwindFocus`，可编辑图表及 HLSL 源 `WindupV2/focus_blur.hlsl`；创建脚本 `make_focus_material.py`。
- 前景时域材质：`/Game/Skills/Whirlwind20260920/ForegroundV3/`；作者脚本 `WindupV3/make_temporal_materials.py`，原材质到技能副本的映射 `Content/ColdSteelData/whirlwind-temporal-materials.json`。
- 图标：原创绘图脚本 `make_icon.py`，银色六边框、石墨底、水平剑与旋转弧线；运行PNG为 `Content/ColdSteelData/Skills/whirlwind_cold_steel.png`，已登记公共恢复脚本。
- 复用来源：当前项目已使用的 Manny 与握持作者源。授权素材/手臂/完整Blend保持本机，不将原创动作或图标的作者身份误写成底层Manny资产的再分发授权。

## 首版交付记录

普通柄与加长柄动画已通过串行接入桥导入/制作并保存。导入最初在PIE中保存失败，结束PIE后从保存步骤续接，未重复导入。

执行了必要的 Game 目标构建；本技能的私有成员访问编译错误已修复。首次完整构建被并行武器源码 `M4HandstopVisual.cpp:59` 中未声明的 `bEnabled` 阻塞，保留该文件，不覆盖其他任务改动。

2026-09-20 用户关闭 UE 后，已再次执行 `Tools/Build/Build-Editor.ps1`。此前武器错误已不再出现；本次 Editor 构建被并行建筑源码 `VoxelBuildComponent.cpp:298`（`GetViewTarget` 不接受输出参数）与 `:309`（`UpdateViewTarget` 为 protected）阻塞，未修改该建筑文件。构建日志为 `Saved/BuildEditor/build-20260920-093635.log`。完整 Editor 模块尚未构建成功；UE 保持关闭，未启动运行验收。同一公共源码仍阻塞构建，因此未重复执行 Game 目标。

遵守用户规则：没有运行测试、PIE回归、动作预览渲染、截图或静态验收。由用户后续实机测试。

## 反向两圈调整（2026-09-20）

已将正式数据 `turnDegrees` 与源码缺省值从 `365` 改为 `-720`，技能描述同步为两周。运行时镜头与扫掠本来就共用该有符号参数，因此无需改动命中循环，也无需重出横持动画；0.8s 内完成两圈。作者源注释已同步，既有 `authoring.json` 保留首次导出时的历史参数记录。

本轮为配置调整，没有额外执行构建或测试。当前 UE 已重新打开；`MasteryDefinition` 的技能定义使用进程内静态缓存，需重新打开 UE 才会读取本次 JSON 参数，单独重开 PIE 不会刷新。源码缺省值随后续常规构建更新，正式 JSON 参数的生效不依赖该缺省值构建。

## 0.3秒蓄势与前景清晰 V2（2026-09-20）

用户反馈手和肩在旋转时拖影。首版使用相机全画面运动模糊（峰值0.65，最大跨度至少8%），V2 施放时暂时关闭该项，改用完成时域抗锯齿/色调映射后的背景采样。手臂网格（含肩）、挂载武器及子部件仅在技能期间写 CustomStencil 231；原像素与2像素边缘保护区保留输入颜色，背景采样也排除231，避免把手臂颜色拖进背景。背景使用9点带权偏航方向采样、无历史帧累积，最大单侧跨度约1.17%画宽。退出时恢复原自定义深度、模板值、写掩码和相机运动模糊设置。

项目开启 `r.CustomDepth=3` 与 `r.CustomDepthTemporalAAJitter=0`，供这一后置遮罩对齐使用。该后处理只在技能期间挂载，起势与停帧阶段强度为0。保留骨骼运动矢量；120Hz子步仍用于战斗判定，但每个渲染帧只提交最终相机朝向下的一次骨骼姿态，完整停帧时清除残留骨骼速度。没有关闭全局TSR、改贴图清晰度或更换手臂材质；如果仍存在时域残影，需根据用户实机反馈继续定位，不能以素材保存或构建成功代替视觉判断。

普通柄/加长柄 V2 已制作、导入和保存，可编辑 Blend、两份 FBX 与加长柄关键帧 JSON 已同步；运行时已改用 V2。此前建筑编译阻塞已不再出现，完整 Editor 构建成功：`Saved/BuildEditor/build-20260920-110333.log`。接入时 UE 未运行，使用离线 Python commandlet；首次在材质属性名处中断，普通柄已保存，从材质与加长柄继续完成，没有重复导入。接入回执及构建输出在 `SourceAssets/Whirlwind20260920/WindupV2/`。

实现参考：[Epic 后处理材质](https://dev.epicgames.com/documentation/unreal-engine/post-process-materials-in-unreal-engine)、[Epic 时域上采样后的后处理](https://dev.epicgames.com/documentation/unreal-engine/temporal-upscalers-in-unreal-engine)、本机 UE5.8 的 MaterialTemplate.ush、SkinnedMeshComponent.cpp 与 MaterialEditingLibrary.cpp。没有启动游戏、运行测试、截图或动作渲染，最终手感和拖影改善由用户测试。

## 0.5秒节奏蓄势、前景时域处理与 ALT 修复 V3（2026-09-20）

用户确认残影仍集中在手、肩、武器，V3 将这三类前景作为处理对象。高速镜头运动会放大时域累积中的残留；V2 的后置背景模糊遮罩不能消除已经进入时域结果的重影。本次针对这一可能来源加入 Temporal Responsiveness，实际重影成因与改善程度未做运行测定。

蓄势扩展为0.5秒，重新制作120ms回拉、220ms蓄住、110ms展开、50ms送出四段曲线，普通柄和加长柄 V3 已导入、保存并接到动画加载路径，编辑源、FBX和关键帧JSON同步保留。0.8秒反向两圈、命中停帧、伤害/修炼公式不变。

项目启用启动时读取的 `r.Velocity.TemporalResponsiveness.Supported=1`。基于当前两类剑的手臂、武器模块和符文覆盖层，生成16个独立的材质/实例副本，仅这些副本输出完整时域响应。运行时在技能开始时临时替换对应前景材质，复制原动态参数，退出时恢复原材质与模板状态。没有改原手臂或武器的贴图、颜色与材质图表；全局时域抗锯齿保持原设置。完全拒绝前景历史可能带来局部边缘闪烁，需要用户自行判断取舍。实现源见 `SourceAssets/Whirlwind20260920/WindupV3/README.md`。

ALT 修复将鼠标可见与菜单/输入锁定区分，近战 CanUse、破防、生产工具、双持输入占用及冲刺体力逻辑复用 `AFPSGAMEPlayerController::BlocksOngoingActions`。ALT 的 GameAndUI 输入模式不再主动将键盘焦点转交 HUD；持续技能/动作不会仅因显示鼠标而隐藏或取消，真实菜单的原有行为保留。点击 UI 的鼠标按下仍被消费，释放事件继续转交游戏。

接入使用串行桥；普通柄先保存，初次材质连接因引脚名错误中断，从该连接续接后保存全部16个材质及加长柄，没有重复导入普通柄或覆盖 V2。回执在 WindupV3 目录。

为加载新的原生代码和启动时渲染能力，读取未保存包状态为空后，通过 UE 正常退出接口关闭编辑器并执行必要完整构建。构建被其他模块的两处错误阻塞：`Combat/MonsterToughnessTypes.h:57` 的 `extern FPSGAME_API thread_local` 导出声明（C2492），以及 `WorldGeneration/TemperateHillsStreaming.cpp:503` 的 `Now` 隐藏同函数已有局部变量（C4456）。按并行修改保留规则，未改动这两个文件。日志为 `Saved/BuildEditor/build-20260920-131625.log`，本轮原生修改尚未编入基础 Editor DLL，UE 保持关闭，不用旧 DLL 宣称新效果已接入生效。

未运行测试、PIE、截图、渲染或回归。资产制作/保存已完成，完整原生构建及其后的启动仍待解除上述阻塞；用户实机测试亦未执行。

## 旋转镜头与前景帧同步修复（2026-09-20）

用户要求排查双动画错位后，读取源码和现有运行组件状态：手臂和模块化剑身共用同一段动画及WPN_root挂点，大旋风分支跳过待机/走路/普通攻击。发现近战组件的 `TG_PostUpdateWork` 晚于 UE 的 PlayerCameraManager 更新，导致技能先前写入的新相机组件角度和前景姿态与本帧缓存渲染视角不同步。完整排查记录位于 `SourceAssets/Whirlwind20260920/AnimationDiagnosis/README.md`。当时运行快照持M16，未抓到实际大旋风帧，未将全部残影确认为单一原因。

用户随后明确要求修复。`RuneSwordWhirlwind.cpp` 现于施放成功后将组件切到 `TG_PostPhysics`，正常结束/取消时恢复 `TG_PostUpdateWork`。保留角色更新前置依赖，让同一帧的镜头转向、手臂与武器姿态、模糊参数先完成，再由 UE 缓存渲染视角。没有增加镜头重复更新或动作计时，原有动作、停帧、判定和修炼数据不变。

此前13:16的构建阻塞已由后续工程构建解除，13:44构建日志为成功。本次执行完整 Editor 构建接入调度修复，结果见下方记录；遵守默认规则，不运行游戏或追加测试。

本次完整 Editor 构建成功，已更新基础 `UnrealEditor-FPSGAME.dll`：`Saved/BuildEditor/build-20260920-140939.log`。构建前编辑器已关闭，本轮没有启动编辑器或 PIE，未进行实机视觉验证。

## V4 连续蓄势与实际姿态衔接（2026-09-20）

用户确认镜头帧同步修复成功，随后反馈0.5秒蓄势僵硬，并授权优化。V4 将原先各段独立归零的速度改为共享节点速度的五次 Hermite 轨迹：0–140ms回拉，140–340ms保持移动并减速蓄住，340–500ms展开；500ms节点以非零速度接入横扫。位置、握柄朝向和刃面朝向共享曲线时间，手臂继续由现有整臂求解器约束在同一握柄上。

新增 `URuneSwordMeshComponent`，仅用于 RuneSwordViewmodel。切片前捕获实际显示的完整骨骼姿态，第零帧保留此姿态，在前100ms按五次曲线衔接到当前大旋风采样，不额外增加蓄势时间。父空间混合保持骨段长度，双手按共同剑骨计算握持目标，再以两骨IK修正肩肘；手指与辅助骨保留局部关系。武器骨及其子骨不被手臂IK重复搬动。提交发生在骨骼挂点发布前，沿用已确认的PostPhysics时序。

普通柄和18mm加长柄 V4 均经串行桥制作/导入并保存；可编辑Blend、两份FBX及加长柄逐帧JSON在 `SourceAssets/Whirlwind20260920/WindupV4`。旧V3材质和动作保留，运行加载路径改为V4。0.8秒反向720度、停帧、技能数值、修炼、ALT逻辑未调整。

编辑器无未保存资产后正常退出完成必要构建。首轮编译在新调用点遇到局部变量 `Cast` 遮挡UE `Cast<>` 函数，限定为 `::Cast<>` 后完整 Editor 构建成功：`Saved/BuildEditor/build-20260920-183009.log`，基础DLL已更新。随后重新启动原FPSGAME工程（未启动PIE）。没有运行检查、游戏测试、预览渲染、截图或回归，动作手感由用户实机测试。

## 施放期间禁止移动和跳跃（2026-09-20）

用户确认整体动作效果后，要求施放期间不可移动、不可跳跃。移动锁直接读取大旋风活动状态，覆盖0.5秒蓄势、0.8秒旋转、0.52秒收势及命中停帧；正常结束或取消时随活动状态自动解除，不修改控制器的输入忽略状态，保留ALT鼠标交互。

起手清除待处理移动输入、水平惯性、跳跃缓存、持续跳跃/攀爬请求及短按冲刺的闪避计时。施放期间阻止方向移动、跳跃、冲刺、滑铲和闪避入口，移动组件同时将最大移动速度置零并拒绝原生跳跃。空中施放保留原有垂直速度与重力，不悬停。结束后由既有移动速度及属性计算恢复控制，无需还原一份可能过期的速度快照。

源码修改已完成。必要Live Coding接入返回`CompileNotStarted / Live coding canceled`，未成功编译；随后为常规构建停止PIE，正常退出脚本因未保存包`/Game/Weapons/DualPistolQuickCombat20260920/M1911/r/Animations/A_Dual_M1911_r_quickcombat`而停止。未保存、覆盖或丢弃该资产，编辑器保持打开，本次限制尚未编入基础DLL。回执位于`SourceAssets/Whirlwind20260920/MovementLock/`；保存现有编辑并关闭UE后继续常规构建。未运行测试或验收，由用户自行测试。
