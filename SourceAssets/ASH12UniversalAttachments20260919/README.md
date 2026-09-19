# ASH-12 通用瞄具与前握把适配

## 制作范围

复用项目当前四种通用瞄具、LPVO 活动环及四种通用前握把主体。新增 ASH 专用导轨接触鞋、侧夹肩与螺钉，保留主体比例、原有 UV、镜片、分划和瞄具内壁消光。共振握把从可编辑源恢复金属／聚合物两个分区。

作者读取当前 `ASH12_Surface_Editable.blend` 和共享配件实际 UE 导出，安装值来自导轨接触段。没有执行新增预览、截图、实机测试或验收渲染。

## 装配约定

以 `WPN_RearSight` 的源坐标为原点，+X 朝前、+Z 沿导轨法线。模型枢轴位于自己的接触面；运行时由 ASH 的参考骨骼导轨帧转换到 `WPN_root`，不复用 M4 的下移参数。

- 上导轨冠面约 `Z=-0.295 cm`，宽约 `2.07 cm`。瞄具原本的 Z=0 与光学中心保留，新增薄接触鞋补齐冠面间隙；全息和 LPVO 前移基准为 11 cm，红点和棱镜为 10 cm，使底脚落在可用导轨段。
- 下导轨冠面 `Z=-14.0265 cm`，宽约 `2.06 cm`。垂直／侧倾／阻手器安装基准为 30 cm，共振为 32 cm；后者较长的主体沿下导轨展开。Blender 横向中心 `+0.0439 cm` 在 UE 为 `-0.0439 cm`。
- 原握把主体仅作整体刚性变换与接触面高度归零，未缩放。夹座中间留出导轨空间，两侧斜肩贴合轨缘。

## 材质

握把金属按 ASH 当前 Front 涂层制作：线性底色 `(0.090,0.095,0.103)`、粗糙度中心 `0.45`、金属度 `0.70`。瞄具连接鞋匹配 Sights 涂层；已有 ASH 瞄具外壳、夹具与倍率环材质继续使用现有枪型专用版本。

新增金属涂层采用独立 UV3、4 cm 物理尺度的细粗糙度贴图；微法线采 UV0。垂直／侧倾握把重新生成涂层所需的 UV0，原光学 UV、标记和法线保留。最终网格设置保留原分离法线、使用 MikkTSpace 按 UV0 重建切线。共振聚合物继续使用自身防滑法线与粗糙度，底色贴近 ASH 非金属分区；棱镜阻手器保留原聚合物材质。新增湿润／水珠材质合并到 ASH 私有天气映射，保留枪体、瞄具、消音器既有映射。

## 抓握与状态

使用已接受的 M4 VRE 垂直／侧倾／阻手器及共振专用整手姿态作为供体，读取过现有 `VREGripExtensions20260912/Delivery/Runtime_Grips.png`。每个握把重新适配 ASH 左手掌心、肩肘与前臂扭转，不改变指骨长度和手模。

每族 11 条动画，共 44 条：idle、aim、fire、aim_fire、equip、reload、reload_empty、SprintEnter、SprintLoop、SprintExit、QuickCombat。普通／空仓换弹时长仍为 2.4／3.3 秒；右手从镜头右侧进入拉栓的当前动作、弹匣、枪根及机械轨道保留。冲刺进出在握把手型与原离镜动作之间渐变，循环保持单手持枪和左臂离镜。

## 作者入口与运行路径

1. `export_shared_sources.py`：从 UE 导出本次共享模型及材料绑定。
2. `read_authoring_inputs.py` / `read_mesh_interfaces.py`：制作所需的导轨与抓握坐标读取。
3. `author_models.py`：连接件制作、UV、涂层贴图和 FBX。
4. `author_grip_animations.py`：保留既有动作，生成 ASH 左手抓握分支与可编辑工程。
5. `import_assets.py`：在启用 RHI 的完整编辑器、非 PIE 状态下导入并保存本次资产，合并天气映射；拒绝 `-NullRHI` 和 commandlet。
6. `install_catalog.py`：只修改 `ue_ash12` 的前握把目录，数值从当前通用 M4 配件目录继承。
7. `read_export_bounds.py`：Blender 读取当前 FBX 的实际顶点边界，写入 `export_bounds.json`。修改源模型并导出后应同步更新。
8. `finish_mesh_build.py` / `repair_bounds.py`：在启用 RHI 的完整编辑器、非 PIE 状态下，从 FBX 重新生成最终切线和边界并保留材质槽。通过 `ASH12AttachmentAssetTools` 清除旧导入残留的 `bDoFastBuild`，使用高精度切线和 UV 格式完整重建网格及距离场。保存前同时核对 FBX 实际边界、渲染边界和距离场范围；禁止在 `-NullRHI` 下重建保存。该步骤依赖已编译的当前 Editor 模块。

可编辑源为 `ASH12_Attachment_Models_Editable.blend` 和四个 `ASH12_*_Grips_Editable.blend`。`models.json`、`animations.json` 记录作者参数，`import.json` 记录实际保存的运行绑定。运行目录为 `/Game/Weapons/ASH12/UniversalAttachments20260919`，已加入 Cook。

配件 ID 沿用通用分类，接入当前枪匠预览／应用、实例保存、武器图标装配和掉落装配；配件卡片继续使用现有通用模型图标。C++ 入口见 `ASH12Attachments.h`、`ASH12WeaponAssets.h` 及现有四种握把装配文件。

## 交付状态

九个模型、材质、44 条动画已制作、导出并保存到 UE，前握把目录和运行接入完成。普通 Editor 模块构建成功，日志 `Saved/BuildEditor/build-20260919-211322.log`。

首次后台导入日志为 `Saved/ASH12UniversalAttachmentMeshesImport.log`。首次切线构建日志 `Saved/ASH12AttachmentTangentFinal.log` 只说明保存成功，当时未进行实机测试。随后用户反馈配件不可见和改造预览拖动异常，排查发现该次 NullRHI 重建保存的九个网格边界损坏；首次保存不再作为有效交付依据。

2026-09-19 修复：确认九个模型的 `bDoFastBuild` 均为 true，清除后从原 FBX 在启用 RHI 的完整编辑器重建，保留原材质、分离法线和 UV 坐标。九个模型的边界均与独立读取的 FBX 顶点范围相符（各轴误差小于 0.02 cm），渲染边界及距离场也通过保存前检查；当前 `import.json` 已记录修复后的边界和构建模式。证据为 `Saved/ASH12PreviewFix/repair.json`、`Saved/ASH12PreviewFixImportedMeshRepair.log`；修复前资产备份在 `BeforeBoundsRepair/`。当前问题和运行结果见 [故障修复记录](../../Docs/Weapons/ash12-preview-bounds-fix-20260919.md)。

最终普通模块构建日志为 `Saved/BuildEditor/build-20260919-222937.log`。独立进程、独立存档下的定向排查记录在 `Saved/ASH12PreviewFixAcceptedFinal.log`：112 项检查通过，失败 0，渲染矩阵错误 0；覆盖四组瞄具／握把的显示与切换、构建及边界数据、ASH/M4 的鼠标拖动与滚轮对比、托腮板显示。未扩大到 44 条动画、天气及其余枪械功能测试。
