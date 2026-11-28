"""Gatehouse masonry fitted to the deployed wall-walk, crenels and nine breakaway bays."""
import math
from pathlib import Path
import sys

from battlement_profile import MERLONS
from chapel_gatehouse import Kit, STONE, CAP, PAVING, FOOTING
import source_mesh


class CurtainKit(Kit):
    def triangle(self, a, b, c, material, offset=(0., 0.)):
        super().triangle(a, b, c, material, offset)
        group = self.groups[material]
        if material not in (STONE,FOOTING) or abs(group['normals'][-1][1]) < .8:
            return
        # Ease the scan across broad elevations so a distinctive stone does not
        # repeat in a rigid grid. At the snap planes both displacement and slope
        # are zero. Fractured surfaces use the intact wall's local coordinates.
        for uv, (x, _, z) in zip(group['uv0'][-3:], (a,b,c)):
            if material == FOOTING:
                # Three complete repeats per bay join the chapel scan at both snap planes.
                uv[0] = self.phase[0] + x / 100.
            fade = math.cos(math.pi * x / 300.) ** 2
            uv[0] += fade * (.026 * math.sin(.018*x + .016*z) + .016 * math.sin(.032*z - .011*x))
            uv[1] += fade * (.018 * math.sin(.014*x - .019*z) + .009 * math.sin(.026*x + .013*z))


def wall_point(column, course, side):
    # Every third column and fourth bed is a buried fracture joint. Positions
    # coincide on both shards. Only the outside skin is used on the standing wall.
    x = -150. + column * (300. / 9)
    z = -28. + course * (388. / 12)
    if column not in (0, 9) and course != 12:
        x += 6. * math.sin(course * 1.3 + column * .82 + side * .75)
    if course not in (0, 12):
        z += 5. * math.sin(column * 1.52 + course * .87 + side * .42)
    # A restrained batter catches the light at the foot. The heavy joints and
    # the smaller relief above it come directly from the same scan as the keep.
    batter = 1. + 1.8 * max(0., 1. - max(z, 0.) / 95.)
    wear = .85 * math.sin(column * math.pi / 9) * math.sin(course * .82 + column + side)
    base_y = 96.8 if side < 0 else 163.8
    y = side * (base_y + batter + wear)
    return (x, y, z)


def quad(mesh, vertices, mat):
    a, b, c, d = vertices
    mesh.triangle(a, b, c, mat)
    mesh.triangle(a, c, d, mat)


def masonry_body(wall, shards):
    for iz in range(12):
        for ix in range(9):
            shard = shards[(iz // 4) * 3 + ix // 3]
            f = [wall_point(x, z, -1) for x, z in ((ix,iz),(ix+1,iz),(ix+1,iz+1),(ix,iz+1))]
            b = [wall_point(x, z, 1) for x, z in ((ix,iz),(ix+1,iz),(ix+1,iz+1),(ix,iz+1))]
            for mesh in (wall, shard):
                facing = FOOTING if iz < 2 else STONE
                quad(mesh, f, facing)
                quad(mesh, b[::-1], facing)
            # Core faces are emitted once per boundary, using identical triangle
            # diagonals on both fragments so the assembled cross-section closes.
            edges = [
                ([f[0],b[0],b[3],f[3]], ix == 0, ix % 3 == 0, True, STONE),
                ([f[1],b[1],b[2],f[2]], ix == 8, ix % 3 == 2, False, STONE),
                ([f[0],f[1],b[1],b[0]], iz == 0, iz % 4 == 0, True, STONE),
                ([f[3],f[2],b[2],b[3]], iz == 11, iz % 4 == 3, False,
                 PAVING if iz == 11 else STONE)]
            for face, outside, fracture, flip, mat in edges:
                if flip:
                    face = [face[0],face[3],face[2],face[1]]
                if outside:
                    quad(wall, face, FOOTING if iz < 2 and mat == STONE else mat)
                if fracture:
                    quad(shard, face, FOOTING if outside and iz < 2 and mat == STONE else mat)


def course(mesh, left, right, levels, mat, bevel_ends=False):
    rings = []
    for z, front, back, inset in levels:
        # Keep the end half-merlons flush where two placed bays form one merlon.
        a = left + (inset if bevel_ends and left > -150. else 0.)
        b = right - (inset if bevel_ends and right < 150. else 0.)
        rings.append([(a,front,z),(b,front,z),(b,back,z),(a,back,z)])
    mesh.solid(rings, mat)


def crown(wall, shards):
    # The front face has a shallow drip and the wall walk a slim edge course.
    # Carry continuous mouldings through each upper fragment on the same joint.
    divisions = [-150., wall_point(3,12,-1)[0], wall_point(6,12,-1)[0], 150.]
    strips = [
        ([(341.,-97.5,-88.,0.),(345.,-101.,-88.,0.),(351.,-101.,-88.,0.),
          (353.,-99.,-88.,0.)], CAP),
        ([(351.,158.,165.,0.),(354.,158.,167.,0.),(358.,158.,167.,0.),
          (359.7,158.,165.8,0.)], CAP),
        ([(359.5,-97.5,-52.,0.),(388.,-97.5,-52.,0.)], STONE),
        ([(388.,-97.5,-52.,0.),(390.,-100.,-50.,0.),(393.,-100.,-50.,0.),
          (395.,-97.,-52.,0.)], CAP)]
    for levels, mat in strips:
        course(wall,-150.,150.,levels,mat)
        for col, (a,b) in enumerate(zip(divisions,divisions[1:])):
            course(shards[6+col],a,b,levels,mat)
    for col,(a,b) in enumerate(MERLONS):
        for mesh in (wall, shards[6+col]):
            course(mesh,a,b,[(394.5,-96.,-53.,0.),(465.,-94.8,-54.,1.)],STONE,True)
            # Capstone overhangs toward the countryside and the walk. At the
            # modular seam there is no doubled chamfer or groove.
            l, r = max(-150.,a-2.), min(150.,b+2.)
            course(mesh,l,r,[(465.,-96.,-53.,2.),(468.,-99.,-50.,0.),
                             (476.,-99.,-50.,0.),(479.,-96.,-53.,2.)],CAP,True)


def build(output):
    source_mesh.OUT = Path(output)
    source_mesh.OUT.mkdir(parents=True,exist_ok=True)
    wall = CurtainKit(3857)
    shards = [CurtainKit(3857) for _ in range(9)]
    masonry_body(wall, shards)
    crown(wall, shards)
    # Retain the shipped five-box character, stair-snap and placement profile.
    wall.collision(-150.,150.,-100.,167.,-28.,360.)
    wall.collision(-150.,150.,-98.,-52.,351.,393.)
    for a,b in MERLONS:
        wall.collision(a,b,-96.,-53.,392.,479.)
    wall.save('SM_HighWall')
    for index, mesh in enumerate(shards):
        mesh.save(f'SM_HighWallShard_{index:02d}')


if __name__ == '__main__':
    build(sys.argv[1])
