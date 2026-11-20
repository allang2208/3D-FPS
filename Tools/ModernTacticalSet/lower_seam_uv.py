"""Give the narrow side walls of sewn panels a tileable UV chart on import."""
import math


REVISION = "SeamWalls01"


def unfold_sidewalls(data, prefix, repeat_cm):
    # The face and reverse of the same piece share a cloth pattern. At their
    # joins the original pattern sometimes maps all three corners onto a line.
    # Keep the longest existing texture edge and open the third corner using
    # the signed local frame of the piece, at its actual material repeat size.
    count = 0
    slots = data["material_slots"]
    for i, (face, slot) in enumerate(zip(data["triangles"], data["triangle_materials"])):
        if not slots[slot].startswith(prefix):
            continue
        uv = data["uv"][i]
        a, b, c = uv
        area = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        if abs(area) > 2.e-9:
            continue
        p = [data["positions"][v] for v in face]
        e = [p[1][j]-p[0][j] for j in range(3)]
        f = [p[2][j]-p[0][j] for j in range(3)]
        cross = [e[1]*f[2]-e[2]*f[1], e[2]*f[0]-e[0]*f[2], e[0]*f[1]-e[1]*f[0]]
        size = math.hypot(*cross)
        if size < 2.e-8:
            continue
        # Consistent projection across a coplanar strip, including UV-less
        # end caps. Fractional tile phase is retained along the primary edge.
        axis = max(range(3), key=lambda j:abs(cross[j]))
        axes = ((1, 2), (2, 0), (0, 1))[axis]
        pairs = ((0,1,2), (1,2,0), (2,0,1))
        first, second, last = max(pairs, key=lambda t:math.dist(uv[t[0]],uv[t[1]]))
        du = uv[second][0]-uv[first][0]
        dv = uv[second][1]-uv[first][1]
        stride = math.hypot(du,dv)
        if stride < 1.e-6:
            data["uv"][i] = [[v[axes[0]]/repeat_cm, v[axes[1]]/repeat_cm] for v in p]
        else:
            length = math.dist(p[second],p[first])
            if length < 1.e-7:
                data["uv"][i] = [[v[axes[0]]/repeat_cm, v[axes[1]]/repeat_cm] for v in p]
            else:
                height = math.copysign(size/(length*repeat_cm),cross[axis])
                uv[last] = [uv[last][0]-dv/stride*height,uv[last][1]+du/stride*height]
        count += 1
    return count
