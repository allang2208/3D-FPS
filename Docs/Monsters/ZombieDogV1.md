# 僵尸犬 V1

**用户要求恢复本版残毛造型，并细化裸露皮肤。当前修订见 [FineSkin V3](ZombieDogFineSkinV3.md)。** 无毛 SkinOnly V2 留作历史方案，F6 仍使用同一个“僵尸犬”入口。下文记录最初残毛版的制作。

2026-09-15。用户指定以现有狼换皮，使用库内腐败皮肤、伤口材质并适当改变造型，沿用狼动作、攻击状态机及 AI。本次从现有狼蒙皮模型继续本地改造。

## 造型与材质

- 灰黑残毛配灰绿坏死皮肤，暗红创面集中在左肩、左颈、左脸与右侧腹，左肋另有三条抓伤。伤口由局部遮罩控制，干皮与创面使用不同粗糙度。
- 左耳上段从原模型切除，原体表断口补成封闭创面；仅焊接切口边缘的重合顶点。耳部残毛层随切口截断。
- 腹侧轻微收瘦，肩部略突出。保留狼原有骨架、绑定变换、权重、牙齿与攻击器官结构，不添加新的动画骨。
- 材质使用库内 `/Game/ZombiSkinMaterial` 的颜色变化、高度、粗糙度与 AO；其法线已找到但未直接套用。高度经静止姿态空间投射，结合原狼法线后烘焙到新 UV 的切线空间，避免不同投射方向的法线混用。
- 新增独立 `ZombieUV`，避免源镜像 UV 把不对称伤口复制到另一侧。Blender 作者文件保留原 `SourceUV`；游戏 FBX 的 UV0 使用新图集。四张 2048 贴图为 BaseColor、DirectX Normal、ORM、Opacity。ORM 的 R/G/B 分别为 AO、粗糙度、金属度，金属度为零。
- 残毛使用 Masked 材质，脱毛区抑制毛片可见性；皮肤与断耳补面使用不透明材质。烘焙是贴图制作，不是动作预览或画面验收。

## 游戏接入

入口：`/Game/Monsters/ZombieDog/V1/BP_ZombieDog`。

蓝图继承现有 `BP_WolfMonster`，独立动画数据集 `DA_ZombieDog_AnimationSet` 只更换参考网格，复用当前 21 个动作槽，包括奔跑 V2 混合配置和普通咬击 V2。命中、受击／弹反中断、扑咬、嚎叫召集、追击／返回、死亡与布娃娃仍由狼和共用怪物系统执行。骨骼与动作无需另做一份重定向。

初始数值沿用狼：220 生命、22 咬击伤害、36 扑咬伤害、380 cm/s 追击速度。没有新增感染、毒伤等玩法。Physics Asset 从狼的游戏版本独立复制，沿用其碰撞体及约束。

血条名称配置为“僵尸犬”。F6 → 怪物生成 → 僵尸犬；野狼仍是单独选项。新目录加入 AlwaysCook，以保留 F6 软引用的资源入口。

## 可编辑文件与重建

- `SourceAssets/ZombieDogV1/ZombieDog_Authoring.blend`：局部几何、原骨架、权重、原 UV、新 UV 与可编辑材质节点。
- `SourceAssets/ZombieDogV1/SK_ZombieDog.fbx`：游戏网格和骨架。
- `SourceAssets/ZombieDogV1/Textures`：四张游戏贴图。
- `SourceAssets/ZombieDogV1/authoring_manifest.json`、`ue_delivery.json`：制作参数及接入记录。
- `SourceAssets/ZombieDogV1/Source`：从当前 UE 狼导出的原始重建输入。
- `Tools/ZombieDog/export_sources.py` → `read_source_geometry.py` → `author_zombie_dog.py` → `install_zombie_dog.py`：导出、载入源、改造／烘焙、UE 导入与接入。

脚本在独立 `ZombieDog/V1` 目录创建资源，不覆盖野狼网格、材质或动作。导入脚本按制作版本更新本次尚未交付的网格和贴图，随后保留该版本资源；后续外观迭代采用新版本或明确重导入所需资产。作者脚本仅操作本次源副本。

模块构建记录：`Saved/BuildEditor/build-20260915-092933.log`。资源导入记录：`Saved/ZombieDogInstall-r2.log`。首次 FBX 导入报告网格节点的绑定矩阵不匹配，引擎随后成功重建有效绑定姿态并读取 34 根骨骼；这一导入处理不等于动画已经试玩验收。

来源见 `SourceAssets/ZombieDogV1/CREDITS.md`。未进行游戏测试、动作预览、截图或画面验收；外观与动作中的皮肤、切口表现交由用户试玩。
