# M-25 涡电匣整理与源码发布（2026-10-05）

按用户授权发布到 `https://github.com/allang2208/3D-FPS.git` 的 main，遵循 WORKFLOW 第 4–8 节。只提交 M25 专用源码、共享入口中的 M25 增量、原创制作配方及技能经验；保留其他任务的工作区改动。用户明确要求地牢刷新后续再设置，本轮不修改地牢刷怪器／池，也不增加音效。

## 当前本机成果

用户已认可怪物主体及游戏网格优化。原 F6 涡电匣入口和 `BP_VortexCofferM25` 使用 `OptimizedV01/SK_M25_VortexCoffer_Game_V01`，LOD 三角形为 349998 / 119998 / 39996 / 9984，沿用 148 骨 UE 骨架、PBR、嘴部弱点和动画。移速 55 cm/s、转向 75 度/s、动画源速 16 cm/s。

近战物理与魔法独立：撕咬原片段 1.4 秒、播放倍率 2，基础物攻 65、CD 2.5 秒；闪电基础魔攻 60、倍率 1、CD 3 秒，雷枪倍率 2.5、CD 20 秒。背部电极特效使用 V02。最新 CombatFixV01 分离撕咬玩家接触与墙体遮挡，并使用归属玩家档案结算客机击杀奖励；本机 Editor/Game 均已构建成功，未进行本轮游戏测试。

## 公开边界

- 公开 `Source/FPSGAME/Monsters/M25*`、`VortexCofferM25.*`、共享 BT／受击／弱点／F6 中的 M25 增量，以及雷枪宽度与专用服务器视觉参数支持。其他怪物、装备、全局闪电淡入淡出和地牢刷新变更不夹带。
- 独立的全怪物连续软体死亡系统尚未在本次基线公开；本机 M25 已保留该系统的接入。公共 M25 保留原死亡动画通路，`TryStartSoftDeath` 的单行挂接以 [可恢复补丁](M25Integration/soft-corpse-hook.patch) 保存，待相应公共 API 发布后应用。未覆盖或回退本机运行源码、资产与原生二进制。
- 公共子集没有单独重新构建。本机 CombatFixV01 的构建结果不能替代公共子集构建或游戏测试。
- 用户提供的 Meshy 模型、参考图／生成三视图、PBR、完整几何／权重采样、Blend/FBX/GLB、UE Content、构建产物、生产回执与日志均留本机。未核准这些媒体的公开再分发许可；原创配方公开不意味着原素材许可转移。

## 归档

60 份已退役文件、5,317,644 字节移入 `trash/m25-retired-20261005`。包括各阶段改动前快照、未提交 TRELLIS 草案、过时 rig-only 状态、旧三视图分发 ZIP 与 Python 字节码。逐文件原路径、目标、大小、SHA-256、原因见 [归档清单](../AssetArchives/m25-retired-20261005.json)，移动后散列一致。

保留原高模、减面中间网格、正式低模及所有阶段作者。它们仍参与重建，不能按版本号判废。正式重建不读取 trash；生产脚本未来重新运行时可以重新生成当次备份。

## 本机恢复顺序

1. 恢复 `SourceAssets/M25VortexCoffer20261004/Inputs/Meshy_AI_Arcane_Maw_1004062246_texture.glb`、参考图、三个独立视图和 RigV01 的 fitted_positions.npy／fitting_inputs.json。拟合输入是早期制作保留数据，公开脚本并不从零重建该步骤。
2. `RigV01/author_rig.py` → Blender `package_blender_fbx.py`。保留原 Blend、骨架定义、权重、PBR 和独立 Idle/Crawl 动画源；骨名与当前攻击／弱点一致。
3. 常规 native 构建后，`UEV01/import_m25.py` 创建原骨骼网格、材质、动画及 AI/F6 蓝图。需要本机共享 BT 和大体型导航（复用 M10 的 225 cm 半径、450 cm 高度规格）。
4. `BackElectricV01/author_back_electric.py` 建立系统，再运行 V02 作者；V02 更新已有系统，因此 V01 作者仍是依赖。`AttacksV01/author_attacks.py` 配置魔法，`BiteV01/author_bite.py` 与 `import_bite.py` 制作撕咬，`HitWeakpointV01/author_responses.py`／`import_hit_weakpoint.py` 制作受击、死亡和嘴部查询形体；最后运行 BiteV02 数值、HuntingV01 和 MovementV02。
5. 最后执行 OptimizationV01 的 `reduce_master.py`、`export_reduced.py`、`import_and_bind.py`，复用原骨架与材质保存独立游戏网格、LOD 和原蓝图引用。FBX 导出需离屏 RHI；只设置 lod_settings 指针不足以应用参数，见对应 README 和技能参考。之前阶段会临时写回高模和旧数值，不要把单个旧导入器当最终安装入口。
6. 本机魔法与电流依赖 `/Game/Skills/Lightning`、`/Game/Skills/ElectricMagic` 及 `ThunderFluxV3`，作者调用已有 NiagaraToolset／RainAssetEditor。原 Niagara、材质与 S_LightningCast1 音频按原许可恢复，不包含在源码克隆中。
7. CombatFixV01 只改 native 逻辑，正常构建即可，无额外资产重导入。全怪物软体死亡的绑定与资产沿独立 `MonsterSoftCorpse20261005` 制作链恢复，不混入本次发布范围。

## 本次发布检查

本轮仅执行用户要求的仓库整理与推送检查：归档散列、精确暂存、完整暂存差异、空白错误、大小、敏感信息／许可边界、未推送历史以及远端 SHA 回读。未启动 UE、游戏、渲染或额外功能测试。实际提交与检查回执保存在本机 Publication20261005/Local。
