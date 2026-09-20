# 苍蓝星辉·双手符文剑模块化

2026-09-19 制作与接入；2026-09-20 最终六款通用配重由用户确认达标。本轮整理未追加游戏测试。

## 当前资产

目录：`/Game/Weapons/AzureRunesword20260913/Modules20260919`。

| 栏目 | 实体与改造 |
| --- | --- |
| 剑身Ⅰ | 独立原装剑刃；延锋、重脊、轻羽保持原装外形与既有数值，界面注明 |
| 剑身Ⅱ | 原刃面纹样／共鸣／侵蚀／导魔，使用现有银白符文覆盖层，仅覆盖剑刃 |
| 护手 | 原装／壁垒／反击／轻量，保留中央剑座，修改外侧护翼 |
| 握把 | 原装／吸震／速握／长柄，保留两端接口与原装握持外轮廓；吸震、速握只刻出浅防滑纹 |
| 配重锤 | 原装保留；改造统一使用 [六款共享目录](../SixSharedSwordPommels20260920/README.md) |

现行基础集保留 10 件静态模块（4 原装＋6 护手／握把改造）和 1 件原骨架手臂载体。原整剑资源不改写。完整原始资产的 Meshy／Manny 来源许可继续沿用，不将本次拆分解释为允许公开原素材。

## 安装合同

实际游戏静态网格作为切割源，Vibe3D 在当前编辑器内切面、封口、保存并导出 FBX。统一厘米空间：剑尖 +Z、宽 X、厚 Y；刃根／护手切口 Z=12.5，护手／握把 Z=-4，握把／配重锤 Z=-19.5。中央宝石安装座与两翼同属护手，切口没有借用寒晶剑数值。

握把和配重锤顶点分别相对 -4／-19.5 cm 的安装点归零。`interfaces.json` 保存实际安装环位置、面角 UV 和法线；完整源模型保留全部 UV 与表面法线。变体采用原装端面与连续形变，原装接口区不变形；新的水晶与支架使用独立材质。

长柄增加 2.8 cm，下端安装环平移，目录的 `pommel_offset_cm` 同步下移任意配重锤。左手复用已存在的 `FrostCrystalSword20260915/Grips20260919/LongGripAnimations` 家族；该家族来自同一套原符文剑动作、相同 WPN_root 空间。本次不重做动画。

手臂由当前实际 `SK_AzureRunesword_Manny` 去除剑体表面生成，保留骨架、权重和材质槽名字。安装比例从 WPN_root 的参考缩放取倒数（约 0.01），不对剑体再次乘位移或缩放。

符文剑原动作已将 Blade_Base／Blade_Tip 位移缩至 80%；本次以 `trace_from_animation` 保留原骨轨道取样，不用参考骨架的 3／100 cm 扩大范围。目录记录 2.4／80 cm 基线。柄尾砸击改读当前装配后的柄尾深度，其近身走廊和单目标合同保留。

## 作者与接入入口

1. `author_in_editor.py`：Vibe3D 拆分当前原装静态剑，当前骨骼网格去剑体，导出基础 FBX／目录参数。
2. `author_variants.py`：从这些 FBX 的原装接口制作六件护手／握把变体，保存 `RuneSword_Modular_Editable.blend`、`Export/*.fbx`、接口数据及真实模型 RGBA 菜单图标。
3. `import_variants.py`：在当前编辑器导入本任务变体和材质，合并 `Content/ColdSteelData/rune-sword-modules.json`；不覆盖寒晶目录。
4. 恢复现行 `Content/ColdSteelData` 配置；配重使用 `../SixSharedSwordPommels20260920/install_catalog.py`。旧 `merge_workbench.py` 和早期三款配重独立导出已归档，不再回写旧选项。历史回执／Blend 内的原型对象只作为生产记录，不是现行导入清单。

基础重建会导出原装输入，普通新增配件只追加变体、图标和目录，不重跑整套流程。`Export/SK_RuneSword_Arms.fbx` 为可编辑手臂载体；动作继续引用当前项目原动作和长柄家族。

共享 `ModularSwordVisual` 以武器 ID 选择目录；持剑、改造草稿／取消／应用、背包图标和掉落均使用同一选择。外观键包含武器、选项、模型与装配参数摘要，实例数据仍只写现有 `gunsmith_parts`。

菜单图标写入 `Content/ColdSteelData/AttachmentIcons20260913/ue_rune_sword_*.png`，来自本次真实部件。渲染仅用于生产菜单资产，没有制作游戏验收截图或预览。

改造详情由 `ColdSteelMelee::Evaluate` 计算实值与差值；卡片只写基本描述。三段连击、独立快速近战、重击、动作耗时、范围、耐力、格挡、魔法与弹反条件效果均来自原数值模型。应用／取消／保存继续使用原工作台事务。

构建方式与最终状态见 `Docs/Weapons/rune-sword-modular-20260919.md`。
