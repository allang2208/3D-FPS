# 四品阶药水瓶 · Blender V1

2026-09-26。按已交付的四品阶概念图，以 Blender 剖面、放样和倒角直接制作。没有调用 Meshy 或 5080 图生 3D。

## 源模型

| 品阶 | 可编辑源文件 | 宽 × 深 × 高 |
| --- | --- | --- |
| 普通 | [Potion_Common_editable.blend](Potion_Common_editable.blend) | 68 × 68 × 175 mm |
| 中级 | [Potion_Medium_editable.blend](Potion_Medium_editable.blend) | 76 × 56 × 180 mm |
| 高级 | [Potion_High_editable.blend](Potion_High_editable.blend) | 74 × 60 × 185 mm |
| 特级 | [Potion_Special_editable.blend](Potion_Special_editable.blend) | 78 × 62 × 190 mm |

每个文件保留可编辑的 Authoring_High、Game_LOD0/1/2 和 Animation_Anchors 集合。默认显示高精度作者网格，游戏版本隐藏以避免重叠。主体为直筒圆瓶、扁梨形、六棱切面和圆角盾形；金属配件逐档采用无金属、锡灰、银色、浅黄铜。

- 玻璃瓶为有内壁、底厚和贯通瓶口的空心结构，主体侧壁名义厚度约 2 mm。
- 三个动作部件共用瓶底原点：Shell、Liquid、Stopper。装饰颈圈和底缘属于 Shell，软木及其顶盖属于 Stopper。
- 每档另有 Closed 完整瓶供地面拾取使用；HP/MP 共用这四套几何，只替换 Liquid 材质槽。
- 瓶口外径 32 mm、内径 24 mm，拔塞结构；液体底面基准为 6.2 mm，与现有排空位移一致。
- 四档瓶口相对抓握基准均为 32 mm，沿用现有生命药水握姿和动作时序。手指贴合及实际饮用观感未运行验收。

## 导出及材质

[Export](Export) 包含每档生命/魔力两个 GLB（共 8 个），各分件与完整瓶的三级 FBX，以及包含原生 FBX LOD Group 的导入文件。

Blender 作者网格与导出使用米；UE 导入后使用厘米。正面为 -Y，Z 向上；所有动作部件底部原点相同。Shell、Stopper、Closed 的 LOD0 FBX 包含独立 UCX 凸碰撞，液体没有碰撞。

玻璃、液体、软木、锡灰金属、银和黄铜独立分槽。软木的 1024 像素 BaseColor、Roughness 和 OpenGL Normal 贴图由确定性纹理脚本制作并打包进源文件；UE 导入翻转法线绿通道。金属颜色与粗糙度使用线性值，几何保留真实倒角。所有造型和程序贴图为本次原创制作，无外部商用模型依赖。

UE 使用 Thin Translucent 实时玻璃/液体近似；它不等同于 Blender 离线路径追踪的厚玻璃折射和体积吸收。液体颜色在材质实例 MI_Potion_Health / MI_Potion_Mana 上设置。

## 已保存 UE 资产与接入

目标目录：`/Game/Items/Consumables/PotionTiersV1`。本轮后台导入保存 16 个静态网格，各包含 3 个 LOD；材料、实例和软木贴图单独保存在 Materials / Textures。

- [import_receipt.json](import_receipt.json)：资产保存回执与导入 LOD 数；不表示游戏测试通过。
- [manifest.json](manifest.json)：源文件、导出路径、材质槽、源几何面数。
- [author_bottles.py](author_bottles.py)：完整 Blender 制作和导出脚本，不包含渲染。
- [import_bottles.py](import_bottles.py)：后台材质制作与 FBX 导入保存脚本。
- [design.json](design.json)：尺寸与剖面参数。

运行映射在 `Content/ColdSteelData/potion_visuals.json`，由 `Items/PotionVisuals` 读取一次并供拾取、第一人称药水共用。八种原物品 ID 不变，同品阶生命/魔力只换液体材质。保留原消耗数量、效果、稀有度、存档和动作时间；保留原模型资产。现有背包图标本轮没有重绘。

制作状态：源模型、GLB/FBX、UE 模型和材质已落盘。FPSGAMEEditor 常规构建成功，16 个构建步骤，总耗时 18.90 秒，基础 DLL 已更新；日志为 build-console.log 和 Saved/BuildEditor/build-20260926-214301.log。未主动启动交互 UE 编辑器、PIE、游戏、截图、验收渲染或测试；实际视觉、抓握和物理表现由用户测试。
