# 寒晶剑：符文可见性与护手接缝修订

> 2026-09-19：剑身符文显示已追加[银白荧光升级](../FrostSwordRuneGlow20260919/README.md)，运行材质路径沿用 SurfaceV2。下文为 9 月 15 日历史修订记录；重建旧符文资产后继续执行新目录的 `apply_rune_glow.py`。

2026-09-15。针对用户报告的“持剑、F 检视均看不到符文”和三款护手接口突兀进行修复。本次仅进行这两项的视觉诊断；没有进行战斗、存档或完整玩法回归。

## 符文

读取原存档时，寒晶剑已安装 `erosion_rune` 和 `riposte_guard`。新启动的独立游戏进程中，原覆盖材质和贴图可以加载并绘制，因此没有证据把用户端的完全不可见直接归因于资源缺失。原显示方案存在以下可见性问题：

- 原图左右空白占比较大，投射到剑身的有效纹样过窄。
- 先缩小贴图再做高亮阈值提取，会削掉细线覆盖率。
- 加色混合容易让白纹与明亮蓝色剑身混在一起。
- 用材质实例对象名称识别剑身，对经过动态材质包装的实例不可靠。

新版本 `SurfaceV2/M_SilverRuneSurfaceV2` 采用预先提取的线条覆盖图，在线性空间生成 mip；横向只取原图中部 30%—70%，再投射到原有剑身范围。材质改为半透明银白表面，保留三种各自的时间闪烁；低谷仍可见。识别依据改为源材质名称。剑身顶点、UV 和动作无需为符文改动。

原图、提示词仍在 `../MeleeRuneMods20260915/Generated`。本次没有重新生成图案。`prepare_rune_masks.py` 是技术遮罩提取；`rune_mip_diagnosis.json` 记录缩小前后的覆盖率。

### 实际持剑组件截图

使用 `-FrostRuneVisualAudit -ColdSteelProfile=FrostRuneVisualAudit_After_09151502` 启动独立游戏进程，经正常库存装备刷新生成 `RuneSwordViewmodel`，不写入用户的 ColdSteelPlayer 存档。拍摄场景为引擎 Entry 空场景，使用诊断灯光。

冻结同一个持剑姿态后关闭／开启符文：

![关闭符文](../../Saved/FrostRuneVisualDiagnosis/ColdSteel_FrostRuneVisualAudit_After_09151502/hold_without_rune.png)

![开启侵蚀符文](../../Saved/FrostRuneVisualDiagnosis/ColdSteel_FrostRuneVisualAudit_After_09151502/hold.png)

![F 检视](../../Saved/FrostRuneVisualDiagnosis/ColdSteel_FrostRuneVisualAudit_After_09151502/inspect_back.png)

截图及每个材质槽的实际参数记录位于 `Saved/FrostRuneVisualDiagnosis/`。这是新进程、独立场景中的绘制证据，不等同于已经复现并解释用户旧进程的完全不可见现象。

同样通过实际装备流程取得的另外两组：

- [共鸣符文＋壁垒护手](../../Saved/FrostRuneVisualDiagnosis/ColdSteel_FrostRuneVisualAudit_resonance_rune_09151504/hold.png)
- [导魔符文＋轻量护手](../../Saved/FrostRuneVisualDiagnosis/ColdSteel_FrostRuneVisualAudit_conduction_rune_09151504/hold.png)

## 护手

旧模型使用独立盒状套筒覆盖原护手切口；两端没有焊接，表面与法线不连续。沿用之前 5080 TRELLIS.2 生成母版的轮廓，本地修订接口：

| 护手 | 接口处理 | 外翼厚度 |
| --- | --- | --- |
| 壁垒 | 填出向厚翼扩张的圆滑连接面 | 26 mm |
| 反击 | 连接颈沿上弯轮廓延伸，削平局部鼓包 | 20 mm |
| 轻量 | 镂空前补出完整连接颈，后方保留开孔 | 14 mm |

以原切口全部边界顶点建立 16 段切向过渡，并在两端共用顶点。局部平滑限制在接口范围；原有保留表面位移不超过 0.7 mm。三款 `authoring.json` 中，连接区开放边均为 0。

三款共用 `M_FrostCrystalSword_SeamlessBronze`：原 UV0 纹理在接口带通过顶点色渐变到 UV1 的同源青铜区域，法线也连续过渡。新护手不再使用独立覆盖套筒。剑刃、握持骨架和手臂动作保持原基线。

运行资产目录：`/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/`。每款同时导入 SM、SK，`MeleeGuardAssets.cpp` 统一负责世界模型、改造预览和持剑模型选择。原装选项仍使用原始剑。

### 模型制作近景

![壁垒护手](bastion_guard/oblique.png)

![反击护手](riposte_guard/oblique.png)

![轻量护手](light_guard/oblique.png)

每款目录保存完整可编辑 Blender 文件、SM/SK FBX 和前／后／斜视制作图。引擎材质与骨架导入后的近景在 `Engine/<guard>/`。

## 文件与重建

- `author_seamless_guards.py -- <guard_id>`：Blender 制作、导出与指定近景。
- `import_smooth_guards.py`：UE 导入模型、顶点色及统一青铜材质。
- `prepare_rune_masks.py`、`import_rune_surface.py`、`silver_runes.hlsl`：符文遮罩和材质。
- `guard_import_receipt.json`、`rune_import_receipt.json`：实际导入资产路径。
- `FrostSwordSurfaceCaptureCommandlet`：只用于指定资产的静态／蒙皮渲染诊断。
- `FrostRuneVisualDiagnosis`：仅显式命令行标志和指定隔离存档可运行。

已完成必要 Editor 原生构建。普通游戏中的手感与其它系统由用户自行测试；再次打开工程会使用新资产路径，已有安装选项无需重新购买。
