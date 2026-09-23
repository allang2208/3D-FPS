# 在运行中的编辑器里做资产

> 正本／相关记录：`skills/ue5-auto-assistant/references/editor-open-development.md`。本文件只保留可复用技法，任务过程与数值以正本为准。

> 本文件由 `asset-model-workflow/SKILL.md` 按「复用面」拆出；入口只留触发表指针。
## 在运行中的编辑器里做资产（2026-09-16）

- **外部进程保存冲突**：编辑器加载着 `.uasset` 时，独立 commandlet/脚本宿主写同一包可能因占用失败，包装接口仍可能返回 `success=True`。修改已加载资产走当前**编辑器进程内**的 MCP/Python，处理本次保存返回和错误；不要为保存而关闭编辑器。用户明确要求落盘验收时，再按范围使用磁盘状态和独立进程读回。案例：`SourceAssets/RomanColumn20260915/README.md` 的保存事故段落。
- 当前编辑器新建的资产可继续在该进程内引用；临时网格 handle 先保存成实际资产。跨进程读取需要先保存并使用正确包路径，不把“必须重启/另开进程才可引用”作为默认制作步骤。
- Vibe3D（`unreal.ModelingService`）四个坑：`append_revolve_polygon` 的半径是 **radius + 剖面 X**（剖面须回中轴才封闭）；`project_uv(Planar)` 输出**厘米级 UV**，需缩放投影器；相切堆叠件**不能 `SelfUnion`**，会裂出开放边；布尔与自并集之后要重新检查封闭性、开放边与连通体数量。
- 建筑构件按 **20 cm 格**对齐：分段交界、pivot 与包围盒边缘都取 20 的倍数，否则与体素件叠放错位。
- **`self_union(handle, bFillHoles, bTrimFlaps)` 的第二个布尔会毁几何**（2026-09-17）：`bTrimFlaps=True` 把凉亭半球穹顶的弧面塌成直弦（顶点 z 20→286 之间一个不剩，看起来"穹顶像圆锥"），也曾破坏矮栏杆法线出黑块。曲面构件一律用多壳重叠不并集；确需并集时传 `(False, False)`。
- **Python 的 `unreal.Rotator(...)` 构造顺序是 (roll, pitch, yaw)**，不是 C++ 的 (pitch, yaw, roll)（实测 `Rotator(10,20,30)` 读回 pitch=20 yaw=30 roll=10）；按 C++ 顺序传会把构件绕错轴（径向肋条被镜像到起拱面以下）。该旋转下局部轴：**X 沿子午线、Y 切向、Z 法线**，模板盒子要"深度在 X、宽度在 Y"。
- **旋成剖面一律用构件局部 z（0 = 底面）**：写成世界高度会让整个网格偏离 pivot，表现为"构件飘在半空 + 别处冒出一圈"。建完先读 `get_bounds()` 的本地 z 是否从 0 起，再摆场。
- **`generate_collision` 会给圆弧网格补一个超大的 sphere/sphyl/taper 形状**：穹顶因此从地面垂到穹顶、堵死整个建筑内部（玩家进不去）。壳体与环的正确口径是**清空简单碰撞 + `CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE`**（三角面即碰撞体，内部通透、子弹照常命中）；盒子类构件才用逐壳 `AlignedBoxes`。生成后**必须读回形状计数**确认。改资产后运行中的 actor 要 `set_collision_enabled(NO_COLLISION)`→`QUERY_AND_PHYSICS` 重建物理状态才会生效。
- **拆装多壳体网格用 `select_connected(handle, name, point)`**：打一个"只有目标壳体才包含"的点（圆盘的空角处），选不中即自检；`selection_bounds` 在该绑定里返回空，别用它校验选区，改用 `selection_count` + 删除后 `get_mesh_info` 的边界反推。**按 z 分带 + 半宽判断"方形"会把同宽圆盘也算进去**（Ø80 圆盘半宽同样是 40，只有对角半径 56.5 区分得出）。
