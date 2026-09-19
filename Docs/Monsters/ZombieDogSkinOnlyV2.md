# 僵尸犬：无毛皮肤 V2

用户随后要求恢复上一版残毛造型，本无毛方案已退出当前入口。当前材质修订见 [FineSkin V3](ZombieDogFineSkinV3.md)。

2026-09-15。用户反馈残毛不自然，明确要求去掉全部毛发，只保留皮肤和伤口。

- 从 V1 的可编辑模型继续，删除 `Fur` 材质对应的外层毛片；保留主体、断耳封口、体型、骨架、权重和现有伤口位置。
- 全身体表采用库内有机皮肤，不再混入原狼毛色和毛发法线。皮肤高度、微小起伏、AO 与伤口干湿差异继续保留。
- 重新烘焙三张 2048 贴图：BaseColor、ORM、DirectX Normal。全模型使用不透明皮肤材质，无残毛材质或透明毛层。
- 沿用 V1 的非镜像图集、动作序列、攻击状态机、数值、AI 和 Physics Asset。

新资源目录为 `/Game/Monsters/ZombieDog/SkinOnlyV2`。现有 `/Game/Monsters/ZombieDog/V1/BP_ZombieDog` 的动画数据集和网格引用切到无毛版，因此 F6 中仍选“僵尸犬”。原 V1 源文件及资产保留为历史制作输入。

可编辑交付位于 `SourceAssets/ZombieDogSkinOnlyV2`：

- `ZombieDog_SkinOnly_Authoring.blend`
- `SK_ZombieDog_SkinOnly.fbx`
- `Textures` 与 `authoring_manifest.json`
- `ue_import.json`、`activation.json`

制作工具依次为 `Tools/ZombieDog/author_skin_only.py`、`install_skin_only.py`、`activate_skin_only.py`。前者使用 Blender 制作并烘焙，后两者导入 UE 并切换现有入口。来源及归属沿用 `SourceAssets/ZombieDogV1/CREDITS.md`。

本次仅更新资源，无 C++ 改动或编译。未运行游戏、动作预览或画面测试，由用户重新进入工程并从 F6 生成僵尸犬试玩。
