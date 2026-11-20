"""Build Lin Zhi's open panto frames on her assembled resting head (Blender cm, -Y forward)."""
from math import cos, pi, sin
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SOURCE = Path(__file__).resolve().parents[3] / "SourceAssets/VillageHerbalist/FullBody/HeadR3"


class _Surface:
    def __init__(self, objects):
        self.parts = []
        self.swatches = {}
        for obj in objects:
            if obj.type != "MESH":
                continue
            mesh = obj.data
            mesh.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in mesh.vertices]
            tris = [(tuple(t.vertices), tuple(t.loops), t.material_index) for t in mesh.loop_triangles]
            if not tris:
                continue
            tree = BVHTree.FromPolygons(points, [t[0] for t in tris], all_triangles=True)
            uv = mesh.uv_layers.active
            colors = []
            for slot in obj.material_slots:
                mat = slot.material
                image = None
                if mat and mat.node_tree:
                    shader = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                    if shader and shader.inputs["Base Color"].links:
                        node = shader.inputs["Base Color"].links[0].from_node
                        if node.type == "TEX_IMAGE":
                            image = node.image
                if image and image not in self.swatches:
                    # An expendable small copy keeps the original packed face atlas intact.
                    small = image.copy()
                    small.scale(512, 512)
                    pixels = np.empty(512 * 512 * 4, dtype=np.float32)
                    small.pixels.foreach_get(pixels)
                    self.swatches[image] = pixels.reshape(512, 512, 4)
                    bpy.data.images.remove(small)
                colors.append(self.swatches.get(image))
            self.parts.append((tree, points, tris, uv, colors))
        self.top = max(p.z for _, points, *_ in self.parts for p in points)

    def hit(self, origin, direction, color=False):
        closest = None
        best = float("inf")
        for part in self.parts:
            loc, _, idx, distance = part[0].ray_cast(origin, direction)
            if loc is not None and distance < best:
                closest = loc, idx, part
                best = distance
        if not closest:
            return None, None
        loc, idx, (_, pts, tris, uv, images) = closest
        vi, loops, mi = tris[idx]
        if not color or uv is None or mi >= len(images) or images[mi] is None:
            return loc, None
        a, b, c = [pts[i] for i in vi]
        e, f, g = b - a, c - a, loc - a
        ee, ef, ff = e.dot(e), e.dot(f), f.dot(f)
        det = ee * ff - ef * ef
        if abs(det) < 1e-12:
            return loc, None
        s = (ff * g.dot(e) - ef * g.dot(f)) / det
        t = (ee * g.dot(f) - ef * g.dot(e)) / det
        ua, ub, uc = [uv.data[i].uv for i in loops]
        u, v = ua * (1 - s - t) + ub * s + uc * t
        rgb = images[mi][int((v % 1) * 512), int((u % 1) * 512), :3]
        return loc, float(rgb @ [0.2126, 0.7152, 0.0722])

    def front(self, x, z, color=False):
        return self.hit((x, -80, z), (0, 1, 0), color)

    def depth(self, x, z):
        p, _ = self.front(x, z)
        return p.y if p is not None else None


def _face_anchors(surf, mid):
    # Find the projecting tip relative to the two adjacent nasal sidewalls.
    tips = []
    for z in np.arange(surf.top - 17.7, surf.top - 12.1, .22):
        for x in np.arange(mid - 1.1, mid + 1.11, .20):
            center = surf.depth(x, z)
            walls = [surf.depth(x + side * 1.9, z) for side in (-1, 1)]
            if center is not None and None not in walls:
                prominence = min(walls) - center
                tips.append((prominence - .07 * (z - surf.top + 15.1)**2 - .16 * (x-mid)**2, x, z))
    if not tips:
        raise ValueError("Cannot locate the nasal profile on the assembled Lin Zhi head")
    _, nose_x, nose_z = max(tips)
    eyes = []
    for side in (-1, 1):
        candidates = []
        for offset in np.arange(2.56, 3.70, .09):
            x = nose_x + side * offset
            for dz in np.arange(2.54, 4.19, .09):
                z = nose_z + dz
                hit, lum = surf.front(x, z, True)
                if hit is None:
                    continue
                score = -.19 * ((offset - 3.12)**2 + (dz - 3.25)**2)
                if lum is not None:
                    near = [surf.front(x+dx, z+dy, True)[1] for dx, dy in
                            ((-.57, .02), (.57, .02), (0, .48), (0, -.48))]
                    if None not in near:
                        score += (np.mean(near) - lum) / max(.07, np.mean(near))
                candidates.append((score, x, z))
        if not candidates:
            raise ValueError("Cannot locate both orbital surfaces on the assembled head")
        strongest = max(candidates)[0]
        cluster = np.array([(x, z) for value, x, z in candidates if strongest-value < .055])
        eyes.append(tuple(cluster.mean(axis=0)))
    return nose_x, eyes


def _ear_support(surf, side, eye, depth, separation):
    ex, ez = eye
    center = depth + separation * 1.53
    _, cheek = surf.front(ex, ez - 1.6, True)
    sites = []
    for y in np.arange(center - 1.9, center + 2.05, .22):
        for z in np.arange(ez - .95, ez + 1.50, .17):
            p, lum = surf.hit((side * 45, y, z), (-side, 0, 0), True)
            if p is None:
                continue
            # The exposed upper helix, just below the darker hairline.
            skin = 0.0 if lum is None or cheek is None else min(lum/max(cheek, .025), 1.)
            score = 1.35*skin + .19*side*(p.x-ex) - .12*(y-center)**2 - .42*(z-ez-.54)**2
            sites.append((score, p))
    if not sites:
        raise ValueError("Cannot fit the spectacle temples to both sides of the assembled head")
    _, p = max(sites, key=lambda s: s[0])
    return Vector((p.x+side*.09, p.y, p.z+.09))


class _Tubing:
    def __init__(self):
        self.verts, self.faces, self.uv = [], [], []

    def face(self, ids, uv):
        self.faces.append(ids)
        self.uv.extend(uv)

    def tube(self, points, radii, guide, phase, closed=False):
        pts = [Vector(p) for p in points]
        rings = []
        distance = [0.]
        sides = 10
        for i, p in enumerate(pts):
            nxt = pts[(i+1) % len(pts)] if closed or i+1 < len(pts) else p
            prev = pts[i-1] if closed or i else p
            tangent = (nxt-prev).normalized()
            a = (guide - tangent * guide.dot(tangent)).normalized()
            b = tangent.cross(a)
            ra, rb = radii[i]
            rings.append(len(self.verts))
            for k in range(sides):
                angle = 2*pi*k/sides
                self.verts.append(p + ra*cos(angle)*a + rb*sin(angle)*b)
            distance.append(distance[-1] + (nxt-p).length)
        for i in range(len(pts) if closed else len(pts)-1):
            n = (i+1) % len(pts)
            u0, u1 = phase + distance[i]/7.5, phase + distance[i+1]/7.5
            for k in range(sides):
                j = (k+1) % sides
                v0, v1 = k/sides, (k+1)/sides
                self.face((rings[i]+k, rings[i]+j, rings[n]+j, rings[n]+k),
                          ((u0,v0),(u0,v1),(u1,v1),(u1,v0)))
        if not closed:
            for start, ring in ((True, rings[0]), (False, rings[-1])):
                seq = list(reversed(range(sides))) if start else list(range(sides))
                self.face([ring+k for k in seq], [(phase+.02*cos(2*pi*k/sides),.5+.3*sin(2*pi*k/sides)) for k in seq])


def _curve(keys, radii, steps=5):
    """Catmull-Rom center line through the hinge, ear support and bent end."""
    pts = [Vector(p) for p in keys]
    result, widths = [], []
    for i in range(len(pts)-1):
        a, b = pts[i], pts[i+1]
        prev, nxt = pts[max(0,i-1)], pts[min(i+2,len(pts)-1)]
        for j in range(steps):
            t = j/steps
            result.append(.5*((2*a) + (-prev+b)*t + (2*prev-5*a+4*b-nxt)*t*t +
                                (-prev+3*a-3*b+nxt)*t*t*t))
            widths.append(tuple(x+(y-x)*t for x,y in zip(radii[i],radii[i+1])))
    return result+[pts[-1]], widths+[radii[-1]]


def add_spectacles(head_objects, rig):
    """Return one rigged mesh, in the same world space as the supplied head objects."""
    bpy.context.view_layer.update()
    surf = _Surface(head_objects)
    head_bone = next(b for b in rig.data.bones if b.name.lower().replace("_","").endswith("head"))
    mid, eyes = _face_anchors(surf, (rig.matrix_world @ head_bone.head_local).x)
    separation = eyes[1][0] - eyes[0][0]
    eye_z = .5*(eyes[0][1]+eyes[1][1])
    shapes = _Tubing()
    guide_front, guide_up = Vector((0,1,0)), Vector((0,0,1))
    bridges = []
    for idx, (side, (ex, ez)) in enumerate(zip((-1,1), eyes)):
        ez = .5*(ez+eye_z)
        cx, cz = ex+side*.030*separation, ez-.108*separation
        rx, rz = .406*separation, .330*separation

        def rim_xz(theta):
            h, v = cos(theta), sin(theta)
            return cx+side*rx*(h*(1+.047*v)+.028*v), cz+rz*v*(1.0-.046*abs(h))

        def wrap(x,z):
            return .14*abs(x-mid) - .10*(z-ez)

        clearance = []
        for theta in np.linspace(0,2*pi,72,endpoint=False):
            x,z = rim_xz(theta)
            y = surf.depth(x,z)
            if y is not None:
                clearance.append(y-wrap(x,z)-.22)
        orbit = surf.depth(ex,ez)
        base = min(min(clearance), orbit-wrap(ex,ez)-.74)

        def rim(theta):
            x,z = rim_xz(theta)
            return Vector((x,base+wrap(x,z),z))

        angles = np.linspace(0,2*pi,64,endpoint=False)
        shapes.tube([rim(t) for t in angles],[(.117,.100+.023*sin(t)) for t in angles],
                    guide_front,.27+idx*.42,closed=True)
        bridges.append(rim(pi-.49))

        # Slightly thickened inside the two nose contacts, as in acetate frames.
        seat0, seat1 = rim(pi-.02), rim(pi+.29)
        pad = (seat0+seat1)*.5
        pad.x -= side*.09
        skin = surf.depth(pad.x,pad.z)
        if skin is not None:
            back = pad.copy()
            back.y = max(pad.y+.05,skin-.03)
            pts, rr = _curve((seat0,pad,back,seat1),
                             ((.07,.065),(.10,.105),(.09,.12),(.065,.065)),4)
            # This saddle curls in depth; its long vertical axis stays stable.
            shapes.tube(pts,rr,Vector((side,0,0)),.59)

        hinge = rim(.46)
        ear = _ear_support(surf, side, (ex,ez), orbit, separation)
        temple_x = max(side*hinge.x+.30, side*ear.x-.20)*side
        bend = hinge.copy()
        bend.x += side*.32
        bend.y += .23
        keys = [hinge,bend,
                (temple_x,hinge.y+1.35,hinge.z+.025),
                (temple_x+(ear.x-temple_x)*.5,hinge.y+(ear.y-hinge.y)*.53,(ear.z+hinge.z)*.5),
                ear,
                (ear.x-side*.04,ear.y+1.04,ear.z-.24),
                (ear.x-side*.25,ear.y+1.90,ear.z-1.08),
                (ear.x-side*.47,ear.y+2.32,ear.z-1.83),
                (ear.x-side*.53,ear.y+2.40,ear.z-1.95)]
        pts, rr = _curve(keys,((.13,.085),(.17,.104),(.14,.085),(.105,.076),
                              (.105,.078),(.114,.080),(.145,.092),(.12,.085),(.060,.045)))
        shapes.tube(pts,rr,guide_up,.10+idx*.33)

    left, right = bridges
    bridge_z = max(left.z,right.z)+.34
    nose = surf.depth(mid,bridge_z)
    center_y = min((left.y+right.y)*.5, nose-.12) if nose is not None else (left.y+right.y)*.5
    crown = Vector((mid,center_y,bridge_z))
    keys = [left,left.lerp(crown,.47)+Vector((0,0,.10)),crown,
            right.lerp(crown,.47)+Vector((0,0,.10)),right]
    pts,rr = _curve(keys,((.115,.115),(.105,.108),(.105,.098),(.105,.108),(.115,.115)),5)
    shapes.tube(pts,rr,guide_front,.44)

    mesh = bpy.data.meshes.new("LinZhi_SpectacleFrames")
    mesh.from_pydata(shapes.verts,[],shapes.faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv",np.asarray(shapes.uv,dtype=np.float32).ravel())
    mesh.polygons.foreach_set("use_smooth",np.ones(len(mesh.polygons),dtype=bool))
    obj = bpy.data.objects.new("LinZhi_SpectacleFrames",mesh)
    bpy.context.collection.objects.link(obj)
    mat = bpy.data.materials.get("M_LinZhiFrames") or bpy.data.materials.new("M_LinZhiFrames")
    mat.use_nodes = True
    mat.diffuse_color = (.062,.028,.014,1.)
    shader = next(n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = .29
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(SOURCE/"T_LinZhiFrames_Color.png"),check_existing=True)
    mat.node_tree.links.new(tex.outputs["Color"],shader.inputs["Base Color"])
    mesh.materials.append(mat)
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted_safe()
    group = obj.vertex_groups.new(name=head_bone.name)
    group.add(list(range(len(mesh.vertices))),1.,"REPLACE")
    armature = obj.modifiers.new("Follow head","ARMATURE")
    armature.object = rig
    return [obj]
