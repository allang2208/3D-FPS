# 陨星封闭岩体与龙息同源火场（2026-10-19）

用户反馈陨石漏空、未封闭，要求匹配已调整的范围，并参考龙息优化地面持续火焰。

后续用户否定本页的 V1 地面火场（像火环）；闭合岩体继续使用，火场已转为 [填充燃烧 V2 与高级魔法距离调整](advanced-magic-range-filled-meteor-20261019.md)。本页 V1 火场参数只作为制作历史。

## 定向排查

`SourceAssets/MeteorClosedVolume20261019/source-diagnosis.json` 记录实际运行模型与原扫描：

- 两者均为 1091 三角面、578 顶点、一个连通体，存在 63 条开放边。
- 陨石尺寸约 76 × 71.73 × 34.42 cm，属于未封底的扁平场景岩石；运行时整体再按技能快照缩放。
- `MI_MeteorNaturalRock` 母材质为 Opaque、非双面，因此漏空首先是几何问题，不是材质透明度。
- 当前龙息版本为 `DragonBreathVolumeV8R6_20261015`，使用原生 Niagara 3D Gas 体积模拟。

## 模型与尺寸

作者 `Tools/Skills/build_meteor_closed_rock.py` 从现有扫描复制制作，在开放边最高处上方截取完整上半部，沿切口镜像并焊接为连续下半部；下半部使用在接缝处归零的小幅不对称位移。保留扫描 UV/PBR，不用双面材质遮盖缺口。

厚度调整为水平宽度的约 82%，居中并重算法线。运行最长边继续取 `80 * (Radius / 217.5)` cm：一级 240 cm，最高级约 397 cm，与三倍爆炸范围和等级成长同步。原始扫描及 RealisticV3 包保持作为重建输入。

独立材质实例把细节纹理平铺从 18 调至 54，适应一级三倍模型的纹理尺度；保持原 BaseColour、Normals、烧黑色调和不透明母材质。

保存时只针对本次修复确认临时网格和保存后 StaticMesh 的封闭性、开放边及连通体，结果写入 `mesh-receipt.json`。这不是游戏画面验收。

## 地面持续火焰

作者 `Tools/Skills/build_meteor_ground_volume.py` 在现有 DragonBreathAuthor 无界面宿主内，复制龙息当前系统与材质实例。每个陨星火场使用一个扁平体积网格，移除可见火焰 Sprite；不可见粒子只在圆形地面内供给温度、密度和向上的速度。

- 复用 R6 红橙温度色、单次曝光补偿、RG 密度/温度采样、体积翻卷与现有 GDF 碰撞。
- 以 `AuraRadius` 分布地面火源，沿原 `Spread` 时钟展开、沿 `Fade` 收尾。原伤害、灼烧、持续时间、遮挡和预览不改。
- 网格宽度为火场直径加 160 cm；高度随半径变化并限制在 240–400 cm；中心上移，使供火点保持在落点附近。
- 本地施法者最大轴分辨率 128，远端 96；压力求解 6 次，源粒子最多 460/秒、寿命最多 0.46 秒。单实例原生网格随长宽高比例分配，未测量实际帧时。
- 保持一个 GroundFlames 组件，按施法复制快照初始化；迟到副本继续剩余火场时间。原落地爆燃、尾焰、声音和碎片时序保持。

运行与后台预载同步切换：`FPSMeteorStrike.cpp`、`FPSFireMagicComponent.cpp`、`PlayerSkillAssets.cpp`；新目录明确加入烹饪列表。

## 保存与构建

新目录 `/Game/Skills/FireMagic20260921/MeteorClosedVolumeV1`：

- `SM_MeteorClosedRock`、`MI_MeteorClosedRock`。
- `NS_MeteorGroundVolume`、`MI_MeteorGroundVolume`。

火场资产已保存，`volume-receipt.json` 为 `complete=true`，后台 commandlet 退出码 0。

模型已实际保存，`mesh-receipt.json` 为 `complete=true`：2252 三角面、1128 顶点，一个连通体、0 条开放边；保存后网格同样封闭。修复后源尺寸约 76.41 × 71.78 × 62.66 cm，运行按最长边归一到上面的技能尺寸。

共享构建中的必要编译修复：`VoxelBuildGeometry.cpp` 的 lambda 同时返回 `INDEX_NONE` 枚举和 `int32`，补充显式 `->int32`；`VoxelBuildComponent.cpp` 的坡段 `End` 局部变量遮蔽外层射线 `End`，改名为 `SlopeEnd`。炼药视图既有诊断代码补齐手册组件 include 与视图访问声明，并把文件追加标志传入 `SaveStringToFile` 的正确参数位。保留这些模块的既有逻辑，没有执行其诊断入口。最终构建状态记录在同目录回执。

随后新增的 `MageOutfitWireAudit.cpp` 用 `Pawn` / `Owner` 局部变量遮蔽控制器成员，导致 C4458；只在三个控制器方法中改为 `ControlledPawn` / `OwnerDetails`，没有执行该辅助工具。

最终构建回执：

- Editor：共享完整构建 `Saved/BuildEditor/build-20261019-171906.log` 成功，205.56 秒；包含本次陨星运行改动与资源引用，正式 DLL 已链接。回执副本 `FPSGAMEEditor-success-shared.log`。之后共享辅助代码新增时的失败尝试不是该次成功构建，也没有覆盖已经成功的 DLL。
- Game：本次 `FPSGAME-build-04.log` 成功，25.41 秒，`FPSGAME.exe` 已链接；包含随后解决的辅助代码变量重名修复。
- 汇总：`SourceAssets/MeteorClosedVolume20261019/build-receipt.json`。模型和火场的实际保存分别见 `mesh-receipt.json`、`volume-receipt.json`。

没有启动游戏、录制模拟或制作验收截图；模型缺口按用户要求做定向拓扑排查，火焰观感和性能交由用户测试。

整理说明（2026-10-22）：本页保留阶段记录；Before 备份和已替代作者的归档位置、当前资源及公开恢复边界见 [陨星发布记录](../Publication/Meteor20261022/README.md)。
