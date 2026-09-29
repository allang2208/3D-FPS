# 手套与锁子甲源码、配方及经验发布

本次发布覆盖独立战术手套、黑色 V4、棕色露指／战术／钢甲细节家族，以及锁子甲 V2 环纹与当前内外层同步摆动。沿用物品 ID 和已保存外观，钢甲属性为防御 20、换弹速度 -10%、拉弓速度 -10%；速度 -10% 对应所需时间除以 0.9。

## 公开范围

- `Tools/ModularOutfit/` 的本次作者算法、烘焙、材质、原生派生、图标和保存／发布入口；原生骨架或纹理数据不内嵌到脚本。
- `FPSOutfitSecondaryMotion.*`、`SteelGauntletPoseNode.*` 及装备组件／动画代理的对应接入；武器换弹与弓拉弓速度、提示栏的装备加成。
- 物品与外观 JSON 只发布四款手套和锁子甲五个装备条目；战斗配置只发布钢甲条目。保留其他会话的文件及同文件未发布修改。
- 生产文档、手套材质／厚度／图标标准、分类几何预算、新增锁子甲表面与同步运动技能。个人 skill 与工程镜像同步维护。

## 当前家族和必须留在本机的依赖

| 装备 | 当前版本 | 保留依赖 |
| --- | --- | --- |
| 黑色皮革 | `BlackLeatherStitchWearV4` | `BlackLeatherDetail20260928` 的 ReliefCuffV2、TailoredSurfaceV3 与源图集 |
| 棕色露指 | `FingerlessDetail20260928` | 裁片手套原生蒙皮、各 UV 组与扫描皮革 |
| 独立战术 | `TacticalDetail20260928` | `OriginalLeatherV1/V2` 的原生派生、Body 与图集 |
| 钢甲 | `SteelDetail20260928` | `SteelGauntletV1` 连续外壳、灰钢衬底及原生姿态修正数据 |
| 锁子甲 | `ChainmailSharedSway20260929` | Interlace V2 原生几何、环纹材质、Body、图标；初版衣身／掉落形状；Relief 脚本辅助函数 |

完整工程恢复还需要项目既有的 V7 裸手、各武器原生骨架／动画和第三方素材。读取 [资源恢复](../AssetSetup.md)；公开源码不是可直接运行的完整资产包。

以下内容不随此次 Git 推送：UE `.uasset/.umap`、Blender/FBX、贴图与图标、源网格 JSON、骨骼权重、动作采样、缓存、日志和 trash。即便 JSON／INL 是文本，含授权模型／动画衍生的密集数据也按资产处理。

`Source/FPSGAME/Weapons/SteelGauntletPoseCurves.inl` 是钢甲姿态节点的**必要本地构建输入**，此次不公开；须从具备相应授权的完整工程备份恢复，或在已恢复原生动作与作者输入后运行 `solve_steel_temporal_pose.py` / `export_steel_pose_runtime.py` 重新生成。不能删掉此 include、给空曲线冒充完整恢复，或声称公开克隆已可独立构建。

扫描皮革来源沿用 `Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl`，元数据保留在家族作者目录。本次只公开自编制作逻辑，不包含原扫描或其他未核准再分发的第三方数据。

## 废案归档

本机 `trash/gloves-chainmail-20260929/` 保存 108 个文件、271,013,033 字节（约 258.46 MiB）：

- 用户否定的 `ChainmailCloth20260929` 资产、代理／作者源及 build/import/publish 入口、旧 C++ 作者实现。
- 被完整钢甲替代的单只 `RightSampleV1` 作者输出、UE 样件及导入入口。

逐文件路径、大小、SHA-256、原因与替代物见 [归档清单](gloves-chainmail-retired-manifest-20260929.json)。移动前限定工程与目标根，移动后文件大小与哈希全部匹配。历史设计文档保留并标明退役。

`build_metal_gauntlet_sample.py` 仍被最终钢甲作为几何函数库导入，保留；黑色 V2/V3、锁子甲 Relief/Interlace 仍是生产依赖，不能按日期清走。巫婆自身的布料代码和资产保持原状。

旧 `BuildChainmailCloth` 反射签名保留兼容，当前源码仅返回 false；失败的作者实现已归档。当前编辑器已运行，本轮整理未替换其 DLL、未重新构建或启动游戏；既有 DLL 的旧离线作者入口仅在后续常规构建时替换，当前装备已不调用该方案。

## 状态与发布边界

轻量锁子甲 21 份第一人称派生及共享材质已在此前完成后台保存，实际记录见 [同步摆动制作](../Characters/chainmail-shared-sway-20260929.md)。本轮是归档、技能沉淀和源码发布，没有重新导入资产、启动 UE、测试动作或测量帧率。

按 `WORKFLOW.md` 第 8 节检查远端、全部待推提交、精确暂存差异、空白错误、公开大小／敏感信息／授权数据边界，再普通推送 `HEAD:main` 并回读远端 SHA。结果与提交号由本次交付消息记录；不把这些仓库检查称为游戏验收。
