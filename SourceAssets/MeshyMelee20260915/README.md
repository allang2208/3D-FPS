# 寒晶·双手剑

2026-09-15，按用户指定的 Meshy ZIP 新增独立近战武器。用户确认名称为「寒晶·双手剑」，攻击和格挡沿用现有双手剑规则。

## 游戏入口

- 物品 ID：`ue_frost_crystal_sword`。
- 下次进入游戏时由起始武库发放至仓库；现有存档与新存档都使用 `ArmoryReceived` 记录一次性领取。仓库空间不足时保留未领取状态。
- 背包占用 2 × 4，装备在任一主手武器组，占用该组副手。沿用库存实例、快捷栏、转移、丢弃拾取和存档流程。
- 左键点按三段连击：右向左斩、左向右斩、突刺；长按蓄力后真实松开重击；右键格挡；F 键检视。动作、体力、伤害公式、剑气、跨步、声音均沿用现有双手剑规则，无新增冰冻等属性效果。
- 图标和物品模型预览通过现有实时模型界面读取本剑的 `world_mesh`。本次没有离线渲染 PNG；图标尚未生成时使用「寒晶」文字。

## 资产与握持

运行网格与四张贴图位于 `/Game/Weapons/FrostCrystalSword20260915`：

- `SM_FrostCrystalSword`：世界掉落及物品模型。
- `SK_FrostCrystalSword_Manny`：保留现有 Manny 手臂、手套、骨架 rest 和蒙皮，剑体刚性绑定至 `WPN_root`。
- `M_FrostCrystalSword` 与 `T_FrostCrystalSword_BaseColor/Normal/Metallic/Roughness`。

以原模型护手附近 `z=-0.427 m` 作为接触基准。剑刃按既有模型刃尖长度适配，约 81.17 cm；柄尾在护手下约 28.24 cm。握柄截面按既有持握区域约 3.02 × 4.65 cm 适配，并在护手与剑首之间平滑过渡；保留原剑的晶体、古铜色护手和深色握柄。未改变手模骨长、权重和动作轨迹。

颜色贴图使用 sRGB，金属度和粗糙度使用线性掩码，法线按 Meshy OpenGL 源到 UE 的方式翻转绿色通道。原包没有自发光或透明度贴图，本次按提供的四张 PBR 贴图接入。

运行时直接引用 `/Game/Weapons/AzureRunesword20260913` 的现有动画、Skeleton、声音与剑气资产。模型适配到相同刃尖和握持基准，现有刃根/刃尖采样、攻击判定距离、有效窗和跨步参数保持原值。

可编辑源中的动作来源：

- 待机、行走、奔跑：`../RuneSword20260913/WeightLeftV5/AzureRunesword_Manny_Editable.blend`；240 Hz 曲线时间轴等比例移至 480 Hz，保持原时长。
- 完整战斗、装备与检视作者源：`../RuneSword20260913/WristOutsideInspectV34/AzureRunesword_Manny_Editable.blend`，保留 V21 格挡、V22 蓄力、V23 装备以及 V34 检视。
- 普通斩 1.775 秒，重击蓄力 2 秒/释放 1 秒，突刺 1.25 秒，装备 1.20 秒，检视 3.60 秒。以共享运行资产和代码为准。

当前项目文档说明 V21 格挡和 V22 蓄力已获历史用户认可；V34 检视仍待用户试玩。本次复用这些资产，不将其历史记录当成本剑的动作验收。

## 可编辑源与制作入口

- `Original/`：指定 ZIP 原始解包。
- `OriginalSource.blend`：原模型导入源。
- `FrostCrystalSword_Manny_Editable.blend`：完整手模、新剑和已有动作。
- `Export/SM_FrostCrystalSword.fbx`、`Export/SK_FrostCrystalSword_Manny.fbx`。
- `build_frost_sword.py`：握柄适配、原 PBR 绑定、FBX 和 Blend 导出。
- `import_frost_sword.py`、`run_import.ps1`：向独立资源目录导入；使用本工程既有的纯内容 ImportHost，不进入游戏。
- `build_native.ps1`：构建 FPSGAMEEditor。
- `authoring.json`：尺寸与动作来源；`import_receipt.json`：导入回执。

构建器读取现有作者源，不重新制作动作。导入器只写入本剑目录，使用已有剑骨架，不覆盖原剑动画。作者源与运行资源共同依赖本机完整工程。

## 来源与分发

- 模型和四张 PBR：用户提供 `D:/FPS3D/资产/Meshy_AI_帮我生成一把半_0914033835_texture_fbx.zip`。包内没有附带许可证文本；本次在用户工程中使用，未公开上传模型、贴图或生成源包，不据此声明可再分发。
- Manny 手臂、手套材质和抓握：沿用本机已有 M4/Manny/VRE 与双手剑作者资产。其许可沿用各自来源，不由 Meshy 或 CC0 声音许可覆盖。
- 共享动作参考、挥剑/命中声音：沿用 `../RuneSword20260913/Reference/`，原参考的 `README.md`、`LICENSE` 和 `COMMIT.txt` 保留在该目录。
- 格挡/弹反和附加挥剑声音沿用工程既有对应资源与来源记录；本次未新增外部音频。

## 本次交付状态

完成模型制作、FBX 导出、UE 材质/网格导入、物品与伤害公式接入、原生构建。UE 导入返回成功；FBX 导入器报告 bind pose 相对矩阵警告，并自动重建 bind pose 成功。该导入记录不代表手臂或握持效果已验收。

按用户全局规则，未运行游戏、PIE、回归、静态检查、验收渲染或截图，由用户自行测试。没有直接操作玩家存档；新增武器由下次正常进入游戏时发放。已打开的编辑器需重新启动以加载本轮原生模块。
