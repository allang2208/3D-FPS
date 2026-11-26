import unreal as u
# 决定性验证:DebugShapeCells 直接核对 FillBrush 的格子排列(同真源 ShapeCells)
def show(name, cells):
    zs = {}
    for c in cells:
        zs.setdefault(c.z, []).append(c.x)
    u.log('[shape] %s n=%d' % (name, len(cells)))
    for z in sorted(zs, reverse=True):
        u.log('[shape]   z=%d x=%s' % (z, sorted(zs[z])))
ok = True
cells45 = u.VoxelBuildComponent.debug_shape_cells(5, False)
# 2026-10-19 第三轮（用户指定一层薄壳）：45° 1×5 只放坡面顶格 (x,0,x)，共 5 格；
# 下方不填。台阶处缝隙是单层切割固有，支撑靠 20×20 共面坡棱接缝。
single45 = sorted((x, z) for x in range(5) for z in [x])
ok &= len(cells45) == 5 and sorted((c.x, c.z) for c in cells45) == single45
show('45deg-slope(5)', cells45)
cells26 = u.VoxelBuildComponent.debug_shape_cells(7, False)
tri26 = sorted((x, z) for x in range(5) for z in range(x // 2 + 1))
ok &= sorted((c.x, c.z) for c in cells26) == tri26
show('26deg-slope(7)', cells26)
cellsg = u.VoxelBuildComponent.debug_shape_cells(9, False)
ok &= len(cellsg) == 25 and max(c.z for c in cellsg) == 4
show('gable(9) rows', cellsg)
cellsp = u.VoxelBuildComponent.debug_shape_cells(10, False)
ok &= len(cellsp) == 35
show('pyramid(10)', cellsp)
# R 旋转:45°坡 swap 后仍是一层，沿 YZ 的 Y 轴爬升 (z==y)
cells45r = u.VoxelBuildComponent.debug_shape_cells(5, True)
single_r = sorted((y, z) for y in range(5) for z in [y])
ok &= sorted((c.y, c.z) for c in cells45r) == single_r
# Box 回归:墙面形状仍是实心 25 格
cellsbox = u.VoxelBuildComponent.debug_shape_cells(2, False)
ok &= len(cellsbox) == 25
u.log('[shape] BOX regression n=%d' % len(cellsbox))
u.log('[shape] ALL=%s' % ('PASS' if ok else 'FAIL'))
