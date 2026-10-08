# 沉匣、悬钟、伏窥者几何修复 V5

2026-10-07。接续 `three-remesh-anatomy-inspection-20261007.md` 的检查结论及用户“修复”指令，三只的 Blender 作者源、四级 FBX、UE 活体网格及重新绑定的软体尸体均已保存。三个 `installation.json` 均为 `complete=true`、`live_imported=true`、`stage=saved_and_bound`。

全部几何制作先在 Blender 后台完成，再按批次互斥使用 UE NullRHI commandlet 导入、保存。未打开编辑器 GUI，未启动游戏，未追加截图、渲染、回归或性能测试。以下面数来自本次作者导出记录，不能当作游戏表现或视觉验收结果。

## 修复内容

- **沉匣 M10**：先焊接 UV 拆分产生的重合几何顶点，同时保留逐角 UV，再制作主体各档 LOD。原口缝边界保持固定；远级不再分别折叠接缝两侧的碎片。近景原有 36 颗独立牙齿、牙龈和内口保留；牙齿 LOD1/2/3 分别分配 3,456 / 1,728 / 1,152 三角面，固定各颗牙的极值顶点。62 骨与两个 V5 口部组织修形继续使用。
- **悬钟 M09**：从 V16 原制作源的完整分件重新离线减面，恢复六片膜、五只眼、眼冠与十根钩指的闭合表面，保留连续腕肩及两只小臂。处理源分件少量多面共边连接，补面投射到原表面；按部件分别分配面数，并固定部件极值和材质交界顶点。使用与原分件 UV 对应的原版材质贴图，继续绑定原 114 骨。
- **伏窥者 M08**：保留当前主体、背部贯通开口与重建内壁，清理局部退化面、多面共边连接并补回下排牙齿和前爪缺口。新补面的位置和 UV 从原制作源投射，使用原皮肤材质；其余表面沿用 V3 配套贴图。口部与身体分别分配远级预算、固定分界顶点，保留 70 骨接口。

这三只继续使用原活体资源路径、生产骨架与物理资产。没有重新导入动画序列，也没有改动攻击参数、音效、AI 或原生玩法代码。已完成的螺柱 M14 缺齿修复 V4 不在本次修改范围。

## 导出面数

| 怪物 | LOD0 | LOD1 | LOD2 | LOD3 |
|---|---:|---:|---:|---:|
| 沉匣 M10 | 202,805 | 79,083 | 30,241 | 11,765 |
| 悬钟 M09 | 274,092 | 123,960 | 64,650 | 52,030 |
| 伏窥者 M08 | 233,324 | 88,500 | 34,500 | 13,798 |

悬钟的膜片封边和材质分区固定顶点限制了远级继续折叠，所以 LOD3 保留 52,030 三角面，高于有缺损旧版的 12,160。这里优先保留完整结构，没有宣称性能测试通过。LOD 屏幕尺寸阈值保持 1.0 / 0.45 / 0.22 / 0.09，实际远近切换交由用户测试。

## 活体与死亡接入

| 怪物 | 保持的活体资产 |
|---|---|
| 沉匣 | `/Game/Monsters/M10Mawcrawler/SurfaceRigV5/SK_M10_SurfaceRig_V5` |
| 悬钟 | `/Game/Monsters/HangingBellM09/V04/SK_M09` |
| 伏窥者 | `/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03` |

每只从已导入网格输出精确 UE 坐标表面，离线复用已认可的软体代理并重新计算绑定。新建配套尸体、独立骨架、DataAsset 和软体动态法线材质，保存到 `/Game/Monsters/AnatomyRepairV5/<ID>/`，再接回原活体的死亡绑定。尸体仅保留完成重绑的 LOD0，避免切换到活体骨骼权重。

## 文件与生产入口

- 作者源、四档 FBX、绑定输入和保存回执：`SourceAssets/AlienGeometry20261006/AnatomyRepairV5/<ID>/`。
- 汇总交付回执：`SourceAssets/AlienGeometry20261006/AnatomyRepairV5/delivery.json`。
- Blender 制作：`Tools/MonsterAI/author_anatomy_repair_v5.py -- <ID>`，由 Blender 的 `--python` 入口执行。
- UE 导入：`Tools/MonsterAI/Invoke-MeshyRemeshV3.ps1 -Species <ID> -Stage import -Revision AnatomyRepairV5`。
- 离线尸体绑定：`Tools/MonsterAI/embed_meshy_remesh_v3.py <ID> D:/FPS3D/FPSGAME/SourceAssets/AlienGeometry20261006/AnatomyRepairV5`。
- UE 尸体保存：同一 PowerShell 入口使用 `-Stage corpse -Revision AnatomyRepairV5`。
- 材质与目标路径适配：`Tools/MonsterAI/install_anatomy_repair_v5.py`。
- 本次修改前的活体和必要蓝图备份：各物种 `Before/`。仅在对应包未加载、没有未保存编辑时恢复指定文件，不回退整个项目。

本次完成资产制作和保存接入，未进行游戏测试或视觉验收。
