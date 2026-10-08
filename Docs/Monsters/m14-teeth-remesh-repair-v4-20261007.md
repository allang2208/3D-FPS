# 螺柱 M14：减面后的缺齿修复 V4

用户反馈减面后的螺柱牙齿缺失。本次只处理螺柱口部几何及对应 LOD、软体尸体，不改攻击时序、音效、AI 或其他怪物。

## 原因和修复

对照 V15 正式制作源和 V3 Meshy 减面源，缺口已存在于减面网格：上排中间齿尖被截断，右侧和下排有表面塌缩及破洞。V3 将整个口部一起减面，未单独保留牙齿内外表面。局部原网格到 V3 的最大偏差约 2.30 cm。此值包含诊断裁剪范围，不代表每颗牙齿的误差。

从 `M14_SupportSkin_v15.blend` 取完整口部表面，连同牙根、牙龈和内口恢复；不是仅复制原先按朝向分类的部分“牙齿”面。原始口部选区 137,490 三角面，在 Blender 中保留边界后按档局部减面，再与用户减面身体连接。移除原身体上损坏的 7,590 三角面口部选区，避免双层牙齿重叠。

三组口部连接边界在各 LOD 保持一致。连接使用连续网格；新旧顶点统一投射 V15 权重和现有 9 个死亡修形。主体保留 V3 UV 和贴图；恢复口部使用原始 UV、原 `M_M14_Mouth` 材质，接缝单独投射 UV，避免夹断的 UV 造成法线贴图斑块。

| 档位 | 完整模型三角面 | 恢复口部三角面，不含连接带 |
|---|---:|---:|
| LOD0 | 251,981 | 60,000 |
| LOD1 | 101,737 | 28,000 |
| LOD2 | 41,965 | 14,000 |
| LOD3 | 17,801 | 7,000 |

原始高模 1,936,942 三角面；V3 为 198,345。V4 仅增加口部所需细节，主体不回退到高模。面数不作为帧率提升的证据。

## 交付与接入

Blender 作者源、四档 FBX、UE 活体网格、配套软体尸体及死亡引用均已保存。`installation.json` 记录 `complete=true`、`stage=saved_and_bound` 和实际保存资产；两个后台 commandlet 均以退出码 0 完成。未打开 UE GUI，也未运行游戏。

- 作者源及四档 FBX：`SourceAssets/AlienGeometry20261006/RemeshV4Teeth/SpiralPillarM14/`。
- 活体继续原路径 `/Game/Monsters/SpiralPillarM14/SK_M14_SupportSkin_v15`，使用原生产骨架、物理资产及动画资源。
- 配套软体尸体、独立骨架及 DataAsset 使用 `/Game/Monsters/RemeshV4Teeth/SpiralPillarM14/`。沿用 V19 的 523 节点、1,620 四面体代理和加强边，重新离线绑定新表面；尸体只使用重新绑定的 LOD0。
- 活体死亡绑定与 `BP_SpiralPillarM14.soft_body_death_data` 一起更新。
- 接入前资产备份位于该版本目录 `Before/`，旧 V3 制作源及尸体保留。

离线尸体绑定写入 125,621 个不同表面位置，全部位于现有软体代理内，无需改动代理或原生 C++。原 49 骨接口和 9 个死亡修形保留；本次没有重新导入动画。

制作入口：`Tools/SpiralPillarM14/author_teeth_remesh_v4.py`。接入入口：`Tools/MonsterAI/Invoke-MeshyRemeshV3.ps1 -Species SpiralPillarM14 -Revision M14TeethV4 -Stage import`，随后离线生成绑定，最后同入口 `-Stage corpse`。

按本次“排查修复”请求进行了局部 Blender 口部诊断，图像和几何记录位于 `SourceAssets/SpiralPillarM14Meshy20261004/TeethRemeshV4/`。没有运行 PIE、游戏回归或性能测试，也不宣称动画中或实际 LOD 切换效果已验收；由用户在游戏中测试。
