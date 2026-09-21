# 巫婆 V05：保留原裙的分件调整

历史记录：本版本含错误适配的内部身体，已由 [CleanRobeV06](CLEAN-ROBE-V06.md) 修复替代。当前制作和导入使用 `clean_robe_v06.py` / `Tools/Witch/import_clean_robe_v06.py`；下文旧脚本用于追溯，不再作为当前 F6 模型的重建入口。

2026-09-20。按用户反馈保留 Meshy 原裙外形，在现有模型上拆分制作，不重新调用模型生成服务。V04 的可见重建裙只作为历史候选保留。

## 可编辑资产

- 母版：`Authoring/CloudGripV02/Witch_GripBodyV02.blend`，原 Meshy 24 骨与局部修正的左手握杖。
- 未切分原始资产及原 PBR：`Authoring/LayeredV04/Preserved/Original_Uncut.blend` 与同目录素材。
- 新组合源：`Authoring/OriginalRobeV05/Witch_OriginalRobeV05.blend`。
- 独立部件：`Authoring/OriginalRobeV05/Parts/` 内帽、头发/头、左右手、上袍、原下袍、原脚、隐藏内腿/小腿、模拟代理，各有 Blender 源与 FBX；没有腰部重复骨架。
- 最终导出：`Delivery/OriginalRobeV05/` 内一个骨骼模型和五段动画 FBX。
- 作者脚本：`original_robe_v05.py`，复用 `layered_v04.py` 的拆分、原动画读取与导出工具。

原裙显示网格保留源面的顶点位置、UV、分裂法线、褶皱、开口和破边；更改的是部件归属、材质槽及蒙皮权重。材质复制原身体 PBR 节点与贴图，不采用 V04 投影到规则裙面的贴图。原脚按足部区域、源皮肤纹理和相邻面切出，继续使用原 UV/PBR；其蒙皮单独归属脚踝/脚趾。隐藏腿膝和小腿沿用本地 Quinn/护士素材，材质统一为深暗内衬。实际切分面索引保存在 `body_manifest.json`。

## 原裙与隐藏模拟网格

`Witch_OriginalRobe_Render` 为可见原裙；`Witch_Robe_SimProxy` 为 1984 顶点的独立模拟代理。代理贴合原裙大轮廓并仅平滑自身，用于 Chaos 布料计算。

用户反馈双层裙后，排查确认当前作者源及 FBX 不含 V04 的可见 `RobeCloth`，但 V05 导入网格中仍有 `SimProxy` 区段并分配身体材质。旧接入调用的 UE `RemoveMeshSection` 实际仅禁用区段，不删除源几何；此前“已移除区段”的描述不准确。现将提取用的 `SK_Witch_OriginalRobeV05_ClothBuildSource.fbx` 与最终 `SK_Witch_OriginalRobeV05.fbx` 分开。后者完全排除代理对象，布料提取/绑定后以最终 FBX 重导入，保留原裙布料数据和原材质。原始母版及历史候选继续保留；代理只留在作者源与布料提取输入中。

本轮针对反馈的排查结果：UE 渲染区段由 5 个减为 4 个，`SimProxy` 材质槽及对应区段已消失；最终 FBX 有 9 个显示部件，没有代理对象。原裙 `Witch_OriginalRobe_Render` 仍为 50202 顶点。证据为 `Saved/WitchV05-skirt-sections-before.json`、`Saved/WitchV05-skirt-sections-after.json` 与 `Saved/WitchV05-source-geometry-after.json`。

用户关闭占用后，已完成布料数据去重和绑定保存：修复前两份布料记录、原裙区段无有效绑定；现在只保留 `Witch_OriginalRobe_ChaosV05_0`，绑定到 LOD0 的原裙区段 3，其他三个区段不绑定布料。使用 UE 自带的标准编辑器绑定工具同步 `UserSectionsData`，不再仅修改临时区段。制作结果记录在 `Saved/WitchV05-cloth-binding-repair.json`。渲染区段仍为 4 个，没有重新导入代理几何；动态效果未试玩。

`Tools/Witch/repair_v05_cloth_binding.py` 已执行并接入 `import_original_robe_v05.py` 的激活流程：已有模拟数据直接复用，绑定经标准工具保存，避免再次提取生成重复数据。制作时用编辑器启动参数 `-EnablePlugins=ChaosClothAssetToolset` 临时加载引擎自带工具；没有修改项目插件配置，已保存的旧式 Chaos 布料在游戏运行时不依赖这个编辑器工具插件。本轮为资产与 Python 制作流程修复，没有新增原生编译。

腰部固定、下摆渐增自由度，多影响权重映射与平滑过渡；上袍腰带区域同步到骨盆，避免上下层分别驱动切口。布料具备腿/足胶囊碰撞、自碰撞参数，角色开启环境布料碰撞。原始显形褶皱不被重新拓扑或直接压成光滑网格。效果未经实机测试，不据此宣称已消除穿模。

## 动作分层

下身仍使用 UE 原生重定向的女性步态，3.2667 秒、基准约 22.3955 cm/s；保留源膝弯、摆腿及骨盆运动。上身为 V02 持物动作的独立制作层，在腰椎到胸肩逐渐混合，持杖侧权重更高。上身呼吸循环重采样为整个步态周期，移除旧方案中途按 2 秒取模造成的重新起播。

- `MotionLayers/Witch_LowerBody_Source.blend`：完整源步态层。
- `MotionLayers/Witch_UpperBody_Carry.blend`：同长度持物参考层。
- `Witch_Walk_OriginalRobeV05.blend`：混合后的交付动作。
- `motion_manifest.json`：分层骨权重、周期、帧数、速度；下身拥有根/骨盆运动。

两份源层保留完整骨架，作者脚本按记录的骨遮罩混合，最终烘焙为当前怪物系统使用的单段行走动画；不是新增两套运行时骨架。其余待机、施法、掷瓶、死亡仍基于 Meshy 云端动作。活体动作按原脚实际蒙皮后的最低点修正平地高度；死亡保留原后倒轨迹。不新增坡地脚锁/IK。原施法 0.535714 秒、掷瓶 0.75 秒与死亡 0.9 秒转布娃娃的业务时序保持原有实现。

## UE 接入记录

目标目录 `/Game/Monsters/WitchMeshy/OriginalRobeV05`，保留 V01–V04，独立骨架与 Physics Asset。接入脚本 `Tools/Witch/import_original_robe_v05.py` / `activate_original_robe_v05.py`，原生布料制作入口 `AWitchMonster::PrepareCombatPhysics`。

当前阶段：源模型和动作导出、UE 导入、原裙与隐藏代理布料绑定均已完成并保存。常规 `FPSGAMEEditor Win64 Development` 构建完成，日志 `Saved/BuildEditor/build-20260920-190749.log`；编辑器已正常重新打开，原生默认引用和当前编辑器 F6 默认值都切到 V05。实际保存阶段写入 `ue_original_robe_v05.json`。入口仍是 **F6 → 怪物生成 → 巫婆 → 在玩家前方生成**，沿用既有 `Witch` ID、导航和数量/清除逻辑。

本次按用户要求排查源网格、实际导入区段、F6 引用与布料绑定，不启动 PIE、截图或预览渲染；动作、抓杖、脚掌和裙摆动态表现交由用户测试。
