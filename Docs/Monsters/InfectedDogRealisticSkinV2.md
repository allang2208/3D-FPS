# 感染犬：写实裸皮 V2

> 2026-09-25 整理：下文保留当时制作/诊断记录，旧路径不再表示现役入口。当前模型、动作、归档映射和恢复顺序见 [感染犬发布记录](InfectedDogPublication20260925.md)。

用户于 2026-09-24 要求制定优化计划并实施。外观目标为低饱和病变绿色的裸皮犬科怪物，保留现有感染犬玩法和已恢复的旧犬科动画。

## 制作计划

1. 从原狼源模型重建无毛片身体。保留骨架、绑定、权重和身体拓扑，转移源自定义法线，按修形的局部变换调整法线；收细尾部和颈部蓬松轮廓，轻量修整肩胛及腹部体块。
2. 用静止姿态米制坐标制作颈部、关节褶皱、细皮纹、毛孔和轻微肤色变化，烘焙至独立 UV。保留突变体绿色皮肤的色彩来源，避免把毛发法线铺回裸皮。
3. 区分皮肤、鼻、眼、口腔、牙齿及爪垫的颜色、粗糙度和皮下散射。使用独立母材质，避免改变其他感染怪物的共享材质。
4. 导入独立 V2 网格、贴图及材质。感染犬蓝图与动画数据引用 V2 外观；保存原版本作为恢复点。现有 Run、转弯和攻击动画、六维属性、感染三个阶段继续沿用。

## 交付位置

- 可编辑制作源：`SourceAssets/InfectedDogRealisticSkinV2/`
- 工具：`Tools/InfectedDog/author_realistic_skin_v2.py`、`install_realistic_skin_v2.py`
- UE 资源：`/Game/Monsters/InfectedDog/RealisticSkinV2`
- 保持原入口：`/Game/Monsters/InfectedDog/BP_InfectedDog`，F6“感染犬”

纹理约定：BaseColor 为 sRGB；Normal 为 DirectX 切线空间；ORM 为线性 AO/Roughness/Metallic；SkinMasks 为线性皮肤/湿部位/薄组织遮罩。作者文件保留源 UV 与最终 UV；导出 FBX 只带最终 UV。

## 制作内容与来源

- 从原狼去除 4426 个毛片三角面，保留身体 3460 顶点、5679 三角面。原骨骼和身体顶点权重沿用，没有重新绑定。
- 保留源身体的连续自定义法线，按形变雅可比的逆转置搬运；导入 UE 时保留法线并由 MikkTSpace 生成切线。
- 尾部沿骨链径向收细并渐缩，颈部宽度按原颈骨权重轻收；腹部轻收、肩胛轻塑形。骨骼关节位置保持原位。
- 色彩/法线贴图为 4096，ORM/皮肤分区为 2048，启用流送。颈部褶皱深度约 0.58 mm，关节细褶约 0.30 mm，胶原细纹约 0.058 mm，毛孔约 0.03 mm；均为制作参数，不代表已经过近景画面验收。
- 独立 Subsurface Profile 配合 Substrate 前表面连接；散射按皮肤和薄组织遮罩控制，硬组织与湿部位使用各自的颜色和粗糙度。
- 使用本机既有 PROTOFACTOR 狼模型、眼/牙齿/口腔色彩和用户的 Meshy 突变体绿色皮肤色彩来源。细纹、毛孔、分区、修形均为本轮本地制作；不复用原狼毛纹法线，也不下载新素材。原始与派生美术资产沿原许可边界保留本机。

## 恢复点

原 `/Game/Monsters/InfectedDog/SK_InfectedDog`、`MI_InfectedDog_GreenSkin` 与 `DA_InfectedDog_AnimationSet` 保留。导入时把当前蓝图的动画集、网格、材质覆盖和动作引用写入 `appearance_before.json`，不修改原动画集；V2 使用它的副本，只切换参考网格。

需要恢复时，将原蓝图的 Animation Set、Mesh、材质覆盖按 `appearance_before.json` 恢复并保存。不要运行旧外观安装脚本，以免它覆盖已恢复的动作配置。

## 状态

模型、贴图烘焙、Blender 制作源与 FBX 已保存，`authoring.json` 状态为 `authoring_bake_and_export_saved`。UE 已通过现有编辑器的 MCP 批次完成导入、材质编译、资源保存及蓝图外观替换，`installation.json` 状态为 `assets_imported_saved_and_bound`。保存回执包括四张贴图、散射 Profile、母材质、材质实例、骨骼网格、专用动画集副本和原入口蓝图。

当前外观：`/Game/Monsters/InfectedDog/RealisticSkinV2/SK_InfectedDog_RealisticSkinV2`；材质：`MI_InfectedDogV2_Skin`；专用动画集：`DA_InfectedDogV2_AnimationSet`。F6 入口继续使用原感染犬蓝图。没有改动动作片段、六维属性或感染规则。

第一次接入遇到编辑器正在试玩，未写入资源；用户结束试玩后完成保存。没有启动、关闭或重启交互式编辑器。制作日志 `Saved/InfectedDogRealisticSkinV2-author.log`，保存日志 `Saved/InfectedDogRealisticSkinV2-install-02.txt`。

后台贴图烘焙属于资产制作；本轮不启动游戏、不追加截图渲染或动作验收，由用户测试。

## 用户要求的截图（后续）

用户随后明确要求“截图给我检查”。使用 UE 后台命令行读取已经保存的 V2 网格及其完整材质，在临时场景中输出静止参考姿态截图，没有改写美术资源、地图或启动游戏。

- 脚本：`Tools/InfectedDog/capture_realistic_skin_v2.py`
- 原图：`Saved/InfectedDogRealisticSkinV2/Preview/01_side.png`、`02_front_three_quarter.png`、`03_skin_closeup.png`
- 捕获采用可移动灯光、手动曝光、2.2 输出 gamma，并通过 `Editor.AsyncAssetCompilationFinishAll` 等待材质就绪。没有后期修图。
- 画面仍可见皮肤偏塑胶、颈部褶皱过于规则，以及背部/尾部黑色瑕疵；这些观察不等于已经确定瑕疵成因，不能标为写实外观验收通过。当前截图交由用户判断，未在截图任务中继续修改正式资产。
