# 缚群 V9：肉体碰撞覆盖与贴身布料约束

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户反馈 V8 衣物仍大量穿进肉体。本轮只修复衣物接触，不重调攻击或材质。

## 源码中发现的缺口

V7/V8 的布料专用 PhysicsAsset 没有主体碰撞，仅包含同侧腿和右侧触手根部。腿半径取肉体径向距离的第 33 百分位再乘 0.88，不能包住可见肉体。长衣的 MaxDistance 可达 18 cm、AnimDrive 为 0.02，贴身区域也可能被拉到肉体内部。V8 外推凹陷及材质调整未补上这层碰撞缺口。

## 本轮制作

- 长衣补齐主体、十条供体肢体和近端触手碰撞。主体按平面四象限分成有重叠的凸体，保留肢体间的凹隙；袖料使用对应供体肢体的凸体，避免整身碰撞块把袖口顶走。每个凸体从对应肉体表面支持点生成并外扩 2 cm。
- 在 Blender 中按同样的碰撞外形重新适配衣物。制作求解使用现有待机、行走、转身与咬击片段的姿态约束，同时考虑实际肉体表面；这属于生成衣物形状，不作为游戏测试。
- 贴身衣物转接到邻近肉体表面的混合骨权重，再沿布面平滑。细分原拟合过程拉长的边，避免长三角面直接横切肉体。
- 上部连接固定，主体附近活动范围收至约 1.2 cm；下摆最多 8.7 cm，并进一步按与肉体的空间余量限制。袖料最多 1.4 cm，同时保留原有更小的限制和固定区。
- 重新统一代理外侧法线，后向止挡距离为 0，半径 20 cm；长衣 AnimDrive 0.12，袖料 0.22，增加动画驱动阻尼及碰撞厚度。保留连续代理和原 4 mm 实体布面厚度。
- 继续使用 V8 布料材质。触手的 0.62 s 蓄力、0.135 s 释放、0.48 s 收势与 2 s CD 不在本轮修改。

## 交付文件

- `SourceAssets/BoundCongregateMeshy20261006/ClothContactV9/BoundCongregate_ClothV9.blend`
- 同目录 `SK_BoundCongregate_ClothV9.fbx`
- `Tools/BoundCongregate/author_cloth_contact_v9.py`
- `Tools/BoundCongregate/import_cloth_contact_v9.py`
- `Tools/BoundCongregate/finish_cloth_contact_v9.ps1`
- `Source/FPSGAME/Monsters/BoundCongregateAuthoring.cpp`

Editor/Game Development 构建已完成，V9 活体网格、布料碰撞与模拟、对应软体尸体、原有 BP_BoundCongregate 均已后台保存，完成记录见输出目录 `delivery.json`。未运行游戏、视觉检查或验收测试，实际布料接触由用户测试。
