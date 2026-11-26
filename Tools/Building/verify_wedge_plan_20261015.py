import unreal as u
# 楔形切割回归:DebugShapePlan(四态旋转)与既有 DebugShapeCells(两态)双验
ok = True

def plan(shape, rot):
    cells, cuts = u.VoxelBuildComponent.debug_shape_plan(shape, rot)
    return [(c.x, c.y, c.z) for c in cells], list(cuts)

def make(d, p): return 1 + (((d - 1) & 3) | (p << 2))

# 45° 1×5 rot0: 一层薄壳只放顶格 (x,0,x)，5 格全部 +X 切(make(1,0)=1)
single = [(x, 0, x) for x in range(5)]
cells, cuts = plan(5, 0)
ok &= sorted(cells) == sorted(single)
for (x, y, z), c in zip(cells, cuts):
    ok &= c == 1
u.log('[wp] 45 rot0 cells=%d cuts_nonzero=%d' % (len(cells), sum(1 for c in cuts if c)))

# 45° rot2(180°): 镜像单层 (x,0,4-x)，全部 -X 切(make(2,0)=2)
cells, cuts = plan(5, 2)
ok &= sorted(cells) == sorted([(x, 0, 4 - x) for x in range(5)])
for (x, y, z), c in zip(cells, cuts):
    ok &= c == 2
u.log('[wp] 45 rot2 cells=%d cuts_nonzero=%d' % (len(cells), sum(1 for c in cuts if c)))

# 45° rot1(90° swap): 单层沿 Y 轴 (0,y,y)，全部 +Y 切(make(3,0)=3)
cells, cuts = plan(5, 1)
ok &= sorted(cells) == sorted([(0, y, y) for y in range(5)])
for (x, y, z), c in zip(cells, cuts):
    ok &= c == 3

# 2×5 坡: 一层 10 格，全部切割
cells, cuts = plan(6, 0)
ok &= len(cells) == 10 and sum(1 for c in cuts if c) == 10

# 26° 1×5 rot0: 实心三角(z<=x//2,9格) + 列顶格 pattern 5(下,x偶)/9(上,x奇)
tri26 = [(x, 0, z) for x in range(5) for z in range(x // 2 + 1)]
cells, cuts = plan(7, 0)
ok &= sorted(cells) == sorted(tri26)
for (x, y, z), c in zip(cells, cuts):
    expect = 0 if z != x // 2 else (5 if x % 2 == 0 else 9)
    ok &= c == expect
u.log('[wp] 26 rot0 cells=%d cuts_nonzero=%d' % (len(cells), sum(1 for c in cuts if c)))

# 26° rot2 镜像:三角(z<=(4-x)//2),列顶 cut= -X 向,pattern 按模板 x=4-x' 奇偶
cells, cuts = plan(7, 2)
tri26m = [(x, 0, z) for x in range(5) for z in range((4 - x) // 2 + 1)]
ok &= sorted(cells) == sorted(tri26m)
for (x, y, z), c in zip(cells, cuts):
    t = 4 - x
    expect = 0 if z != t // 2 else (make(2, 1) if t % 2 == 0 else make(2, 2))
    ok &= c == expect
u.log('[wp] 26 rot2 cells=%d cuts_nonzero=%d' % (len(cells), sum(1 for c in cuts if c)))

# 既有两态出口不受扰:45 rot=false 与 plan(5,0) 同构
cells_old = u.VoxelBuildComponent.debug_shape_cells(5, False)
ok &= sorted((c.x, c.y, c.z) for c in cells_old) == sorted((x, 0, x) for x in range(5))

# Box 回归:墙面仍 25 格全 0 切
cells, cuts = plan(2, 0)
ok &= len(cells) == 25 and set(cuts) == {0}

u.log('[wp] ALL=%s' % ('PASS' if ok else 'FAIL'))
