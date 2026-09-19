# 僵尸犬：恢复残毛与细化皮肤 V3

2026-09-15，用户要求恢复无毛版之前的造型，主要优化粗糙的皮肤材质。

随后已按用户要求接入 [随机伤口 V4](ZombieDogRandomWoundsV4.md)，继续使用本版细皮肤质感，身体伤口与脱毛范围改由每只犬的种子控制。以下保留 V3 制作记录。

## 制作调整

- 恢复 V1 主体、残毛层和断耳封口。UE 内直接复制 V1 网格并替换材质，保留其骨架、绑定、权重、UV 与各材质分区。
- 有机皮肤投射由每米 3.4 次改为 8 次，缩小原有组织纹理的可见尺度。
- 皮肤凹凸距离从 2.5 mm 降到 0.65 mm；伤口边缘的凹凸距离从 4 mm 降到 1.6 mm。叠加 0.09 mm 的细节噪声，作用范围限于原裸露皮肤遮罩。
- 收窄皮肤色调变化，减轻大块暗斑与 AO 反差。干皮粗糙度映射到 0.54–0.70，伤口保留 0.32 的湿润粗糙度。裸皮区域进一步减弱原狼毛发法线，残毛区域维持 V1 强度。
- BaseColor、ORM、Opacity、DirectX Normal 四张贴图均从 2048 提升到 4096，保留 V1 非镜像图集与伤口位置。

以上数值是本次制作参数，尚未经用户试玩调整。没有改动几何或原有伤口、脱毛遮罩，也没有重新生成角色、修改动作或调整战斗数值。

## 接入与源文件

资源目录为 `/Game/Monsters/ZombieDog/FineSkinV3`。新网格使用材质实例 `MI_ZombieDog_FineSkin`、`MI_ZombieDog_FineFur`，父材质继承 V1 的皮肤与透明残毛设置。动画数据集复制切换前的僵尸犬配置，只替换参考网格。现有 `V1/BP_ZombieDog` 指向新数据集，F6 继续选择“僵尸犬”。

可编辑源位于 `SourceAssets/ZombieDogFineSkinV3/ZombieDog_FineSkin_Authoring.blend`，贴图、制作参数、导入与切换记录在同目录。几何导出仍复用未修改的 `SourceAssets/ZombieDogV1/SK_ZombieDog.fbx`。原素材归属沿用 `SourceAssets/ZombieDogV1/CREDITS.md`。

工具依次为 `Tools/ZombieDog/author_fine_skin.py`、`install_fine_skin.py`、`activate_fine_skin.py`。未进行游戏、动作预览或画面测试；本次仅更新资源，无需 C++ 编译。
