# 寒晶·双手剑：三款握把（2026-09-19）

> 2026-09-19 用户确认本轮最终结果成功、符合预期。此记录来自用户实机反馈；本次归档/文档整理没有重新测试。

## 已制作与接入

| 改造 ID | 名称 | 模型表现 | 两端安装面距离 |
|---|---|---|---|
| `shock_wrap` | 吸震缠柄 | 蓝灰皮革、交叉缠绕凹缝、银色收边 | 17.7 cm |
| `swift_grip` | 速握轻柄 | 薄皮握面、纵向凹槽、细银色嵌条 | 17.7 cm |
| `long_twohand` | 长柄双手 | 上段斜缠皮革、下段横向防滑纹、中间银环 | 20.5 cm |

按已同意的 Blender 精确建模路线制作。`Designs/` 保存三款独立生成的三视图和提示词；实际模型继承原剑安装端，以实物尺寸为准。

- 直接保留原装握把上端 2 cm、下端 2 cm 的网格、UV、顶点色及表面法线。中段采用连续网格重建，缠绕和凹槽为几何形状。
- 原装、吸震及速握共用护手连接点和配重锤连接点。长柄保留相同端面截面，柄尾与所选配重锤同步下移 2.8 cm。
- 各配重锤仍使用已接受的模型和材质；握把连接端复用现有 `M_FrostCrystalSword_SeamlessBronze`。
- 新皮革使用 Blender 制作的 2K 底色、粗糙度、法线贴图，银色饰面使用独立 PBR 材质。
- 三款均已输出实际模型的 1024 RGBA 改造选项图标，使用寒晶剑专属图标名，不覆盖另一把剑的共用图标。
- 复用现有三个改造 ID、属性数值及存档选择。只更新寒晶剑模型目录和握把栏目说明。

## 长柄动作

运行时选择 `long_twohand` 后使用 `Grips20260919/LongGripAnimations` 的 14 段动画。

- 从 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_*` 当前源动画复制，保留全部时长、采样帧数、武器轨迹、右手和手指动作。
- 左手实际握柄阶段沿剑轴向柄尾移动最多 1.8 cm；用保持骨段长度的手臂解算调整锁骨、上臂、前臂、手腕旋转。
- 权重依据原动作的左腕与握柄位置计算，离手检视、装备入场和扶剑格挡时逐渐解除。近乎伸直的手臂在可达范围内适配，不拉长骨骼。
- 完整动画源读数在 `source_animation_inputs.json`，可编辑逐帧数据与导出的 FBX 在 `Animations/`。
- 制作时参考现有 V46 检视、V52 下劈、V45 重击及 V21 扶剑格挡图；未制作新的动作验收图或运行游戏。
- 动画目录切换与配重锤偏移在共享模块装配逻辑接入；格挡/弹反音效仍读取原武器音效目录。

## 输出位置

- 模型：各改造子目录中的 `SM_FrostGrip_*_Editable.blend` 与同名 FBX。
- 材质源：`Textures/LeatherMaterial_Editable.blend`。
- UE：`/Game/Weapons/FrostCrystalSword20260915/Grips20260919`。
- 图标：`Content/ColdSteelData/AttachmentIcons20260913/ue_frost_crystal_sword_grip_*.png` 及对应 Texture2D。
- 接入目录：`Content/ColdSteelData/frost-sword-modules.json`。
- 导入写入记录：`import_receipt.json`；动作生成记录：`animation_receipt.json`。
- 改动前数据副本：`Before/`。

## 交付状态

模型、PBR、图标、动作资产和安装切换逻辑已写入工程。必要的 Editor 原生构建返回 `Succeeded`，目标已是最新。

**未运行游戏、测试或视觉验收，由用户自行测试。** 模块目录在进程中缓存；已开着的游戏或编辑器需要重新启动后读取新的改造目录。

## 制作脚本

1. `read_authoring_inputs.py`、`read_animation_inputs.py`：读取原安装截面及动作资料。
2. `author_grips.py`：重建三款握把并导出 FBX。
3. `bake_leather.py`：制作皮革 PBR 贴图。
4. `finish_grips.py`：给可编辑模型配置贴图，并制作改造栏图标。
5. `author_long_grip_animation.py`：复制并适配长柄动作；再次制作应使用新的修订目录，避免覆盖已存在的动画。
6. `import_grips.py`：导入模型、材质及图标，写入对应改造项。
