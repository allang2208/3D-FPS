# 强化魔力球配重 V2

依据用户确认的 `../ManaOrbPommelConceptV2/empowered_mana_orb_design_01.png` 制作。用户确认语：按设计图进行精细化建模，同时魔法球内附加特效。

实体造型：保留原装柄尾上端 2 mm 接口和原始安装偏移，制作收腰接座、三片弯曲黑银护爪、内凹符文、上下尖菱形紫晶及镂空底托。护爪为有侧壁与倒角的实体，紫晶球直径 81 mm。中部保持外露球形轮廓。

材质：4096×4096 BaseColor、ORM、切线法线。ORM 通道为 AO、Roughness、Metallic。法线使用 OpenGL 约定，UE 导入翻转绿色通道。法线保存金属微表面，主要轮廓、倒角、护爪厚度和刻槽使用真实几何。

球内魔力：局部球体内的 24 步程序体积采样、脉动亮核、5 条实体旋转光丝、32 个实体光点。全部使用材质时间与局部坐标；旋转位移转换到世界空间后应用，随配重整体移动，无新增 Actor Tick。外壳之外不布置漂浮光片。RuneAwake 增强紫色魔力，EnergyTint 不改变配重颜色。

效果与身份：`ue_runebound_warhammer` 专属，`pommel/empowered_mana_orb`，符文苏醒基础 20 秒，装备后 30 秒。运行时持续时间及复制沿用已实现的服务器逻辑。

制作文件：`author_model.py`、`ManaOrbPommel_Construction.blend`、`ManaOrbPommel_Editable.blend`、`Export/SM_Runebound_EmpoweredManaOrb_V2.fbx`、`Textures/`。导入脚本为 `import_assets.py`，由 `import_background.ps1` 在现有 UE 批次互斥内后台执行。改造图标由实际新模型制作灰度输入，再按统一铆钉金属边框生成，提示词记录在 `icon_prompt.txt`。

V1 为用户否决的旧模型，已连同禁止发布标记移入 `trash/warhammer-refinements-retired-20261025/SourceAssets/RuneboundWarhammer20261022/ManaOrbPommelV1/`；本修订使用独立包。以 `import_receipt.json`、`build_receipt.json`、`published.json` 分别记录资产保存、构建和实际目录接入结果。未运行编辑器、游戏或视觉验收；由用户自行体验。

## 2026-10-24 白色棋盘格材质修复

用户反馈的球体棋盘格对应 `M_RuneboundManaOrb_VolumeV2` 的 SM6 编译失败：`PreSkinnedPosition` 仅能在顶点阶段使用，原能量云将它用于像素阶段。导入时保存资产和 C++ 构建不能证明该 GPU 材质编译成功。

已将体积材质坐标改为 `LocalPosition / Component / Exclude Material Shader Offsets`，通过现有编辑器重新制作、编译并保存该材质；其他几何、材质槽与玩法不变。`import_assets.py` 同步修正。原包备份已归档至 `trash/warhammer-refinements-retired-20261025/SourceAssets/RuneboundWarhammer20261022/ManaOrbPommelV2/BeforePixelRepair/`。

`pixel_material_repair_receipt.json` 记录保存及 GPU 编译结果。使用 `MaterialEditingLibrary.get_statistics` 完成目标资源的编译任务，实际生成顶点着色器 339 条指令、像素着色器 1465 条指令。编译缓存完成不需要再次改写已保存的材质图。为保存材质结束了一次正在运行的 PIE，保留原编辑器打开；未主动启动游戏、截图或进行视觉验收。

## 特殊改造分类

用户要求“设置为特殊改造”。运行目录、作者镜像及发布脚本已使用 `tier: special`，但界面的 `ColdSteelModification::Tier` 独立分级遗漏了该 ID。现已在 `GunsmithModificationTier.h` 将 `ue_runebound_warhammer / pommel / empowered_mana_orb` 明确归为 `Special`。必要构建结果写入 `special_tier_build_receipt.json`，不追加游戏测试。
