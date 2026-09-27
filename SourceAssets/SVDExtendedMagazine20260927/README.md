# SVD 扩容弹匣 — 2026-09-27

本轮按配件标准、原厂加长件规则、材质统一与图标规则制作。默认后台制作与构建；没有启动 UE、PIE、游戏测试或验收预览。UI 图标是配件交付资源。

## 形体与来源

- 母版：`SVDRefinedFinish20260923/SK_SVD_ModularStock.blend` 的 `SM_SVD_Magazine`；当前运行来源为 `StockAdapter20260923/SK_SVD_ModularStock`，不重新导入整枪或手臂。
- 在原弹匣骨骼局部的斜截面坐标中，保留 `z + 0.21871*y >= -0.026 m` 的原件。喉部、卡笋、口缘、内壁、托弹板与原厂上部抓握区继续使用原几何。
- 新区从原壳体 `[-0.026, 0.024] m` 的完整冲压面段取得，沿前后轮廓共同拟合的中心曲线延续约 **49.28 mm 弧长**。截面差异分布到整段，接缝分边后共用顶点，原底板沿曲线整体移动。
- 原面 UV0、材质分区和角点法线保留；切面属性在原面内插。新增区使用原冲压面的纹理，不重新投影整张机匣图集。当前几何为 23,590 个三角面，离线另制 11,795／4,718 面两级远景 LOD。
- 模型保存于原 SVD 骨骼网格空间，运行时复用现有 `WPN_SOCKET_Magazine` 骨链 bind 逆变换一次。没有另加手调座位或整体缩放。
- 材质直接绑定当前原厂弹匣的 `MI_MI_SVD_Magazine_Matte_86b0db`，复用已有干湿材质映射；不改现用枪体、V7 裸手和动作资源。

源模型为 LeroyCake 的 **SVD (Dragunov sniper rifle)**，沿用 CC BY 4.0 署名；详见 [第三方声明](../../ThirdPartyNotices/SVD_DRAGUNOV.md)。本轮壳体延长、原面重用、LOD 和图标均属于派生修改。既有表面参考及共享动作沿用各自来源许可。

## 游戏接入

`ue_svd` 新增 `magazine` 槽，仅提供 `false`（原厂）与 `ext_mag`（扩容）：

| 属性 | 原厂 | 扩容 |
| --- | --- | --- |
| 基础容量 | 10 | 20 |
| 普通换弹基础耗时 | 3.6 s | 4.5 s |
| 空仓换弹基础耗时 | 4.6 s | 5.75 s |
| 开镜耗时修正 | 无 | +5% |

扩容的 `stats`／`effects` 逐字沿用既有通用 `ext_mag` 数值，说明只描述形体。表中为目录基础计算值，实际技能及其它修正仍由原系统结算。

沿用枪匠草稿、应用、物品实例 `gunsmith_parts`、弹药溢出退回、持枪装配、独立预览、掉落和异步图标准备。新增专用模型路径；隐藏原厂外壳时同步隐藏 `SVD_InterfaceSteel` 内壁／底板槽，拆除恢复整套原厂件。SVD 不进入大弹鼓分支。

普通／空仓换弹保留本枪当前动作和各前握把变体，弹匣继续跟随原机械骨骼。没有调整手指、动作长度、音效源时钟、补弹阶段或旧存档内容。

## 制作入口

1. `read_source.py`：读取当前 SVD 材质，用于绑定和图标着色。
2. `measure_source.py`、`measure_pattern.py`：制作所需的源几何、冲压表面与现有手匣关系参数；不生成测试图。
3. `author_magazine.py`：可编辑主模型、原厂参考和 FBX；`SVD_ExtendedMagazine_Editable.blend`。
4. `author_lods.py`：后台减面并导出单个 FBX `LodGroup`；`SVD_ExtendedMagazine_LODs.blend`。必须在主模型导出之后执行。
5. `author_icons.py`：两张真实模型透明侧视图，原厂图同时用于分类入口；保存 `Icons/` 可编辑场景并复制生产 PNG。Blender 着色使用实际图集及当前涂层参数，但未逐节点复刻 UE 雨湿／微纹程序。
6. `run_import.ps1`／`import_assets.py`：无编辑器时使用 commandlet；已有编辑器时使用现有互斥桥，只保存本轮新包。整组 LOD 在 FBX 中一次导入，不调用游玩期间受限的编辑器 LOD 生成接口。
7. `update_catalog.py`：只修改 SVD JSON 对象，保留其它武器和并行编辑；执行后目录生效需重新创建游戏实例。

运行资产：`/Game/Weapons/SVDDragunov20260922/ExtendedMagazine20260927/SM_SVD_ext_mag`。

源码：`Source/FPSGAME/Weapons/SVDAttachments.h`、`M4DrumVisual.cpp`、`Content/ColdSteelData/gunsmith.json` 与 `Config/DefaultGame.ini`。

## 构建与交付边界

本轮已完成实际保存：扩容网格及三个 LOD、三张 UE 图标资产全部落盘，`import_receipt.json` 为 `status=imported_and_saved`、`catalog_published=true`。随后仅更新 SVD 的目录条目。既有编辑器内的旧游戏实例不会重新读取目录，下次进入游玩即可读取新槽位。

`build_editor.log` 记录本轮常规 `FPSGAMEEditor Win64 Development` 构建成功、基础 DLL 已链接落盘；未自动打开或重启编辑器。接入沿用已有编辑器和批次互斥，仅保存本轮资源，没有停止或启动游玩。

制作中将接缝多边形改为显式三角面以适配 FBX 导入。导入器曾提示局部近零切线／副法线；这属于着色限制记录，不代表视觉验收通过。没有运行一致性脚本、静态检查、游戏回归或验收渲染；安装观感、换弹接触、拆卸恢复和保存重进交由用户测试。
