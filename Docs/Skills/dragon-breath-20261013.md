# 龙息：法杖限定终极魔法

用户要求新增龙息，使用新导入的喷火资产，前方 90° 扇形每 0.5 秒伤害一次；等级成长半径 5–15 米，配套卡片、详情与群体修炼，并在完成后检查遗漏。

## 规则与成长

20 级，所有数值真源为 `Content/ColdSteelData/skills.json:dragonBreath`。设 `K=等级−1`、`G=K/19`：

- 半径：`500 + 1000×G` cm，固定总夹角 90°，随瞄准朝向转动。半径不受装备施法距离词条扩大，以保持用户指定的 15 米上限。
- 每跳基础伤害：`floor(30 + 5×K + 魔攻×(0.90 + 0.08×K))`。沿现有火系入口叠加法杖／施法器倍率、火系与魔法词条，再走目标魔防、穿透与随机暴击；不单独叠加智力，不使用要害暴击。
- 持续：`6 + floor(2×G)` 秒；每 0.5 秒一次，起始首跳、持续终点不额外结算，共 12–16 跳。
- 基础耗蓝：`160 + floor(60×G)`；基础冷却：`45 − floor(7×G)` 秒。现有减耗、冷却、链式与魔法书施法速度规则继续应用。
- 以持续持杖施法作为代价：起手预扣一次，接触喷出时确认并启动冷却；释放前取消退回实际扣款，释放后中断不退款。切武器、死亡、受控、捕获或优先动作停止喷吐。
- 伤害检测有独立高度厚度 `±(80 + 前向距离×0.28)` cm，围绕瞄准平面展开，避免无限 Z 轴柱体；完整墙和楼板阻挡。真实孔洞、独立可穿透栏杆沿 `MagicOcclusion` 规则。

| 等级 | 半径 | 每跳基础伤害 | 持续 | 蓝耗 | 冷却 |
| --- | --- | --- | --- | --- | --- |
| 1 | 5.00 m | 30 + 0.90×魔攻 | 6 s | 160 | 45 s |
| 10 | 9.74 m | 75 + 1.62×魔攻 | 6 s | 188 | 42 s |
| 20 | 15.00 m | 125 + 2.42×魔攻 | 8 s | 220 | 38 s |

表内为基础配置，实战及面板由同一快照函数读取当前装备加成。该组数值是首版平衡设计，尚无游戏平衡验收。

## 修炼

每跳每个有效目标 +1 XP，直接击杀 +8 XP；某一跳命中至少两只可修炼目标，整次额外 +6 XP；同次直接击杀至少两只，额外 +12 XP。群攻／群杀奖励各只发一次，技能结束汇总；空放、尸体、友方、召唤物和后续附加灼烧击杀不计。死亡、离场丢弃未结束修炼。升级需求为 `150×当前等级`，最高 20 级；随机暴击同时沿原暴击修炼入口。

## 美术、动作与成本

当前制作路线为 Niagara Fluids Volume V8（2026-10-14），源与实际落盘状态见 `SourceAssets/DragonBreath20261013/VolumeV8_20261014/production-notes.md` 及同目录 `delivery.json`。用户已否定 V7 龙息效果，并指定参考 RedefineFX 喷火器课程；原火球和篝火仍属认可效果，不修改。新版运行引用为 `/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume`，使用 Epic `Grid3D_Gas_SimpleParticleSource` 的三维温度／密度／速度场及 Niagara Volume Renderer。可见火焰不再由 Sprite 火片组成。

V8 保留 90° 玩法扇形，70% 热源集中在约 15° 的中心喷流，其余向外围展开。不可见热源 360/s，最长寿命 0.8 秒；它们只注入流体，不绘制火焰。每位施法者至多一个流体组件，网格尺寸随 5–15 m 射程调整；本地画质对应最长轴 80/96/128/160/160 格，远端为 80 格，属性网格倍率为 1，压力迭代 8 次，体积步长倍率 0.75。停止施法后 0.65 秒显示淡出，不再造成伤害；死亡与 EndPlay 立即清理。上述为制作预算，不是实测帧率或显存承诺。

网格启用运动补偿，喷口沿既有同帧杖尖和瞄准朝向，流体域中心位于射程的 46% 处。9 条方向射线每 0.1 秒约束热源行程；气体使用全局距离场碰撞，伤害仍独立采用身体多点与实体遮挡。距离场与方向采样属于表现近似，不能宣称所有动态或薄壁几何均得到精确绕流。没有全局改变项目光照、纹理池或其他火焰。

V5/V6/V7 保留为历史与恢复源，不再从当前作者入口生成。V8 入口 `Tools/Skills/build_dragon_breath.py`，核心作者 `build_dragon_breath_volume.py` 和 `dragon_fluid_source.py`，在专用 `AuthorHost/DragonBreathAuthor.uproject` 中后台执行；普通编辑器没有该制作模块时，不应直接运行此脚本。制作宿主已配合正式项目使用 DX12/SM6、体积渲染和距离场设置。

本地喷口取同帧持杖施法末端，使用已有持杖前挥及 `ContinueSpellRelease` 保持喷吐，结束回收。共用手势占用与优先中断。远端复制激活时间及施法快照，由服务器判定伤害与奖励；客户端不结算伤害。

六边金属龙首喷火图标为本轮生成，已保存 `Content/ColdSteelData/Skills/dragon_breath_hex.png`；原图及恢复副本在 `SourceAssets/DragonBreath20261013`，加入 `Tools/UI/prepare_cold_steel_skill_icons.py`。不对第三方资产作公开提交或许可转让。

## 接入检查记录

- 定义／伤害快照／耗蓝共用 FireMagic 家族入口；半径独立线性插值，界面读取同一函数。
- 技能页全部／主动／魔法列表、卡片图标、点击详情、拖拽捕获、拖影、返回焦点、当前与下级效果、MAX 和修炼卡片已接入；布局沿冷钢标准，规划 `Docs/UI/dragon-breath-plan-20261013.md`。
- 快捷栏验证、绑定、按键施放、缺蓝置暗、法杖提示及冷却环复用 FireMagic 分支；补入 F6 调级目录和技能升级通知。
- 存档反射字段与技能版本 22，版本 21 只补新技能及冷却项，不重置上挑等旧项。释放前保留实际扣蓝记录，读档退款并清理预留；已释放冷却继续保存，活动喷火不恢复。
- 服务器技能白名单、阶段请求、伤害、复制表现、成功／拒绝回执、预留超时与取消 RPC 已接入；权威端再次验证法杖。
- 添加专用 Cook 目录；原材质及纹理通过 Niagara／材质引用进入依赖。PNG 沿已有技能 UFS 目录打包。
- 定向制作入口 `Tools/Skills/build_dragon_breath.py`，原资产读取记录 `SourceAssets/DragonBreath20261013/source-topology.json`。所有资产必须实际编译保存后才算交付；仅作者脚本不算。

## 交付状态

2026-10-14 Volume V8：三维流体资产已实际保存，Game 与 Editor 正式构建均已完成。当前重建入口和运行引用已切到 Volume V8，下一次启动编辑器使用新版。回执 `SourceAssets/DragonBreath20261013/VolumeV8_20261014/delivery.json`；本轮没有启动游戏、PIE、截图、渲染或性能验收，实际观感交由用户试玩。以下保留先前版本的历史交付记录。

源码、PNG 与五个 UE 资产已落盘。特效通过本次独立 Editor-only AuthorHost 后台制作，`Saved/DragonBreath20261013/author-assets-r4.log` 退出码 0；Niagara 编译记录 `valid=1, pending_after=0`。资产清单为 `SourceAssets/DragonBreath20261013/asset-authoring.json`。

按本轮用户要求，用 `Tools/Skills/inspect_dragon_breath.py` 重新读取已保存资产，核对三个发射器、无限循环、全部运行参数、材质指向、移除逐粒子碰撞及 1/10/20 级配置；`Saved/DragonBreath20261013/asset-review.log` 退出码 0，结果保存 `SourceAssets/DragonBreath20261013/integration-review.json`。

代码检查补齐了法杖限制、释放前退款、持续动作占用、伤害权威、重复目标去重、旧档迁移、快捷栏与 Cook 目录；详情说明改为读取配置，释放帧补上死亡／受控复核，特效在组件更新后使用同帧喷口。

最终 `FPSGAMEEditor Win64 Development -NoUBTMakefiles` 后台构建退出码 0，`Saved/DragonBreath20261013/Editor-final.log` 记录 `Target is up to date / Result: Succeeded`。主 DLL 已由共同构建更新到 2026-10-13 11:10:41，晚于本次最后源码改动；龙息运行时和技能 UI 对象分别于 11:07:24、11:07:08 编译。此前并行修改造成的编译阻塞已解除，本轮没有修改那些无关联机／地形实现。

本轮检查不包含启动 GUI 编辑器、PIE、游戏截图、联机实机或帧率测试；这些不因源码与资产编译成功被宣称已通过。

## 2026-10-13 火焰不可见修复 R2

用户反馈持续施法和扣蓝正常，但没有火焰。定向读取 Niagara CPU 粒子缓存发现，原版在 0.35 秒有 60 个火焰粒子、11 个小火星、3 个大火星，位置与尺寸正常，但采样颜色全部为 `(0,0,0,0)`。末尾自定义赋值在写入 `Particles.Color` 时又读取该输出，令颜色与透明度清零。

制作脚本移除了这条颜色自引用赋值，将寿命、遮挡距离与施法强度的透明度计算放入原 `ScaleColor` 模块，保留素材的 RGB 颜色配置、火焰材质及子图动画。每帧基于初始颜色计算，不累计乘以前一帧透明度。另取消制作脚本对插值生成标志的单独覆盖，避免标志与生成脚本类型不一致；加载后的现有脚本已重新编译保存。

通过现有编辑器桥保存了五个龙息资产，版本 `DragonBreathVisibilityR2_20261013`。编译返回 `valid=1, pending_after=0`；无需原生 C++ 构建。备份与 SHA-256 清单在 `trash/DragonBreathVisibility20261013/receipt.json`，资产保存回执在 `Saved/DragonBreathVisibility20261013/apply-01.json`。

同参数定向粒子复查：0.35 秒的粒子数量相同，火焰 RGBA 恢复为 `(1,1,1,1)`，火星恢复素材发光颜色 `(50,12.7954,0)`，透明度随寿命正常变化。前后缓存记录为 `SourceAssets/DragonBreath20261013/VisibilityFix/simulation-before.json` 和 `simulation-after.json`。探针只在现有编辑世界创建临时组件，随后销毁；没有启动 PIE、另开编辑器或保存场景。此记录证明粒子颜色问题已修复，实际玩家施法的视觉效果仍交由用户测试。

## 2026-10-13 火焰主体恢复 R3

用户实机截图证明 R2 只修复了可见性，画面仍以黑烟和火星为主。重新读取 Fab 原包后确认：`MI_TrailSmoke` 的父材质 `M_Smoke` 是 Default Lit、没有 Emissive 接线；前版将它命名为 `M_DragonFlame` 并没有产生真正火焰。原示例地图另外引用了有发光接线的地面燃烧材质，之前的“只复制 Niagara”漏掉了这一表现层。证据在 `SourceAssets/DragonBreath20261013/FlameRestoreR3/materials.json`、`flame-layer.json` 及本地材质导出，不以发射器名称判断火焰完整性。

R3 作者 `Tools/Skills/build_dragon_breath_flame.py` 使用原包 `T_TiledFire` 制作空中火焰材质：格内 UV 还原后独立平铺流动采样、原子图 Alpha 轮廓、软边与深度淡出、Unlit 自发光和一次曝光补偿。主体按速度朝向拉长为 1.65 倍，在最后 30% 寿命转成低透明度尾烟；火星尺寸、发射量与过高亮度下调。不会改动 90°、等级范围、伤害频率、耗蓝、法杖条件和修炼。

R2 二进制备份及 SHA-256 记录保留在 `trash/DragonBreathFlameRestoreR3_20261013/receipt.json`。用户停止试玩后，检测到编辑器也已退出，因此使用已有 AuthorHost 在后台完成材质着色器与 Niagara 编译、五个资产保存；`Saved/DragonBreathFlameRestoreR3/author-assets-r3.log` 退出码 0，Niagara `valid=1, pending_after=0`。材质和系统分别于北京时间 18:13:44、18:14:00 落盘。

重新从磁盘读取后确认 Unlit、单次曝光补偿、`T_TiledFire` 火焰纹理、主体材质绑定、8×8 动态轮廓与速度对齐均已保存；`Saved/DragonBreathFlameRestoreR3/read-saved-r3.log` 退出码 0，结果为 `SourceAssets/DragonBreath20261013/FlameRestoreR3/saved-material-binding.json`。没有启动 GUI 编辑器、PIE 或执行画面验收；实际喷流观感交由用户确认。

## 2026-10-13 新生巨片与喷流 R4

用户截图仍有占据右侧屏幕的巨型火纹平面。定向读取发现主发射器的 InitializeParticle 沿用原烟片 250–300 cm 随机尺寸、0–360° 随机旋转；R3 只在更新栈覆盖尺寸。CPU 粒子出生帧先以原始巨大尺寸在右手喷口显示，下一帧才缩小，持续发射时每帧都存在巨片。

`JetFixR4/particles-before.json` 记录了 5 m／15 m、0°／90°／233° 三组实例：出生粒子 Age=0，尺寸 253–296 cm；已有粒子左右分布相等，实际角度约 −44.18° 至 +44.63°。因此已证明本次基础扇形计算包含左右两侧，截图中的单侧表现不能由“仅生成一侧粒子”解释。

R4 同时写入出生和更新两阶段的尺寸、零旋转、UV 比例及子图帧。出生尺寸 6×10 cm；主体宽度按实际飞行距离增长 `min(130,6+距离×0.20)`，长度为宽度的 1.8 倍。以真实动态火舌图集替换地面平铺火纹，AlphaComposite 发光在最终透明度后预乘，出生淡入和 18–45 cm 近镜头淡出消除贴脸平面。火星保留 1×1 图集帧 0，避免误用主火焰的 8×8 帧索引。施法／伤害／范围／遮挡规则不改。

R3 资产和作者脚本恢复副本、SHA-256 清单在 `trash/DragonBreathJetFixR4_20261013/receipt.json`。用户停止试玩后，原编辑器发生 DynamicWind／RenderCore 访问异常并退出，本轮新资产尚未写入；错误现场保留在 `Saved/DragonBreathJetFixR4/editor-exit-context.log`，没有修改该插件或主动关闭编辑器。

随后通过现有独立 AuthorHost 后台保存五个资产，`Saved/DragonBreathJetFixR4/author-assets.log` 退出码 0，Niagara `valid=1, pending_after=0`；主材质和系统于北京时间 19:12:25、19:12:35 落盘。构建图表期间有旧输出尚未接通的临时 ComponentMask 警告；重新读取最终保存材质后，编译错误列表为空，真实输出链只引用动态火舌图集，并确认出生尺寸 `float2(6,10)`、旋转 `0`、UV 比例 `float2(1,1)`。结果在 `JetFixR4/saved-asset-checks.json`。

修复前的三朝向实际粒子采样已完成；修复后的独立 commandlet 没有产生可读取的模拟数据，`probe-after*.log` 中的 `No particle data` 属后置探针未完成，不能标记为粒子复测通过。未重新开启 GUI 编辑器或运行游戏，玩家画面及实际喷流观感仍待用户测试。

## 2026-10-13 更换为 Realistic Jet V5

用户明确否定 R4 并要求换一种火焰。新作者 `Tools/Skills/build_dragon_breath_realistic.py` 从喷火器源取得完整 `M_Fire_C`（6×6）和 `M_Spark_A`，复制为独立 `M_DragonNativeJetV5`、`M_DragonNativeSparkV5`，保留其 SubUV、噪声、动态偏移和透明度指数，只适配曝光、出生及近镜头淡入、接触软边。旧 `build_dragon_breath.py` 改为当前制作入口，防止后续重建恢复被否定版本。

四层为 `JetSource / JetCore / JetRoll / JetSparks`，分别使用短而紧凑的喷口、向前输送的火焰主体、放缓并翻卷的外层，以及少量火星。采用左右成对发射和独立粒子翻卷相位，主体沿完整 ±45° 范围展开；白黄火核渐变至橙红尾部。原始源的蓝光极高数值、浓烟、光源与折射层没有直接照搬。出生阶段即写好小尺寸和零 Alpha，更新阶段显式计算颜色，保留之前已明确的出生巨片与自引用颜色修复。

本轮只替换视觉，90°、5–15 m、每 0.5 秒伤害、法杖限制、耗蓝、冷却、修炼和存档不改。退役版本及作者恢复副本在 `trash/DragonBreathRealisticJetV5_20261013/receipt.json`。原素材读取与正式保存回执位于 `SourceAssets/DragonBreath20261013/RealisticJetV5`；不因脚本写完宣称已保存，实际落盘状态见制作回执。

本轮停止试玩后编辑器再次发生 DynamicWind 渲染线程访问异常，现场保留在 `Saved/DragonBreathRealisticJetV5/editor-exit.log`。改用独立 AuthorHost 完成后台制作；首次 Niagara CPU VM 不支持 HLSL `smoothstep`，作者已改成等价三次多项式。最终 `Saved/DragonBreathRealisticJetV5/author-final.log` 退出码 0，Niagara `valid=1, pending_after=0`，两份材质与四层系统于北京时间 22:33:16–22:33:28 保存。正式回执 `RealisticJetV5/delivery.json` 标记 `assets_saved`。本轮未启动游戏、渲染预览或追加验收测试，观感由用户确认。

## 2026-10-14 连续喷流 V6

用户要求继续向火焰喷射器效果优化，没有选择缩小技能范围，因此保留 90° 伤害和外围表现。V5 虽设为世界空间，位置却每帧引用当前 `User.Origin/Forward/Side/Up`，旧火焰仍跟随玩家整体平移旋转；同时主火流完全铺满 ±45°，无法形成集中的连续主体。

V6 在出生时保存喷口世界位置、方向、横轴／纵轴、飞行速度、终点与阻挡法线。更新只读取这份粒子自身快照，新的杖尖姿态只影响新粒子。中心约 19.8°，速度 18 m/s、沿速度拉长、取消随机旋转；外围仍为 90°、15 m/s、低一些的 Alpha 并保留翻卷。距离成长通过飞行寿命扩展，喷口保持小尺寸。材质沿用 V5 原生材质，不再仅换图。

出生遮挡取已有九条射线的最近方向，在对应墙面平面上求交；到达后限制前向位移，扰动投影至墙面切向，约 0.08 秒内消散。它是出生时采样的表现近似，粒子存活期间不追踪后续新移动过来的障碍物；服务器伤害仍实时按原规则独立检查。保留完整楼板／墙和已有镂空规则。

运行时新增 `User.EmissionScale`，将生成数量与已存在粒子的透明度分开。停止施法立即停止发射／伤害／动作，已存在粒子继续运动并在 0.35 秒内淡出；最多保留原单个组件，新施法替换旧尾焰，死亡、读档清理、EndPlay 强制销毁。首次激活前先写入射线和法线，避免前几帧从墙另一侧喷出。固定包围盒余量增至范围 +600 cm，容纳移动过程中的短尾。

制作入口保持 `Tools/Skills/build_dragon_breath.py`；V5 恢复副本及 SHA-256 清单在 `trash/DragonBreathFlowV6_20261014/receipt.json`。本轮按用户规则只做开发、资产编译保存和必要原生构建，不追加游戏测试、粒子探针或截图。实际落盘回执位于 `SourceAssets/DragonBreath20261013/FlowV6_20261014`，构建日志位于 `Saved/DragonBreathFlowV6_20261014`。

本次 `FPSGAMEEditor Win64 Development` 后台构建退出码 0，`Editor-build.log` 记录 `Result: Succeeded`，编辑器模块 DLL 于北京时间 2026-10-14 08:28:23 更新。随后独立 AuthorHost 的资产制作进程退出码 0，`author.log` 记录 Niagara `valid=1, pending_after=0`，两份材质与 `NS_DragonBreath` 已实际保存；系统落盘时间为 08:29:30。`FlowV6_20261014/delivery.json` 标记 `assets_saved`。这些记录仅证明构建与保存完成，不代表游戏画面、多人表现或性能已验收；本轮未运行游戏。

## 2026-10-14 用户要求自行检查：V6 R1

本轮用户明确要求自行检查。新增隔离 AuthorHost 的 `DragonBreathReview` commandlet，创建临时预览世界并显式初始化其 FXSystem，采集实际 Niagara CPU 缓存和离屏画面；不打开 GUI、PIE，不保存场景。先前 Python commandlet 无粒子数据的原因是引擎默认不为 commandlet 世界创建 FXSystem。首次新探针的组件回收次序触发 rooted-object 断言，已在探针内部修正为先解除 root、注销，再销毁，随后完整采样进程正常退出。

检查发现 V6 快速转向时，插值生成会使新粒子的方向向量长度降至约 0.72–0.80，实际速度和距离随之缩水。R1 将插值后的方向归一化，并加入少量纵向展开；旧粒子的出生位置／方向快照保持不变。离屏画面还显示主火流偏暗、细碎，因此提高喷口与主体的黄白亮部，降低主体材质的侵蚀参数，保留外围橙红翻卷。发射率仍为 244/s，90°、5–15 m、伤害和耗蓝规则不变。

重建期间另发现一个制作流程问题：增量编译可以返回 `valid=1`，但系统 VM 漏掉 `JetSource.ExecutionState`，喷口在运行中变为 Disabled、生成数为 0。仅靠资产拓扑检查无法发现。完整重编后恢复，因此给现有 `CompileRain` 接口增加可选 `bForce=false` 参数，保持其他调用默认行为；龙息作者在保存前显式传 true。隔离宿主与正式编辑器接口同步支持此参数。

最终版本 `DragonBreathFlowV6R1_20261014` 的系统于北京时间 09:11:21 实际保存，`author-final.log` 退出码 0；正式编辑器构建成功，DLL 于 09:10:57 更新。最后独立进程从磁盘加载、不指定 ForceCompile，`final-readback.log` 直接读取到喷口运行状态，四层均正常生成。`check_dragon_breath_samples.py` 的 34 项检查全部通过：5 m／15 m、左右覆盖、新生尺寸和有限值、转向后旧轨迹保持与新粒子速度、停火后不新增粒子、0.35 秒透明度归零、采样墙面前的粒子中心截止。采样墙面是传入的固定遮挡平面，不等同于已运行玩家的真实场景碰撞。

证据目录为 `Saved/DragonBreathReviewV6_20261014`：`particles-before.json`、最终 `particles.json`、`checks.json`、5 m 第一人称近似视角、5 m／15 m 侧视图及固定墙面图。只完成了 VFX 离线模拟和实际离屏渲染；未做实际关卡施法、伤害数值实战、多人同步或性能验收。生产备份在 `trash/DragonBreathReviewV6_20261014/receipt.json`。

## 2026-10-14 认可火球／篝火来源 V7

用户明确表示现用火球火焰很好、篝火也可以；不要求统一所有火焰，后续在认可素材上开展。该认可只覆盖原火球和篝火，并不代表下述龙息派生版已经通过观感验收。

新作者 `Tools/Skills/build_dragon_breath_accepted.py` 复制完整的现用火球连续内核材质和篝火火焰材质到龙息自己的 `AcceptedV7` 目录。火球内核保留既有噪声、原创燃烧场、暖色温、唯一曝光补偿和 AlphaComposite 预乘；仅在副本加近镜头／出生淡入，预乘颜色和透明度同步处理。篝火保持 8×8 原生解码、正方形贴图比例及动态侵蚀参数，按粒子秒龄播放，避免技能距离改变时整个动画被高速压缩；没有把 6×6 的旧喷火材质套进新图集。少量火星复制篝火原生 `M_Spark`，保留其不使用半透明 Opacity 输入的材质结构。

喷口、连续主体、外层火舌、火星分别为 24／144／64／4 个每秒；主体提供持续覆盖，外围仍沿原 90° 伤害范围分布。世界空间出生快照、方向归一化、墙面截断、0.35 秒停火余焰和全部技能数值沿现有实现。火球、篝火系统及材质只读，来源散列记录在 `SourceAssets/DragonBreath20261013/AcceptedV7_20261014/accepted-source-sha256.json`；V6 生产恢复副本在 `trash/DragonBreathAcceptedV7_20261014/receipt.json`。

正式重建入口 `Tools/Skills/build_dragon_breath.py` 已切换到 V7，资产可选检查工具的材质预期也同步更新。后台 AuthorHost 完成三份专用材质及原路径 Niagara 系统保存，`author-final.log` 记录 `valid=1, pending_after=0`，保存标记时间为北京时间 12:34:31。完整制作回执为 `SourceAssets/DragonBreath20261013/AcceptedV7_20261014/delivery.json`。没有修改 C++，无需重新构建游戏模块。本轮没有追加粒子测试、渲染、GUI 编辑器或游戏试玩；V6 的 34 项检查不能视为 V7 的测试结果。

## 2026-10-14 体积喷流 V8 与方向／显示 R1

龙息已使用 Niagara Fluids 三维网格及体积渲染，运行路径为 `/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume`；V7 为被用户否定的历史版本。V8 的资产与 Game／Editor 构建已完成，原始制作记录在 `SourceAssets/DragonBreath20261013/VolumeV8_20261014/production-notes.md`。

针对随后反馈的反向／不可见问题，R1 取消混用世界速度与局部索引的 streak 偏移，使用有效的非插值出生设置，增加独立的局部网格 RG 温度材质及单次曝光补偿。三个朝向的 GPU 数据证明热源朝前且存在温度，没有将玩法瞄准方向反转。系统和两份材质已于 14:44 保存，完整 Niagara 编译成功；重建作者同步。本次不改技能数值或游戏 C++。详细证据、局限和回执见 `SourceAssets/DragonBreath20261013/VolumeV8R1_20261014/repair-notes.md`，实际视觉仍待用户试玩。

## 2026-10-14 主体暖色 V8 R2

用户反馈主体过白并授权优化。R2 专用体积材质以实际 G 通道温度独立映射 0.35–160 的暖色曲线，使用暗红／橙红／橙黄／金黄／暖浅黄过渡，取消中性纯白端点；主体发光增益由 0.8 调整为 0.4。保留现有透明度、密度和单次曝光补偿，因此不会因扩大颜色温度范围同时降低火柱的透明度厚度。运行系统路径不变，改绑 M_DragonVolumeFlame_R2 / MI_DragonVolumeFlame_R2；作者与 HLSL 已保存。

2026-10-14 16:18:42 后台保存完成，制作 commandlet 退出码 0，Niagara valid=1、pending_after=0；两份材质编译完成。本轮未修改游戏 C++、技能玩法，也未执行游戏／PIE／GPU 回读／画面或性能验收。具体参数与制作记录见 `SourceAssets/DragonBreath20261013/VolumeV8R2_20261014/production-notes.md`，正式回执为同目录 `delivery.json`，最终观感由用户试玩确认。
