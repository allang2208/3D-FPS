# FPSGAME 流体接入地图与落盘

基线日期：2026-09-24。除个人技能位置外，下列路径相对 `D:/FPS3D/FPSGAME`。本页提供定位入口；实际引用变化时读当前源码，不因为历史作者入口存在就重跑全套。

## 按目标定位

| 类别 | 运行入口 | 制作入口与记录 |
| --- | --- | --- |
| 原生流体基础库 | `/Game/Fluids/Foundation`，目前是素材入口 | `Tools/Fluids/bake_mantaflow_foundation.py`、`author_foundation_ue.py`、`publish_foundation.py`；`Docs/Fluids/free-foundation-20260923.md` |
| 枪口烟 V15 | `Source/FPSGAME/Weapons/FPSWeaponFXComponent.*`；`Characters/FPSPreloadAssetRegistry.gen.h` | `Tools/Fluids/bake_muzzle_smoke.py`、`author_muzzle_smoke_v15.py`；`Docs/Fluids/muzzle-smoke-v15-20260923.md` |
| 火球燃烧内核 | `Source/FPSGAME/Skills/FPSFireballProjectile.*`；现用 `M_FireballCohesiveCore` | `Tools/Fluids/bake_fireball_core.py`、`apply_fireball_fluid_core.py`；`Docs/Fluids/fireball-fluid-core-20260923.md` |
| 陨星／焰甲燃烧场 | `Skills/FPSMeteorStrike.*`、`FPSFireMagicComponent.*`；`/Game/Skills/FireMagic20260921/RealisticV5` | `Tools/Fluids/apply_fire_magic_fluid_fields.py`；原作者 `Tools/Skills/build_fire_magic_realistic.py`；`Docs/Fluids/fire-magic-fluid-fields-20260923.md` |
| 爆燃烟、毒雾、腐液 | 上述火系入口及 `Monsters/PoisonMaggotVenomFX.*` | `Tools/Fluids/author_impact_smoke_corrosion.py`；`Docs/Fluids/impact-smoke-corrosion-20260924.md` |
| 水面／水花 | `WorldGeneration/RiverPilotFXSubsystem.*`、`WaterImpactFootprints.*`，均在 `Source/FPSGAME` | `Tools/Fluids/author_river_pilot.py`、`bake_river_splash_natural.py`、`author_river_splash_natural.py`；`Docs/Fluids/river-splash-natural-performance-20260924.md` |
| 全水体注册与水面覆盖 | 上述水面子系统、`Source/FPSGAME/Building/ColdSteelFountain.cpp`、`Dungeons/AuthoredDungeonGenerator.cpp` | `Tools/Fluids/export_water_footprints.py`、`generate_water_footprints.py`、`author_water_impacts_all.py`；`Docs/Fluids/all-water-impacts-secondary-20260924.md` |
| 毒液弹／巫婆毒池 | `Source/FPSGAME/Monsters/PoisonMaggotProjectile.*`、`WitchProjectile.*`、`PoisonMaggotVenomFX.*` | `Tools/Fluids/author_venom_projectiles.py`；`Docs/Fluids/venom-projectiles-witch-pool-20260924.md` |
| 风、涉水、击水蒸汽、统一预算 | `Source/FPSGAME/WorldGeneration/FluidPresentationSubsystem.*`；`Movement/FPSFootstepAudioComponent.cpp` | `Tools/Fluids/author_fluid_interactions.py`；`Docs/Fluids/fluid-interactions-five-20260924.md` |
| 烟雾接触／血液／冷雾／尾迹 | 共享流体子系统、`Source/FPSGAME/Weapons/FPSImpactFXSubsystem.*`、`Skills/FPSIceSpikeVolley.*` | `Tools/Fluids/author_fluid_polish.py`、`fluid_contact_nodes.py`、`water_wake_authoring.py`；`Docs/Fluids/fluid-polish-five-20260924.md` |

冰锥飞行冷雾原作者为 `Tools/Skills/build_ice_spike_frost_v2.py`，不要为了接入命中冷雾重建冰锥全部模型和动作。水面公共 HLSL 为 `SourceAssets/RiverPilot20260923/RippleField.hlsl`；尾迹和血液源在 `SourceAssets/FluidPolish20260924/`。网格轮廓变动时再重导出水面轮廓并构建，单纯材质调色不需要重导几何。

常用运行资产：

- 枪口：`/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeShotV15`、`NS_FPS_MuzzleSmokeStreamV15`，共用 `T_MuzzleSmokeMantaflowV14`。V14 是密度源；旧 V14 烟系统文档不再决定当前运行系统。
- 水花：`/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash`；自然图集 `/Game/Fluids/RiverSplashNatural20260924/T_RiverSplashPacked`；水冠 `M_RiverCrown` 保留修复。
- 三种表面：`/Game/Fluids/RiverPilot20260923/M_RiverPilot`、`/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWaterV3`、`/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_Dungeon_ShallowPuddle`。
- 毒液材质：`/Game/Fluids/VenomProjectiles20260924`；血液材质 `/Game/Weapons/GunplayFX/Impacts/Blood/M_FleshDropletV2`、`M_FleshStainV3`。
- 蒸汽：`/Game/Fluids/FluidInteractions20260924/NS_WaterImpactSteam`；冷凝命中雾 `/Game/Fluids/FluidPolish20260924/NS_IceImpactMist`；飞行冷雾 `/Game/Skills/IceSpike/FrostV2/NS_ColdMist`。

## 后台制作与已有编辑器

先写好本次目标清单、源修改、作者参数及保存回执路径，复用对应作者函数；批量作者通常会改多个资产，不能为单一调参盲跑整个历史脚本。导入一个 Python 文件前先读取其顶层入口，避免 `import` 意外执行全量制作。

未被现有编辑器占用的目标包，优先适用的 `UnrealEditor-Cmd -run=pythonscript -script=<绝对脚本路径>` 后台方式。读取目标作者对 RHI／编辑器子系统的要求：NullRHI 可以适用于部分资产构建，却不能据此宣称 GPU shader 或实际画面已经验收；交互编辑器专用 PIE 查询等 API 在 commandlet 分支应避开。

已有编辑器加载的资产使用现有桥。示意调用中的变量由本次实际任务指定，不照抄旧脚本去重制无关资产：

```powershell
& 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' `
  -PythonScript $fluidAuthorPath `
  -OutputFile $fluidReceiptPath `
  -MaxOutputChars 3000 -QueueWaitSeconds 240
```

目标包有未保存改动、PIE 正占用或写入结果不明时，保留现场，只向当前用户说明。批次互斥不覆盖任意外部进程，也不保证事务回滚；不能绕过桥或另起 commandlet 写相同包。退出码 75 表示等待超时且未发送请求，保留批次稍后重试，不高频轮询，不联系其他任务。

资产作者应只编译／保存目标包，保存调用返回结果进入本次回执；未知节点布局不静默清空图表。工具异步返回“已开始”时，沿其完成接口处理必要编译再保存，不能提前写“已完成”。端口或插件退出错误与资产保存结果分别报告，不能用完成标记掩盖非零退出码。

## 原生构建

源码有变更时，必要构建入口为：

```powershell
& 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1'
```

目标是 `FPSGAMEEditor Win64 Development`，日志在 `Saved/BuildEditor`。该脚本拒绝在项目编辑器／commandlet 占用时覆盖 DLL；不要绕过保护、杀进程或用旧 DLL／对象文件冒充新构建。短命后台制作结束后可再构建；确需用户关闭已有窗口时，先完成独立源码与资产准备，再在当前对话说明具体占用。

类／结构布局、反射属性或默认组件变化用常规构建，不依赖 Live Coding 修补。新类被资产作者引用时按依赖先构建，再制作资产；只有材质参数变化时不无故构建 C++。纯技能文档更新不连接 UE、不运行构建或验证器。构建后保持编辑器关闭，交由用户正常打开。

## 交付记录与后续标准更新

将本次实际发生的状态写入 `Docs/Fluids/<topic>-<date>.md`，引用本批唯一回执，不覆盖旧证据。至少清楚说明：

- 改变的效果、接入对象和未覆盖部分；受保护的玩法与已认可资产。
- 可编辑源、作者入口、导出通道／帧信息，以及实际保存资产清单。
- 运行预算与近似范围，哪些是理论估算，哪些有用户授权后的实测依据。
- 必要构建的真实结果和日志；待导入、待保存、待编译的部分单列。
- 用户反馈、历史证据与本轮测试分别记录；未测试就明确由用户测试。

第二轮五项有源码、10 个保存资产和 `build-20260924-154901.log` 构建记录，但没有运行／视觉／性能验收。第一轮文档中的“毒池生命周期内不更新轮廓”已被第二轮动态边界替代；早期“120 m 河流试点”也已被全水体接入替代。以后引用历史文档保留版本顺序。

技能标准新增经验时同步个人目录和工程镜像；实际资源仍留在工程，不复制到 skill 包。发布请求另遵守工程 `WORKFLOW.md` 的许可和精确提交规则，本工作流的创建／使用本身不触发 Git 发布。

### 归档与源码发布的经验（2026-09-24）

- 先按实际运行引用和作者依赖分类，不能按旧日期或“失败过”整目录搬走。V15 枪口烟仍使用 V14 密度；Foundation 的 SVT／液体缓存及专属 UEAuthoring 工程仍有重建用途；自然水花保留四套 FLIP 缓存、正常帧和空帧修复入口。它们不是废案。
- 确认被替代的 `Before*`／`Backup` 快照和有当前 `.blend` 对应的 `.blend1` 可移入 `trash/<task>/`，每文件记录原路径、归档路径、大小、SHA-256、原因及保留替代物。移动前校验绝对路径归属，移动后读回散列；不删除正式资产和有效输入。旧制作回执保留历史路径，通过归档清单定位迁移后的原件。
- 水花旧程序化形状 HLSL、V14 导入器和单项修复脚本是否可退役，由当前生成器读取／重建链决定；仅未被游戏直接加载不够。先保留仍被作者调用的中间输入，不为“目录整洁”破坏重建。
- 公开内容限已审阅的原创源码、作者脚本、HLSL、紧凑参数和文字记录；UE 包、Blender／Alembic／VDB、PNG／EXR、模拟缓存、材质图导出、传输回执、专属导入工程及 trash 保留本机。图集原创也不默认扩大本项目源码仓库的二进制发布范围。新目录用精确忽略／放行规则，不能把整个 SourceAssets 加入提交。
- 共享文件可能混有伤害、免疫、命中音效、矿材外观和地牢装配修改。发布流体时拆到改动块，保留其他工作树／暂存区内容。特别是水面注册钩子，不应顺带提交整份地牢生成器重构；必要依赖要随流体提交，不能留下未声明的新接口。
- 用户要求推送时按工程规则 fetch、审阅未发布提交与完整暂存差异，检查大小／许可／敏感信息及 `git diff --cached --check`，普通推送到授权分支后回读 SHA。推送检查不自动授权运行游戏或性能测试；此前共享工作树的成功构建不冒称为剥离其他改动后的提交独立重编译结果。
