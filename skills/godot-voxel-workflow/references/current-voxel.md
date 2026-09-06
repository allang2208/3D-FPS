# 2026-09-06 本地体素案例

这些定位来自 E:/3d/3-dfps 本地工作区。工作流独立发布，以下运行代码不保证在相同远端提交中存在；缺失时先核实当前任务目录，不自动复制其他工作区。

| 责任 | 本地相对路径 / 参数 |
|---|---|
| 格子和碰撞 | scripts/building/block_grid.gd；CELL_SIZE=.5 |
| 放置与保存 | scripts/building/build_system.gd；材质注册和impact_surface一起接入 |
| 支撑 | scripts/building/support_graph.gd；地基0，上行不增代价，水平每格+1，最大4，不向下传播 |
| 圆角 | scripts/building/wood_block_mesh.gd；木石共用，当前半径.036米、每外露边11个切面，邻接缓存 |
| 木材 | generated_wood_material.gd；wood_generated_v3/oak_albedo.png，实际1254平方，非独立端面贴图 |
| 石灰岩 | stone_material.gd；stone_voxel_v1/limestone_albedo.png |
| 大理石 | marble_material.gd；复用sky_base/marble.gdshader，新块启用fine_slab_detail，旧场景默认不变 |
| 面板 | scripts/building/build_panel.gd；CATALOG选择，build_requested确认 |
| 相机平滑 | scripts/stair_camera_spring.gd、camera_fx.gd；临界阻尼ω18，约270ms收束95% |

现存ID：floor/wall/ceiling、stone_floor/stone_wall/stone_ceiling、marble。大理石为一个通用块，旧类型未合并。材料当前不消耗；共享承重图不模拟不同材料重量或应力破坏。悬挑上限沿支撑路径累计，竖向延伸不重置水平代价。存档使用独立.sky-building后缀和cell_size校验。

本地工具在tools/sky-base：test_wood_edges、test_voxel_steps、test_stair_camera、test_wood_building、test_stone_building。render_build_thumbnails用BUILD_THUMB_ONLY=marble只更新大理石；render_wood_edges使用WOOD_MATERIAL=generated/stone/marble。测试先设置独立存档；全屏切换为窗口后等待数帧，再设尺寸，检查实际值，否则截图可能仍为2560宽。

废案经验：早期程序木材和Wood Table Worn v2的斑点使用户感觉像泥土；以v3顺纹橡木替代。源素材和许可保留用于溯源，淘汰的派生实现与中间预览可在解除引用后删除，不能把历史方案写成当前材质。
