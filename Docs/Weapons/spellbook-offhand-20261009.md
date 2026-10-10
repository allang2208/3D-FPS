# 元素炼金魔法书副手接入

> **2026-10-10 已暂停。** 当前为 V17 恢复原阅读方向、原开掌的已编译现场，视觉未确认、recover 待重做。历史版本不作为当前认可模板。后续任务及归档见[暂停记录](spellbook-paused-20261010.md)。

用户选择 evildeer《Magic book set》蓝紫色金纹封面（book2 / Elemental Alchemy），左手从书脊侧握持。最初接入闭合握持与移动，随后新增 F 键持书前击及法杖组合的右键专注翻页。照片握姿先制作 Photo V2，随后按用户“封面不用正对镜头，像照片一样侧着”的修正制作 Photo V3：书脊朝向视线，封面向侧后方转开，书顶向右上倾斜；手背仍可见，拇指压封皮、四指绕到另一面。

- 定义：`Content/ColdSteelData/items.json` 的 `ue_alchemy_spellbook`，当前按用户要求改为 2 × 2 格，副手槽 8 / 11。
- 获取：现有 `GrantStartingArmory` 一次性仓库发放；沿原装备、存档与仓库事务保存，不改写现有用户存档。
- 资源：`/Game/Weapons/SpellbookEvildeer20261009/`。保持已导入的原始封皮及页面 PBR 材质。
- 抓握：当前作者源为 `SourceAssets/SpellbookEvildeer20261009/GripPhotoV3/author_grip.py`。V3 将 V2 的书本挂点和手指姿态作为固定夹持输入，联动转侧手与书，并围绕新掌向重新制作整条左臂支撑，输出 `grip.json` 与 `SpellbookAuthoredGrip.h` Revision 3。保持 V7 bind、蒙皮、骨长。初版 `Grip/` 保留历史，`GripPhotoV2/grip.json` 仍为接触制作输入。
- 移动：基础姿态复用空手同源的 `LeftGaitV16` 32 组走路／32 组奔跑轨迹，按照片掌向重制肩肘腕支撑。后续用户要求低位小幅持书，运行按 `SpellbookCarryTuning.h` 将走路／奔跑姿态混合权重分别压到原来的 0.35／0.25，再把完整左臂下移 5 cm。继续使用 `FStaffLocomotion` 的脚步相位与停启、走跑过渡；书随最终手骨同帧移动。
- 可编辑源：`GripPhotoV3/Spellbook_PhotoGripV3.blend`，包含原生 V7 左臂、所选书本及 Idle / Walk / Run 动作。三段动作与 C++ 表同源；Blender 的循环为标准化步幅，游戏速度仍由脚步距离相位驱动，无需重新导入 UE 动画。
- 显示：独立左臂拥有手套衣袖与消耗品动作，主手模型让出重复左臂；主手换弹／检视时暂收书并恢复主手原生左臂。无主手时仍显示现有右臂待机。
- 世界：现有身体握持映射转接左手指姿和书的静态模型，拾取模型与实时模型图标使用同一本书。
- 占手：持书阻止原左手施法；F 优先路由持书前击，主手法杖施法继续使用右手。
- 版权：原来源、作者、CC BY 4.0 与修改说明在源目录 `ATTRIBUTION.md` 及随内容打包的 `ColdSteelData/Licenses/SpellbookEvildeer20261009.txt`。

初版后台构建日志为 `Saved/BuildEditor/build-20261009-212300.log`。照片握姿 V2 完成后的最终 `FPSGAMEEditor Win64 Development` 后台构建记录为 `Saved/BuildEditor/build-20261009-214238.log`，返回 `Target is up to date`、`Result: Succeeded`；当前产物为 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。这是构建状态，不代表视觉、运行时或联机验收。可编辑 V2 Blend 已由后台 Blender 实际保存。

本任务未启动 UE 编辑器、游戏、预览渲染或自动测试。下次进入游戏，在仓库取出“元素炼金魔法书”并放入副手槽，由用户测试实际握持与走跑效果。

## 后续装备图标同步

按用户要求制作 `Content/ColdSteelData/Icons/ue_alchemy_spellbook.png`，使用真实闭合书与原 PBR：当前为 320 × 320 透明 RGBA，适配 2 × 2 占格，正交、竖直居中，轮廓主轴约 91%，稍露书脊。作者入口与可编辑场景位于 `SourceAssets/SpellbookEvildeer20261009/InventoryIcon/`，正式 PNG 与作者 PNG 同步。

`items.json` 补齐 PNG 与取景角度；`ColdSteelEquipmentIcon.cpp` 支持目录中的 roll，让这本书的实际长轴竖直展示。已有异步模型图标和目录 PNG 回退覆盖装备栏、背包和仓库。旧存档在正常加载事务中同步此书的展示字段，保留原实例装备状态与数值。

本次离线渲染仅用于用户要求的正式图标；没有启动 UE、游戏或自动测试。后台构建 `FPSGAMEEditor Win64 Development` 已完成，日志 `Saved/BuildEditor/build-20261009-215101.log` 返回 `Result: Succeeded`；游戏中的显示效果由用户测试。

## Photo V3 侧握修正

用户确认“图标保持现状”，本次只改游戏握持。书顶在相机画面中向右倾约 31 度，封面法线与相机前向反方向约 68 度，露出书脊并让书页外缘向侧后方退。这是单张照片的三维适配参数，不宣称恢复了照片拍摄深度。

固定 V2 的 `BookInHand` 和局部指骨旋转，联动改变掌向与书的方向，再制作 65 组 Idle / Walk / Run 原生肩肘腕局部姿态。腕部轨迹、原副手步频、走跑幅度、消耗品让手和装备图标保持原流程。V3 JSON、C++ 姿态表、独立编辑 Blend 已实际保存；未渲染或运行游戏。

用户选择自行关闭 UE 后继续编译。编辑器退出后执行常规 `FPSGAMEEditor Win64 Development` 构建，等待已有构建结束后返回 `Target is up to date`、`Result: Succeeded`；本次最终日志为 `Saved/BuildEditor/build-20261009-220751.log`。没有重新启动编辑器或游戏，实际侧握观感与移动效果由用户测试。

## 后续 2 × 2 占格与图标

用户将魔法书改为 2 × 2 格；目录尺寸及魔法书缺省占格同步更新。沿 `MigrateAuthoredGridFootprints` 为已有 `ue_alchemy_spellbook` 实例回填新尺寸，并清除旧矩形物品的旋转标记，保持图标竖直；缩小占格沿用原存放位置与装备状态。

图标保持此前确认的 0 / 75 / 90 取景角度，重新从原模型和 PBR 渲染为 320 × 320 正方形画幅，等比例取景，不拉宽书体。正式 PNG、作者 PNG、编辑 Blend 和 `production.json` 同步保存，渲染记录为 `InventoryIcon/render-2x2.log`。实时模型图标继续由同一占格推导画幅。握姿与动作未修改，未运行游戏测试。

此次后台常规构建已编译 `ColdSteelInventoryRules.cpp` 并链接 `UnrealEditor-FPSGAME.dll`，日志 `Saved/BuildEditor/build-20261009-221040.log` 返回 `Result: Succeeded`。没有启动编辑器或游戏，旧存档迁移及界面显示由用户测试。

## 后续低位小幅持书

用户要求参考空手摆幅，在屏幕下方晃动。读取当前 `UnarmedAuthoredLocomotion20261001` 与作者 `full-pose.json` 后，确认空手左臂和持书基础腕部轨迹同源，而持书有额外上抬构图及更长的可见书体。此次在既有完整局部姿态混合处缩小移动权重：走路 0.35、奔跑 0.25，保持脚步相位和速度过渡，并在相机空间统一下移完整左臂 5 cm。不会单独偏移书本或拆开手指接触。

参数统一保存在 `Source/FPSGAME/Weapons/Spellbook/SpellbookCarryTuning.h`。`GripPhotoV3/save_editable.py` 读取同一参数，以与运行相同的局部位移及归一化四元数混合保存 Idle / Walk / Run；编辑源展示最大步态权重，实际运行另有原速度淡入及轻微变化。`Spellbook_PhotoGripV3.blend` 与 `editable-source.json` 已更新，保存记录为 `GripPhotoV3/save-low-carry.log`。基础 V3 姿态表、夹书挂点、侧握方向、2 × 2 占格和图标保留。

本次仅修改既有函数体及编译期数值，无类布局变化。通过现有编辑器的 MCP 批次互斥调用 Live Coding，返回 `Result: Success`、`Live coding succeeded`，记录为 `GripPhotoV3/compile-low-carry-result.txt`。当前会话已热编译；此次低位参数尚未进行基础 Editor DLL 的常规构建，需在编辑器关闭后构建。没有启动或重启编辑器、运行游戏、截图、渲染或执行动作测试。

## 持书快速近战

按用户要求，F／快速近战快捷栏在副手装备此书时优先进入 `SpellbookPush`。保留 Photo V3 的局部指骨和 `BookInHand`，从低位持书由肩肘带动整条左臂快速前伸，书保持侧握；接触后收回当前低位待机／移动层。动作长度 0.43 秒，接触 0.14 秒，前伸时肩部跟进、肘部保留少量弯曲，原生骨长和蒙皮不变。

作者入口为 `QuickMelee/author_strike.py`，输出 57 个密集原生姿态至 `strike.json` 和 `SpellbookAuthoredStrike.h`；`save_editable.py` 实际保存 `QuickMelee/Spellbook_QuickMelee.blend`，含原生 V7 左臂、所选书本和 `A_Spellbook_F_ForwardShove`。沿用原书本约束，动画源读取当前低位参数。新增动作直接编入 C++，无需导入新 AnimationSequence。

动作使用现有 `UFPSQuickCombatComponent` 单一时钟，在角色更新相机前推进；接触跨帧时先停在准确接触时间，刷新该姿态并从实际书页外沿查询一次命中，再继续恢复。复用快速近战体力、伤害、击退、修炼和确认音；武器属性取实际副手书实例，不借用主手枪械属性。结束后沿原规则解除动作占用，不追加冷却；死亡、换装、界面和翻越沿既有动作仲裁退出。世界身体采样使用同帧左手和 `SpellbookPush` 通道。

此制作未运行游戏、渲染或测试；实际击出观感、命中与切换由用户测试。

持书前击的最终常规后台构建已完成：`Saved/BuildEditor/build-20261009-224717.log` 返回 `Target is up to date`、`Result: Succeeded`。等待工程既有构建和资产导入结束后，使用 `Tools/Build/Build-Editor.ps1` 完成 `FPSGAMEEditor Win64 Development` 收尾；当前基础 DLL 已包含持书前击及此前低位小幅摆动，不再仅依赖低位参数的 Live Coding 补丁。本轮没有打开编辑器或运行游戏，实际效果由用户测试。

## 空主手右拳与法杖专注

后续输入规则：空主手＋魔法书时，左键使用现有普通拳击的右拳，按住连续出拳也固定右侧。左手继续保持书脊握姿；双空手仍按原规则交替出拳。世界身体的空手采样只接管自由的右手，避免覆盖持书左手。F 仍是此前持书前击。

主手实际为法杖且副手为本书时，右键切换专注，再按一次收书；右键松开不退出。入口位于角色原有 Staff 右键分支，并以装备事务缓存的主手法杖身份再次限制。手枪＋书继续走原 ADS，其他主手继续保留各自右键行为。专注是本次输入／表现状态，没有新增未要求的伤害增益、Buff、蓝耗或技能等级。

左手从实时持书进入积蓄动作，0.18 秒左右书本离手；0.65 秒达到蓄势掌姿，书在相机左下前方悬浮。0.60 秒开始快速打开，打开时长 0.35 秒。展开后沿已保存 `A_Spellbook_FlipPages` 采样，一个余弦往返周期 16 秒，先翻向另一侧再反向翻回，端点减速至零。退出时从当前页进度退回、反向播放开书轨道合拢，再回到实时低位握书姿态。专注期间按 F 会先完成合书回握，再提交原快速近战动作和体力消费；界面、换装、死亡、翻越及消耗品接管沿现有中断入口取消专注。

运行实现：`SpellbookFocus.cpp`、`SpellbookFocusPose.cpp`、`SpellbookFocusMotion.h`；V7 积蓄手型读取当前 `fireball_hand_pose.json` 的掌向、手腕位置和手指语义，适配原生完整肩肘腕及辅助骨，未直接套用旧 Manny 骨轴。`Focus/author_focus.py` 生成 40 组姿态到 `focus.json` 和 `SpellbookAuthoredFocus.h`；`Focus/save_editable.py` 已实际保存 `Focus/Spellbook_Focus.blend`，包含积蓄、浮书、开合及一轮前后翻页。保存日志 `Focus/save-editable.log`。

书页使用现有三张活动页、每页八段骨骼的弯曲动画，不启用 Chaos 布料、刚体或逐页碰撞。闭合持书继续使用静态模型；翻页组件只在专注显示时由现有书组件手动采样，无独立 Tick。装备时异步加载现有书模型和 Open／FlipPages，姿态表按组件有界缓存；本地世界视图的浮书共享同一骨骼结果（Leader Pose），不另跑一套动画图。世界闭合书跟随原 StaticSource 可见性隐藏。此为现有本地控制流程，不新增专注状态的跨客户端复制协议。

采用此方案的依据是本动作的页数、弯曲轨迹和往返节奏都可预定，不需要环境碰撞反馈，因此可省去实时布料求解及碰撞更新；这属于实现选择，未进行帧率或 GPU 测量。Epic 的 SkeletalMeshComponent 文档也明确指出持续更新布料外部碰撞有性能成本： https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SkeletalMeshComponent?application_version=5.6 。

上述现有 UE 模型和翻页动画已在本书初版导入中保存，本次复用它们，不需要再次导入模型。新增手臂积蓄姿态编入 C++。源码和可编辑源已保存；本轮没有运行游戏、截图、渲染或自动测试，实际握持、翻页方向、收书观感和输入效果交由用户测试。

用户关闭编辑器后，已通过 `Tools/Build/Build-Editor.ps1` 完成常规 `FPSGAMEEditor Win64 Development` 构建，日志 `Saved/BuildEditor/build-20261009-231118.log` 返回 `Result: Succeeded`。本次实际编译 `SpellbookFocus.cpp`、`SpellbookFocusPose.cpp`、持书组件及输入／身体接入，并链接基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。没有重新启动编辑器或游戏，构建成功不代表运行或视觉验收。

## 阅读方向、自然接书与翻页金光

用户反馈内容倒置后，将专注悬浮姿态沿书面转动 180 度，两个书面轴同时取反，保持页面法线与阅读倾角。闭合 Photo V3 书脊抓握、F 前击、低位摆动、2 × 2 占格和图标继续使用原输入。

收书改为独立的抬手迎接、接住书脊、手指扣合及整臂下落；不再倒放积蓄动作。`Focus/author_return.py` 以肩、腕连续三次曲线、完整肩肘腕支撑和错峰指姿生成 61 帧 `return.json`／`SpellbookAuthoredReturn.h`。运行入口采样实时左臂并消退姿态差，收势末段接回实时移动层。未离手便取消专注时，仅将当前握书姿态平滑放下。

返回总时长为当前书页回正 0 或 0.42 秒＋按当前开度计算的合书时间（最多 0.38 秒）＋0.64 秒接书收势。手臂从退出时便开始迎接，书沿连续弧线转回手中；总进度 70% 到达书脊接触点，此后书与最终手骨刚性同步，手指依次扣住并共同回落。退出途中再次右键仍沿原规则完成收书后重开；F 排队仍在收势结束后触发，不改快速近战结算。

`SpellbookFocusGold.cpp` 为打开／翻页增加两道细金色流光与 16 个闪烁光点，翻页中段加强，合书随开度淡出。一个 DynamicMesh 组件、416 个三角面，装备时建模一次，运行仅更新三个材质标量；无逐帧网格上传、粒子求解、碰撞或动态灯光。材质为独立的 `/Game/Weapons/SpellbookEvildeer20261009/Effects/M_Spellbook_GoldOrbit`，不修改原 PBR。作者入口为 `Focus/GoldOrbit/install_material.py` 与 `gold_orbit.hlsl`。只在专注浮书显示时绘制，取消或卸装时隐藏。此为实现预算，没有进行性能测量。

`Focus/Spellbook_Focus.blend` 已通过后台 Blender 同步新的阅读方向和接书曲线，包含原生 V7 手臂及原书，保存日志 `Focus/save-natural-return.log`。金光制作源保留在上述 HLSL／Python 与运行几何代码中。本轮不运行游戏、渲染或动作测试；资产保存及构建结果另行记录。

本轮金光材质已通过无界面 Python commandlet 实际创建和保存，`Focus/GoldOrbit/install_receipt.json` 返回材质路径及空着色器错误列表；最终 `install-material.log` 为 `Success - 0 error(s), 6 warning(s)`，没有材质编译失败或默认材质回退记录。等待既有构建／commandlet 退出后，常规 `FPSGAMEEditor Win64 Development` 构建 `Saved/BuildEditor/build-20261009-233626.log` 返回 `Target is up to date`、`Result: Succeeded`，现有基础 DLL 已是当前源码产物。本次没有启动交互编辑器、游戏或渲染验收，实际方向、接书观感及金光效果由用户测试。

## 用户指定的先合书、下落、抓握与待机

用户再次反馈上一版收书不自然，明确要求“书本直接合上，然后掉到左手上，左手衔接抓握动作，然后自然恢复待机状态”。本节替代上一版同时抬手迎接和弧线返书的动作设计；上一版不视为已认可。

运行以单一退出时钟依次执行：原位合拢 0.28 秒、下落 0.22 秒、接触后抓握 0.16 秒、收回待机 0.42 秒，共 1.08 秒。合书阶段位置固定；不再先倒翻至首页，而是从当前页姿态直接向闭合参考姿态混合。浮书在手动动画求值后写入同一骨骼缓冲，本地世界书仍共享这一份结果，没有增加动画组件或物理求解。

左手在合书时移到书下方等待，保持开指；闭合书沿加速下落曲线进入书脊握点，下落期间转向侧握朝向。接触后书刚性跟随手骨，手臂下沉约 1.8 cm 缓冲，五指才依次扣合，随后整臂带书回到当前低位待机／移动层。接书点相对退出时的实际书位置计算，覆盖悬浮轻晃以及书仍在升起时的取消。尚未离手便取消时，仍直接将当前握书姿态放低。

`Focus/author_return.py` 从 `SpellbookFocusMotion.h` 读取秒制参数，生成 73 个姿态到 `return.json` Revision 3 与 `SpellbookAuthoredReturn.h` 中的 `SpellbookAuthoredDropReturn`。`Focus/save_editable.py` 同步当前页直接合拢、下落、接触缓冲、扣指及待机交接；可编辑源 `Focus/Spellbook_Focus.blend` 的本次制作日志为 `Focus/save-close-drop.log`。示例在完整往返翻页后再翻到中间页合书，覆盖新闭合轨道的制作意图。既有类布局与资产身份保持原样，本次为函数逻辑和作者姿态数据调整。

本轮按规则仅制作、保存与必要编译，不主动运行游戏、测试或渲染。编译生效范围在完成后记录。

最终构建：编辑器在等待接入期间已退出，原 Live Coding 请求未连接成功，没有将热编译计为完成；随后等待既有构建和后台资产进程结束，通过 `Tools/Build/Build-Editor.ps1` 完成常规 `FPSGAMEEditor Win64 Development` 构建。`Saved/BuildEditor/build-20261010-000548.log` 返回 `Target is up to date`、`Result: Succeeded`，基础 DLL 已是本轮当前源码产物。`Focus/save-close-drop.log` 记录可编辑 Blend 实际保存成功。未由本任务关闭或重新打开编辑器，未运行游戏或动作测试。


## 2026-10-10：实际排查缺失的开掌与落掌过渡

本节替代上一版 1.08 秒收书制作。用户明确要求排查后，在当时已运行的游戏中通过真实右键输入路径复现，并记录 `Focus/Debug20261010/baseline/transition.csv` 及阶段截图；未由本任务启动游戏、编辑器或更改装备、存档。

定位到两处实质问题：`author_return.py` 将动画总时长 `length` 覆盖成肩腕距离（旧 `return.json` 的 total 为 31.4006369），导致以秒指定的扣指时段缩成极短归一化区间；同时旧接书姿态直接使用待机侧握掌向，实际记录中落书阶段掌向 Z 为 -0.5526，书也在下落的 0.22 秒内旋转约 173 度回侧握。合拢骨骼资源存在，运行封面角度确实从约 165 度变到 0 度。旧截图的连续 PNG 捕获造成明显帧间隔，不能用它断言正常游戏也跳帧。

现改为共享秒制时钟：

| 时间 | 动作 |
| --- | --- |
| 0–0.34 秒 | 从当前翻页姿态原位合拢书本，左手开始展开 |
| 0.34–0.52 秒 | 书保持闭合悬停，掌心朝上移到接触点 |
| 0.52–0.76 秒 | 书保持阅读时的朝向，加速下落 8.5 cm；手指仍展开 |
| 0.76–0.86 秒 | 落到掌面，左手连同书下沉约 1.1 cm 缓冲 |
| 0.86–1.22 秒 | 五指错峰收拢，手腕与书共同转回照片侧握 |
| 1.22–1.64 秒 | 平滑落回原低位待机及实时移动层 |

接触使用独立的 `PalmMount`，根据实际 V7 掌骨位置、掌面法向和书背接触点求解；落掌前不再使用原书脊侧握挂点。回握时围绕接触点转动、平移至 Photo V3 挂点，最后精确衔接原握姿。页动画、输入规则、快速近战、金光及图标沿用现有实现；没有新增物理模拟或持续更新组件。

作者脚本将 `duration` 与 `reach_distance` 分开，生成 103 个姿态到 `return.json` Revision 4 和 `SpellbookAuthoredReturn.h` 的 `SpellbookAuthoredPalmCatch`。`Focus/save_editable.py` 已同步掌心挂点、开指、缓冲、回握及时间标记，后台保存 `Focus/Spellbook_Focus.blend`；手臂姿态直接编入 C++，不需重新导入动画资产。

针对本问题执行 `Debug20261010/check_return.py`：总长 1.64 秒，落掌 0.76 秒，收指 0.86–1.22 秒；等待和下落阶段掌向 Z 为 0.9063，落掌前手指保持展开，掌面接触点一致，最终局部姿态与原 Photo V3 完全一致。证据为 `authored-pose-check.json`。`source-preview/` 是后台 Blender 制作姿态预览，使用项目 75 度垂直视场；它不代表 UE 修正版运行验收。编辑器在本轮过程中退出，后续未主动重新启动。`fps.Spellbook.ReproReturn` 仅为显式执行的编辑器调试命令，默认仅记录数据，可附一个采样时间单独截图，避免连续压缩 PNG 干扰动作计时。

最终常规构建 `Saved/BuildEditor/build-20261010-003304.log` 返回 `Result: Succeeded`，本轮最终 103 帧掌心接书数据与运行函数已链接进基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。中间的 Live Coding 连接失败不计为交付；没有关闭任何既有进程。修正版游戏内动作尚未再次运行，交由用户确认。


## 2026-10-10：收书时放大与偏移异常

用户反馈新收书过程书模型放大。原因在 `SpellbookFocus.cpp` 的落掌挂接：原握持／近战路径在组合挂点前已将 `hand_l` 世界变换的缩放设为 1，新落掌分支直接使用完整骨骼变换，遗漏了同样的处理。V7 手骨携带约 `(100,100,100)` 的导入单位缩放，`PalmMount * Hand` 同时将书的尺寸与挂点平移放大。

修复在取得手骨世界变换后先保留位置和旋转、将缩放设为 1，再转换到相机空间并组合掌心挂点。没有改变已制作的合书、开掌、下落、缓冲、收指时间或原书模型尺寸。

针对真实作者数据执行 `Focus/Debug20261010/check_scale_contract.py`，结果记录于 `scale-contract-check.json`：旧路径的书缩放约 100 倍，落掌坐标错误变成约 `(300.45,427.29,484.87)` cm；剥离手骨导入缩放后恢复为 1 倍与目标 `(44,-19,-22.5)` cm，接触点计算误差小于 1e-6 cm。这是源骨架挂接计算检查，未计为 UE 游戏运行验收。现有显式调试命令额外记录浮书、手骨和握持书的三轴缩放，便于后续精确定位同类问题。

常规后台构建 `Saved/BuildEditor/build-20261010-003750.log` 已成功，实际编译 `SpellbookFocus.cpp` 并链接基础 `UnrealEditor-FPSGAME.dll`。编辑器在本轮过程中退出，没有主动关闭或重新启动；未执行修复后的游戏运行复现。


## 2026-10-10：按新照片与视频改为竖直落书

用户提供 `codex-clipboard-6c63b01a-cb82-4ebb-ac8e-430542a4b579.jpg` 与 `dae0d3b6859f77d7273cb211991421f5.mp4`，明确要求合上后竖直落掌，收指采用图中握法，再参考视频恢复待机。本节替代上一版平托封底接书。已读取视频：720×1280、约 29.948 FPS、145 帧、4.842 秒；参考关键帧与阶段解释保存于 `Focus/UprightReturn20261010/reference.json`，照片副本和抽帧同目录。

照片中书的长边向上、书页侧朝向读者，拇指和四指从两侧夹住书脊。视频前约 0.8 秒保持竖直握稳，随后翻腕把封面带入视野，约 1.6–2.6 秒继续落手到低位。三维深度为作者适配；游戏末帧仍落回现有 Photo V3 低位握书，而非改写原待机。

新的退出时钟总长 1.94 秒：0–0.34 秒合拢并立起；0.34–0.52 秒闭合竖直悬停并让左手就位；0.52–0.76 秒竖直下落 8.5 cm；0.76–0.86 秒接触缓冲；0.86–1.10 秒保持竖直收拢手指；1.10–1.94 秒连续翻腕、展示封面并整臂下落。立起时略向前、向上调整位置，为竖直书页边和左掌留出画面空间。尚未离手便取消专注的放手恢复继续为 0.42 秒。

`SpellbookFocusMotion::UprightReturn` 定义统一竖直方向；下落阶段只改变位置，收指期间手腕也保持同一方向。接住后整段采用固定 `BookInHand` 抓握，去掉旧版掌面挂点向侧握挂点滑动的路径；书和手共同翻腕。保留上一轮剥离 V7 手骨 100 倍导入缩放的修复。五指复用已制作的书脊夹持接触，准备阶段张开，接触后才错峰收拢。

`Focus/author_return.py` 输出 `return.json` Revision 5、121 组完整左臂姿态及 `SpellbookAuthoredUprightReturn`；翻腕段使用连续旋转样条经过封面朝向读者的中间姿态，腕与肩走连续下降曲线，最后精确回到原待机。`Focus/save_editable.py` 已同步竖直合书、固定握点、整臂回收和阶段标记，后台实际保存 `Focus/Spellbook_Focus.blend`。没有重新导入或更换原书模型、材质、图标及翻页资产。

本轮只读取用户参考、制作与保存、必要构建，未运行游戏、动作测试或新姿态渲染。旧平托版检查脚本改为指向保存的 V4 制作快照，避免将其掌向条件误用于本次竖直抓握；没有重跑旧检查。运行和视觉效果仍由用户确认。

本轮最终常规构建 `Saved/BuildEditor/build-20261010-010514.log` 返回 `Result: Succeeded`；实际编译四个魔法书相关翻译单元并链接基础 `UnrealEditor-FPSGAME.dll`。编辑器在接入期间退出，Live Coding 请求失败未计为完成；随后等待已有 commandlet 结束才进行后台构建。未主动关闭、打开或重启 UE。
