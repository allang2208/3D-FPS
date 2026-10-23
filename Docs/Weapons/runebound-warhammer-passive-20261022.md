# 符文战锤：符文苏醒

武器 `ue_runebound_warhammer` 的原生被动，独立于改造栏选择的通用符文，不改武器的模块接口、外形、动画或动作时序。

## 机制

- 每次对存活敌人造成实际伤害的近战攻击积累一格，十格自动苏醒，持续二十秒。
- 同一攻击的多目标、多接触共用 `MasteryAttackSerial`，最多蓄能一次。挥空、友方、场景破坏不蓄能；苏醒期间不再蓄能。
- 苏醒期间附加魔法伤害为 `智力 × 0.15 + 精神 × 0.15`。现有寒晶双手剑原生基础系数为各 `0.10`，此次系数为其 1.5 倍。
- 附伤进入 `ColdSteelWeaponDamage::Evaluate` 的魔法通道，再由现有攻击倍率、魔法增伤、暴击和目标防御统一结算。数值随每次攻击快照捕获；蓄满的那一次攻击不追溯追加新状态伤害。
- 普通三连击、蓄力重击及冲击波、冲刺下砸、旋风斩、升龙与快速近战共用此被动。一个范围动作仅蓄一格。
- 到期重新蓄能；收起、切换武器实例、死亡时清空。未设置未命中衰减，不写入存档。服务端维护实例、格数及结束时刻，通过组件复制同步。

## 表现与资产

复用苍龙 HUD 的左侧位置、浮动惯性、充盈、符文环带和晶片底层。新 UI 材质剔除顶部动物纹理，替换为几何符文印章，统一蓝色并添加缓慢漂浮的微粒。蓄能时显示当前格数比例，苏醒瞬间闪亮充满，再显示剩余持续时间。

`SourceAssets/RuneboundWarhammer20261022/PassiveV1/prepare.py` 从原始 BaseColor 提取原生蓝色刻纹的 UV 发光遮罩；复制原装 Substrate 材质并增加默认零强度的 `RuneAwake`。不改原材质、贴图、UV 或模型。模块配方按材质槽覆盖，保留通用改造件的独立材质和附加符文层。

激活时原生刻纹淡入蓝光，锤柄至锤头周围出现三十六个相机朝向的蓝色发光粒子；固定拓扑，仅更新顶点，六十米外停更，专用服务器不建表现组件。材质和锤体组件缓存每四分之一秒随模块重建刷新；收起、死亡隐藏，结束游戏销毁。

UE 资产目录：`/Game/Weapons/RuneboundWarhammer20261022/PassiveV1`。

- `T_RuneboundNativeRuneMask`
- `M_RuneboundAwakeSurface`
- `M_RuneboundEnergyHud`
- `M_RuneboundMote`

作者源与后台导入均保留在同名 `SourceAssets` 目录。`import_receipt.json` 记录实际保存范围，`publication_receipt.json` 记录配方发布，构建结果单独记入 `build_receipt.json`。

## 接入入口

- `Production/RuneboundHammerTuning.h`：次数、持续时间、附伤系数和资源路径。
- `Production/ProductionRuneboundPassive.cpp`：服务端状态、攻击去重、复制、HUD、发光和粒子生命周期。
- `Skills/ColdSteelSkillRules.cpp`：实际伤害后提交有效命中。
- `Weapons/WeaponDamagePanel.cpp`：共用伤害通道。
- `Weapons/AzureDragonEnergyComponent.*`：新增可选材质皮肤，苍龙默认资源不变。
- `Content/ColdSteelData/runebound-warhammer-{modules,gunsmith}.json`：材质绑定与被动性质说明。

按用户规则未运行游戏、PIE、截图、视觉或联机验收；实际效果由用户测试。

V1 首轮交付时，四个被动资产已保存、模块配方与性质说明已发布，`FPSGAMEEditor` 后台构建成功。该轮 `FPSGAME` Game 目标在种植工作台的并行代码中遇到缺失的 `PlantingGrid`、`PlantingGridSlots`、`PlantingProductSize` 和 `UpdatePlantingLayout` 声明，停止了已失败的 Game 构建并保留该子系统现场。当时交付为 Editor DLL 与已保存资产；后续修复与构建状态见 V2。

无界面导入采用进程级 `UE_SKIP_UBT_SDK_SETUP=1`，跳过与材质作者任务无关的重复平台 SDK 查询，避免其子进程等待共享 `Build.bat` 锁；不修改系统环境或 SDK 配置。材质端按 Substrate 节点实际的 `Emissive Color` 输入连接。

## 命中锤头粒子 V2

苏醒期间的有效攻击会在锤头释放一团 160 颗蓝色粒子，展开后沿锤头缓慢旋绕、上浮并在约 2 秒内淡出。锤头中心沿用模块接口 Z=91.6 cm，跟随实际锤体，不在受击者或相机处发射；普通三连击、重击冲击波、冲刺、旋风、升龙与快速近战共用实际伤害提交入口。同次范围攻击合并为一团，不因目标数重复堆积。

服务端确认苏醒状态及有效伤害后，通过组件的外观多播同步这次命中。粒子复用已经保存的 `M_RuneboundMote`，保留 36 颗原有常驻微粒，额外使用四组可复用命中粒子池，合计上限 676 颗；不按粒子生成 Actor 或组件。切换、死亡、结束游戏沿用原清理，六十米外停止可见几何更新，专用服务器不创建表现。

此前 Game 构建遇到的种植工作台缺失声明和 HeQue 首个包含头文件，在本轮开始时已由当前源码补齐；保留现有修正，通过本轮必要构建生成新二进制。V2 记录保存于 `SourceAssets/RuneboundWarhammer20261022/HitMotesV2`，最终构建状态以该目录回执为准。

V2 的 `FPSGAME` 与 `FPSGAMEEditor` 常规后台构建均已成功，分别生成新版 Game 可执行文件与 Editor DLL；原阻挡错误已消除。未启动编辑器界面或游戏，未运行测试、截图或视觉验收，由用户测试。

## 迅捷魔力符文特殊改造 V1

`swift_mana_rune`（迅捷魔力符文）接入符文战锤已有的 `rune` 改造栏，品级为特殊；仅此武器提供该选项。通用双手锤符文继续共用原配件库，原装模块、外观比例及所有动画保留。

安装后，符文苏醒所需的有效攻击由 10 次降为 5 次，左侧能量条按五格显示。攻击去重、二十秒持续时间、附伤公式 `智力 × 0.15 + 精神 × 0.15` 与服务端结算规则不变。移除或换用其他符文恢复十次；改造预览草稿不影响实战计数，应用后由武器实例的 `gunsmith_parts.rune` 决定，沿用现有存档、恢复与改造事务。

新表面材质 `M_RuneboundSwiftRuneSurface` 复用原生刻纹遮罩和原装 PBR，只强化锤体已有符文：常态呈较暗的蓝色流光，苏醒时增加青蓝色流动脉冲与邻域光晕。通过模块配方的 `surface_materials` 对实际材质槽覆盖，不更换模型或刻纹 UV。改造预览接入独立时间参数，暂停的预览场景也可持续显示流光；运行时使用世界时间。

迅捷符文苏醒后常驻漂浮微粒由 36 增至 60，锤头每次有效命中的蓝色粒子由 160 增至 240，并加强旋绕速度与大小。仍共用四组可复用命中池、约两秒淡出、攻击去重和原有清理规则，固定几何容量为 1020；普通符文仅显示其原有数量。

配件以特殊品级显示，使用独立蓝色符文图标，条件效果写入绿色 `special_effects` 描述。选择、应用及恢复共用配件白名单和物品数据读取缓存；其他双手锤不提供或保留该专属符文。模块重建先加载所选符文的表面材质，保持原生发光、通用符文叠层和第一／第三人称模块路径兼容。

材质保存于 `/Game/Weapons/RuneboundWarhammer20261022/SwiftManaRuneV1`。作者材质、可编辑图标场景、制作图标、导入和发布脚本，以及构建／保存回执位于 `SourceAssets/RuneboundWarhammer20261022/SwiftManaRuneV1`。基础模块重生成流程调用被动配方时，会保留已发布的迅捷符文配置。

本轮仅完成后台制作、资产保存、数据发布与必要编译。未启动编辑器界面或游戏，未执行测试、截图、视觉或联机验收，由用户测试。

迅捷符文 V1 最终 `FPSGAMEEditor` 与 `FPSGAME` 常规构建均成功，分别记录在 `build-editor-02.log`、`build-game-03.log`。Editor 首次链接遇到旧调用目标文件仍引用双参数 `SpawnImpact`；现有头文件与实现已统一为带默认开关参数的接口，重新增量构建后完成链接，未改写该并行子系统。构建和交付记录分别保存为本轮目录的 `build_receipt.json` 与 `delivery_receipt.json`。

## 双特殊魔力符文 V2

两款特殊改造共用原有符文槽，互相替换，均仅供符文战锤使用。此次只改符文、属性结算与表现，保留原装网格、模块接口和全部动画。

| 符文 | 常驻加成 | 苏醒规则 |
| --- | --- | --- |
| 迅捷魔力符文 | 攻击速度 +10%，通过现有 `attack_speed_mult` 参与普通攻击与连段时钟 | 5 次有效攻击触发，持续 20 秒 |
| 破坏魔力符文 | 持用时精神、智力各 +10% | 10 次有效攻击触发，持续 20 秒；仅苏醒自身附加魔法伤害翻倍 |

迅捷符文保留既有蓝色流光和密集蓝色微粒。攻速不另加蓄力速度，也不改变使用独立动作时钟的武技。

破坏符文 ID 为 `destruction_mana_rune`，使用特殊品级、专属灰白金属框破裂晶核印章图标。原生刻纹材质为 `M_RuneboundDestructionRuneSurface`：相向汇聚的蓝紫能量、慢速呼吸、苏醒时亮白裂光脉冲和蓝色边缘光晕。原装 PBR、刻纹 UV 和其他配件材质保留，预览沿用独立时间参数。

破坏苏醒期间，锤头周围有 48 颗聚能微粒，每次有效攻击释放 200 颗蓝紫菱形碎光，向外扩散后上浮、淡出。共用已有四组有界粒子池和 1020 颗几何容量；使用独立的 `M_RuneboundDestructionMote`，不按粒子生成 Actor。表现材质通过现有异步加载句柄共同持有，远端通过实际锤座原生表面识别所装符文；专用服务器保持不创建表现组件。

属性倍率由 `RuneboundHammerTuning.h` 的破坏符文参数提供，物品数据通过现有只读缓存识别实际安装项。`UColdSteelStatusModel::Attribute` 与静态 `ResourceMaximum` 同用当前主手装备判定，覆盖实际属性、魔法攻击、魔法防御、魔法上限和恢复；不修改已分配属性或将倍率写回存档。切换、移除和装备恢复使用现有事务，避免重复叠加。改造台用当前属性扣除已装符文倍率，再计算草稿与本槽原装的差值；物品浮窗显示直接精神／智力百分比。

苏醒附伤仍在共用 `ColdSteelWeaponDamage::Evaluate` 中处理：破坏符文将原本 `智力 × 0.15 + 精神 × 0.15` 的原生苏醒贡献乘以 2，且这里的属性已包含常驻 +10%。其他附魔、侵蚀符文和附加伤害不因此再乘 2，仍沿各自原有公式、攻击倍率和防御结算。

作者材质、粒子着色器、可编辑图标、导入和发布脚本位于 `SourceAssets/RuneboundWarhammer20261022/DestructionManaRuneV1`。发布入口同时回写迅捷符文的攻速字段和两份正式目录，基础模块重生成也保留两款特殊符文。实际保存及编译范围以该轮回执为准；未运行游戏或测试，由用户测试。

V2 最终三项新资产已实际保存，正式目录与改造图标已发布；`FPSGAME`（`build-game-03.log`）和 `FPSGAMEEditor`（`build-editor-01.log`）最终构建均成功，UBT 确认目标与当前源码一致。构建途中身体动画评估器及种植 `Prepare` 接口的共享源码不一致随后由当前源码补齐，本任务未覆盖这些文件。原有编辑器运行期间，两次桥接等待均未发送请求；无界面导入通过仅允许新建包的开关保存三个独立资产，没有覆盖已加载或未保存包。最终范围记于 `build_receipt.json`、`delivery_receipt.json`，未启动编辑器界面、游戏或测试。

## 背包图标修正 V2

此前目录兜底 PNG 导出了带紫色缺材质和遮挡的 Blender 制作场景。该图片现改由标准 `ColdSteelWeaponIconCatalog -Definition=ue_runebound_warhammer` 制作，使用背包同一模块装配、原生 PBR、透明背景和正交竖幅：384×768、轮廓居中、主轴按共用 91% 规则取景，不对整把武器去色。实际 PNG 为 `Content/ColdSteelData/Icons/ue_runebound_warhammer.png`。

`SourceAssets/RuneboundWarhammer20261022/author_icon.py` 已改为上述定向作者入口，成功后同步 Export 源图，防止基础注册和重导重新复制旧图。动态背包捕获继续使用原有模块及配方缓存；本轮没有修改武器、技能、模型、动画或 UI 布局。旧图、旧作者入口和旧 UI Texture2D 保留于 `InventoryIconV2/Before`，实际图像制作与 Texture2D 保存分别记录于该目录的回执。未运行游戏或验收测试。

最终 PNG、作者 Export 和已有 UI Texture2D 均已更新。用户授权结束当前 PIE 以保存图标后，定向重导实际保存成功，UI 资产采用 EditorIcon、sRGB、NeverStream、NoMipmaps；编辑器保留，没有重开游戏。此次未修改原生代码，无需 C++ 重编译。
