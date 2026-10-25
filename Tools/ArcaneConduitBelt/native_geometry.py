import bpy,bmesh,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path("D:/FPS3D/FPSGAME");R=P/"SourceAssets/ArcaneConduitBelt20261025/ModelR1";E=R/"Exports";TAU=math.tau


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def bv(p):return Vector((p[0]*.01,-p[1]*.01,p[2]*.01))

def unit(v):return np.asarray(v)/max(float(np.linalg.norm(v)),1.e-12)

def smooth_circular(v,sigma=2):
    k=np.arange(-int(sigma*3),int(sigma*3)+1);w=np.exp(-.5*(k/sigma)**2);w/=w.sum()
    return sum(np.roll(v,int(i),axis=0)*q for i,q in zip(k,w))

def bary(p,tri):
    a,b,c=tri;v0=b-a;v1=c-a;v2=p-a;d00=v0@v0;d01=v0@v1;d11=v1@v1;den=max(d00*d11-d01*d01,1.e-15)
    v=(d11*(v2@v0)-d01*(v2@v1))/den;w=(d00*(v2@v1)-d01*(v2@v0))/den
    q=np.maximum([1-v-w,v,w],0);return q/max(q.sum(),1.e-12)

class Cap:

    def mesh(self, name, points, faces, mat=0, uv=None, slots=None, col=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata([bv(p) for p in points], [], [list(reversed(f)) for f in faces])
        me.update()
        ob = bpy.data.objects.new(name, me)
        (col or self.cols[('01_EDITABLE_LOD0', '02_EXPORT_LOD1', '03_EXPORT_LOD2')[self.level]]).objects.link(ob)
        for m in self.mats:
            me.materials.append(m)
        if uv is None:
            uv = [(p[0] / 4, p[1] / 4) for p in points]
        layer = me.uv_layers.new(name='UV0_PhysicalScale')
        for i, poly in enumerate(me.polygons):
            poly.use_smooth = True
            poly.material_index = slots[i] if slots else mat
            for li, vi in zip(poly.loop_indices, poly.vertices):
                layer.data[li].uv = uv[vi]
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(me)
        bm.free()
        if col is None:
            self.objects.append(ob)
        ob['source_units'] = 'centimetres mapped to Blender metres'
        return ob

    def solid(self, ob, cm, inner_mat=None):
        mod = ob.modifiers.new('Physical sewn thickness', 'SOLIDIFY')
        mod.thickness = cm * 0.01
        mod.offset = -1
        mod.use_even_offset = True
        if inner_mat is not None:
            mod.material_offset = inner_mat
        return ob

    def tube(self, name, paths, radius, mat, sides=6, closed=False):
        ps = []
        uv = []
        fs = []
        for path in paths:
            path = np.asarray(path)
            start = len(ps)
            n = len(path)
            arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
            for j, p in enumerate(path):
                tangent = unit(path[(j + 1) % n] - path[(j - 1) % n]) if closed else unit(path[min(n - 1, j + 1)] - path[max(0, j - 1)])
                ref = np.array([0.0, 0.0, 1.0]) if abs(tangent[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
                u = unit(np.cross(tangent, ref))
                v = np.cross(tangent, u)
                for k in range(sides):
                    ps.append(p + radius * (u * math.cos(TAU * k / sides) + v * math.sin(TAU * k / sides)))
                    uv.append((TAU * radius * k / sides / 4, arc[j] / 4))
            for j in range(n if closed else n - 1):
                for k in range(sides):
                    fs.append([start + j * sides + k, start + j * sides + (k + 1) % sides, start + (j + 1) % n * sides + (k + 1) % sides, start + (j + 1) % n * sides + k])
            if not closed:
                fs.append([start + k for k in reversed(range(sides))])
                fs.append([start + (n - 1) * sides + k for k in range(sides)])
        return self.mesh(name, ps, fs, mat, uv)

    def ribbon(self, name, path, normals, width, mat, thickness=0.035):
        ps = []
        uv = []
        fs = []
        arc = 0.0
        for i, p in enumerate(path):
            if i:
                arc += float(np.linalg.norm(p - path[i - 1]))
            tangent = unit(path[min(len(path) - 1, i + 1)] - path[max(0, i - 1)])
            side = unit(np.cross(normals[i], tangent))
            for sign in (-1, 1):
                ps.append(p + side * width * 0.5 * sign)
                uv.append(((sign + 1) * width / 8, arc / 4))
        for i in range(len(path) - 1):
            fs.append([i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2])
        return self.solid(self.mesh(name, ps, fs, mat, uv), thickness)

    def stitch(self, name, path, normals, mat=7, pitch=0.28, radius=0.014):
        if self.level == 2:
            return
        p = np.asarray(path)
        normals = np.asarray(normals)
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
        paths = []
        for s in np.arange(0.1, arc[-1] - 0.13, pitch):
            line = []
            for phase in np.linspace(0, 1, 4 if self.level == 0 else 3):
                at = min(s + phase * 0.17, arc[-1])
                i = min(len(p) - 2, max(0, np.searchsorted(arc, at) - 1))
                t = (at - arc[i]) / max(arc[i + 1] - arc[i], 1e-09)
                point = p[i] * (1 - t) + p[i + 1] * t
                n = unit(normals[i] * (1 - t) + normals[i + 1] * t)
                line.append(point + n * (-0.006 + 0.028 * math.sin(math.pi * phase)))
            paths.append(line)
        if paths:
            self.tube(name, paths, radius, mat, 4 if self.level == 0 else 3)

    def rounded_rect(self, w, h, r, n=6):
        out = []
        for cx, cz, start in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
            for a in np.linspace(start, start + 90, n, endpoint=False):
                out.append([cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a))])
        return out

    def frame(self, name, center, w, h, innerw, innerh, depth, mat=4):
        outer = self.rounded_rect(w, h, min(0.18, h * 0.2), 8 if self.level == 0 else 5)
        inner = self.rounded_rect(innerw, innerh, min(0.12, innerh * 0.2), 8 if self.level == 0 else 5)
        ps = []
        fs = []
        n = len(outer)
        for y, ring in ((-depth / 2, outer), (-depth / 2, inner), (depth / 2, outer), (depth / 2, inner)):
            ps.extend([np.asarray(center) + [x, y, z] for x, z in ring])
        for i in range(n):
            k = (i + 1) % n
            fs.extend([[i, k, n + k, n + i], [2 * n + i, 3 * n + i, 3 * n + k, 2 * n + k], [i, 2 * n + i, 2 * n + k, k], [n + i, n + k, 3 * n + k, 3 * n + i]])
        ob = self.mesh(name, ps, fs, mat)
        bevel = ob.modifiers.new('Rounded moulded edges', 'BEVEL')
        bevel.width = 0.00018
        bevel.segments = 3 if self.level == 0 else 2
        return ob

    def box(self, name, center, size, mat=4, bevel=0.05):
        ps = [np.asarray(center) + np.array([sx, sy, sz]) * np.asarray(size) / 2 for sx, sy, sz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))]
        fs = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        ob = self.mesh(name, ps, fs, mat)
        b = ob.modifiers.new('Soft manufactured corners', 'BEVEL')
        b.width = bevel * 0.01
        b.segments = 3 if self.level == 0 else 2
        return ob

    def displace(self, ob, family):
        row = SURFACE[family]
        tex = bpy.data.textures.new(ob.name + '_Height', type='IMAGE')
        tex.image = bpy.data.images.load(str(R / 'Textures' / f'T_{family}_Height.png'), check_existing=True)
        tex.image.colorspace_settings.name = 'Non-Color'
        disp = ob.modifiers.new('Actual woven micro-relief', 'DISPLACE')
        disp.texture = tex
        disp.texture_coords = 'UV'
        disp.strength = row['height_range_m'][1] - row['height_range_m'][0]
        disp.mid_level = 0.5

SURFACES=read(R/"textures.json")["maps"];SURFACE={r["name"]:r for r in SURFACES}

class NativeBelt(Cap):

    def __init__(self, row):
        self.row = row
        self.body = row['body']
        self.native = read(row['native_reference'])
        self.bones = self.native['bones']
        self.bone_by = {x['name']: x for x in self.bones}
        self.body_points = np.array(self.native['positions'])
        self.body_faces = np.array(self.native['triangles'], dtype=np.int32)
        self.pants_points = np.fromfile(R / 'Inputs' / f'{self.body}_positions.bin', dtype='<f4').reshape(-1, 3)
        self.pants_faces = np.fromfile(R / 'Inputs' / f'{self.body}_triangles.bin', dtype='<i4').reshape(-1, 3)
        right = np.array(self.bone_by['thigh_r']['position']) - np.array(self.bone_by['thigh_l']['position'])
        right[2] = 0
        self.right = unit(right)
        forward = sum((np.array(self.bone_by['ball_' + s]['position']) - np.array(self.bone_by['foot_' + s]['position']) for s in ('l', 'r')))
        forward[2] = 0
        self.forward = unit(forward - self.right * (forward @ self.right))
        self.up = np.array([0.0, 0.0, 1.0])
        self.origin = np.array(self.bone_by['pelvis']['position'])
        self.origin[2] = 0
        self.fit_waist()
        z = self.top.mean()
        centers = self.body_points[self.body_faces].mean(1)
        self.weight_faces = self.body_faces[(centers[:, 2] > z - 17) & (centers[:, 2] < z + 8) & (np.abs(centers[:, 0] - self.origin[0]) < 32)]
        self.weight_tree = BVHTree.FromPolygons([Vector(p) for p in self.body_points], self.weight_faces.tolist(), all_triangles=True)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.unit_settings.system = 'METRIC'
        self.scene.unit_settings.scale_length = 1
        self.cols = {}
        for name in ('01_EDITABLE_LOD0', '02_EXPORT_LOD1', '03_EXPORT_LOD2', '04_RIGID_ATTACHMENT_MASTERS', '05_EXPORT_ASSEMBLY', '06_NATIVE_REFERENCES', '07_HIGH_SURFACE_SOURCES', '08_ATTACHMENT_ANCHORS'):
            col = bpy.data.collections.new(name)
            self.scene.collection.children.link(col)
            self.cols[name] = col
        self.objects = []
        self.mats = []
        self.level = 0
        self.active_frame = None
        self.active_weights = None
        self.active_kind = 'belt'
        self.weights = {}
        self.sockets = []
        for row in SURFACES:
            self.make_material(row)
        mat = bpy.data.materials.new('Arcane_SilverGrey_Thread')
        mat.use_nodes = True
        bs = mat.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (0.19, 0.20, 0.22, 1)
        bs.inputs['Roughness'].default_value = 0.87
        self.mats.append(mat)

    def fit_waist(self):
        ps = self.pants_points
        delta = ps - self.origin
        angles = np.mod(np.arctan2(delta @ self.right, delta @ self.forward), TAU)
        high = ps[:, 2].max()
        region = ps[:, 2] > high - 10.0
        tops = []
        count = 256
        for a in np.arange(count) * TAU / count:
            da = np.abs((angles - a + math.pi) % TAU - math.pi)
            sel = region & (da < 0.055)
            if not np.any(sel):
                sel = region & (da < 0.11)
            tops.append(float(ps[sel, 2].max()))
        self.top = smooth_circular(np.array(tops), 2.0)
        self.na = count
        self.height = 7.2
        geometry = BVHTree.FromPolygons([Vector(p) for p in ps], self.pants_faces.tolist(), all_triangles=True)
        radii = np.zeros((9, count))
        fallback = 0
        for j, v in enumerate(np.linspace(0, 1, 9)):
            for i, a in enumerate(np.arange(count) * TAU / count):
                direction = self.right * math.sin(a) + self.forward * math.cos(a)
                z = self.top[i] - 0.35 - self.height * (1 - v)
                start = self.origin + np.array([0, 0, z])
                travel = 0.0
                last = None
                for _ in range(16):
                    hit, normal, face, dist = geometry.ray_cast(Vector(start + direction * travel), Vector(direction), 40 - travel)
                    if hit is None:
                        break
                    travel = float((np.array(hit) - start) @ direction) + 0.008
                    last = travel
                    if travel >= 38:
                        break
                if last is None:
                    da = np.abs((angles - a + math.pi) % TAU - math.pi)
                    sel = (da < 0.09) & (np.abs(ps[:, 2] - z) < 1.2)
                    if not np.any(sel):
                        raise RuntimeError('Waist source has no surface at ' + str((self.body, a, z)))
                    last = float(np.max((ps[sel] - start) @ direction))
                    fallback += 1
                radii[j, i] = last
        self.radii = np.stack([np.maximum(smooth_circular(q, 2), q) + 0.32 for q in radii])
        pts = np.array([self.point(a, 0.5, 0) for a in np.linspace(0, TAU, 1025)])
        self.arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
        self.arc_angles = np.linspace(0, TAU, 1025)
        self.perimeter = float(self.arc[-1])
        self.fit_report = dict(body=self.body, pants_asset=self.row['pants_asset'], package_sha256=self.row['package_sha256'], front_axis=self.forward.tolist(), right_axis=self.right.tolist(), circumference_cm=self.perimeter, waist_width_cm=float(np.ptp(pts @ self.right)), waist_depth_cm=float(np.ptp(pts @ self.forward)), waist_top_range_cm=[float(self.top.min()), float(self.top.max())], belt_width_cm=self.height, source_samples=count * 9, nearby_surface_fallbacks=fallback, fit_tested=False)
        write(R / 'Authored' / f'{self.body}_waist_fit.json', self.fit_report)
        print('BELT_WAIST_AUTHORED', self.body, round(self.perimeter, 2), flush=True)

    def sample(self, array, a):
        f = a % TAU / TAU * self.na
        i = int(f) % self.na
        t = f - int(f)
        return array[i] * (1 - t) + array[(i + 1) % self.na] * t

    def point(self, a, v=0.5, offset=0):
        v = float(np.clip(v, 0, 1))
        j = min(7, int(v * 8))
        t = v * 8 - j
        radius = self.sample(self.radii[j], a) * (1 - t) + self.sample(self.radii[j + 1], a) * t
        direction = self.right * math.sin(a) + self.forward * math.cos(a)
        return self.origin + direction * (radius + offset) + self.up * (self.sample(self.top, a) - 0.35 - self.height * (1 - v))

    def angle(self, arc):
        return float(np.interp(arc % self.perimeter, self.arc, self.arc_angles))

    def outward(self, a):
        return unit(self.right * math.sin(a) + self.forward * math.cos(a))

    def frame_at(self, arc, offset=1.35):
        a = self.angle(arc)
        normal = self.outward(a)
        tangent = unit(self.point(a + 0.001) - self.point(a - 0.001))
        tangent = unit(tangent - self.up * (tangent @ self.up))
        return (self.point(a, 0.5, offset), np.stack((tangent, normal, self.up), axis=1))

    def native_weights(self, p):
        q, _, face, _ = self.weight_tree.find_nearest(Vector(p))
        tri = self.weight_faces[face]
        bc = bary(np.array(q), self.body_points[tri])
        out = {}
        for vi, amount in zip(tri, bc):
            for bi, w in self.native['weights'][int(vi)]:
                out[int(bi)] = out.get(int(bi), 0) + float(w * amount)
        out = dict(sorted(out.items(), key=lambda x: -x[1])[:8])
        total = sum(out.values())
        return {k: v / total for k, v in out.items() if v / total > 1e-05}

    def make_material(self, row):
        name = row['name']
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        n = m.node_tree.nodes
        l = m.node_tree.links
        bs = n.get('Principled BSDF')
        bs.inputs['Sheen Weight'].default_value = 0.17 if row['kind'] in ('nylon', 'webbing', 'pad') else 0
        for channel in ('BaseColor', 'Normal', 'ORM'):
            tex = n.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(str(R / 'Textures' / f'T_{name}_{channel}.png'), check_existing=True)
            tex.extension = 'REPEAT'
            if channel == 'BaseColor':
                l.new(tex.outputs['Color'], bs.inputs['Base Color'])
            else:
                tex.image.colorspace_settings.name = 'Non-Color'
                if channel == 'Normal':
                    normal = n.new('ShaderNodeNormalMap')
                    l.new(tex.outputs['Color'], normal.inputs['Color'])
                    l.new(normal.outputs[0], bs.inputs['Normal'])
                else:
                    sep = n.new('ShaderNodeSeparateColor')
                    l.new(tex.outputs['Color'], sep.inputs[0])
                    l.new(sep.outputs['Green'], bs.inputs['Roughness'])
                    l.new(sep.outputs['Blue'], bs.inputs['Metallic'])
        m['physical_tile_cm'] = row['tile_m'] * 100
        self.mats.append(m)

    def mesh(self, name, points, faces, mat=0, uv=None, slots=None, col=None):
        local = np.asarray(points, dtype=float)
        world = local if self.active_frame is None else local @ self.active_frame[1].T + self.active_frame[0]
        ob = super().mesh(name, world, faces, mat, uv, slots, col)
        if uv is None:
            layer = ob.data.uv_layers.active
            for poly, face in zip(ob.data.polygons, faces):
                q = local[list(face)]
                normal = np.cross(q[1] - q[0], q[2] - q[0])
                axes = [k for k in range(3) if k != int(np.argmax(np.abs(normal)))]
                for li, vi in zip(poly.loop_indices, poly.vertices):
                    layer.data[li].uv = (local[vi, axes[0]] / 4, local[vi, axes[1]] / 4)
        ob['assembly_kind'] = self.active_kind
        if col is None:
            self.weights[ob.name] = [self.active_weights.copy() if self.active_weights is not None else self.native_weights(p) for p in world]
        return ob

    def solid(self, ob, cm, inner_mat=None):
        return super().solid(ob, cm, inner_mat)

    def local(self, arc, offset=1.35, kind='carrier'):
        self.active_frame = self.frame_at(arc, offset)
        self.active_weights = self.native_weights(self.active_frame[0])
        self.active_kind = kind

    def world(self):
        self.active_frame = None
        self.active_weights = None
        self.active_kind = 'belt'

    def tube(self, name, paths, radius, mat, sides=6, closed=False):
        return super().tube(name, paths, radius, mat, sides if self.level == 0 else max(4, sides - 2), closed)

    def stitch(self, name, path, normals, mat=9, pitch=0.32, radius=0.017):
        return super().stitch(name, path, normals, mat, pitch, radius)

    def band(self, name, arc0, arc1, v0, v1, inner, outer, mat, n=160, puff=0):
        na = max(8, round(n * (arc1 - arc0) / self.perimeter))
        nv = 6 if self.level == 0 else 3
        aa = [self.angle(x) for x in np.linspace(arc0, arc1, na + 1)]
        ps = []
        uv = []
        fs = []
        for off in (inner, outer):
            for j, v in enumerate(np.linspace(v0, v1, nv + 1)):
                for i, a in enumerate(aa):
                    bulge = puff * math.sin(math.pi * i / na) * math.sin(math.pi * j / nv) if off == inner else 0
                    ps.append(self.point(a, v, off - bulge))
                    uv.append(((arc1 - arc0) * i / na / 4, v * self.height / 4))
        m = (na + 1) * (nv + 1)
        for side in (0, 1):
            for j in range(nv):
                for i in range(na):
                    k = side * m + j * (na + 1) + i
                    fs.append([k, k + 1, k + na + 2, k + na + 1])
        for j in (0, nv):
            for i in range(na):
                k = j * (na + 1) + i
                fs.append([k, k + 1, k + 1 + m, k + m])
        for i in (0, na):
            for j in range(nv):
                k = j * (na + 1) + i
                fs.append([k, k + na + 1, k + na + 1 + m, k + m])
        return self.mesh(name, ps, fs, mat, uv)

    def native_rig(self):
        arm = bpy.data.armatures.new(self.body + '_NativeBeltRig')
        rig = bpy.data.objects.new(arm.name, arm)
        self.cols['01_EDITABLE_LOD0'].objects.link(rig)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        reflect = Matrix.Diagonal((1, -1, 1))
        for b in self.bones:
            eb = arm.edit_bones.new(b['name'])
            axes = Matrix(b['axes']).transposed()
            for i in range(3):
                axes.col[i] = axes.col[i].normalized()
            matrix = (reflect @ axes @ reflect).to_4x4()
            matrix.translation = reflect @ Vector(b['position']) * 0.01
            eb.matrix = matrix
            eb.length = 0.025
        for b in self.bones:
            if b['parent'] >= 0:
                arm.edit_bones[b['name']].parent = arm.edit_bones[self.bones[b['parent']]['name']]
        bpy.ops.object.mode_set(mode='OBJECT')
        rig.select_set(False)
        rig.show_in_front = True
        rig.hide_render = True
        rig['body_variant'] = self.body
        rig['pants_reference'] = self.row['pants_asset']
        rig['runtime_tested'] = False
        return rig

    def bind(self, objects, rig):
        for ob in objects:
            weights = self.weights[ob.name]
            ids = {k for ws in weights for k in ws}
            groups = {i: ob.vertex_groups.new(name=self.bones[i]['name']) for i in ids}
            for vi, ws in enumerate(weights):
                for bi, w in ws.items():
                    groups[bi].add([vi], w, 'REPLACE')
            ob.parent = rig
            ob.modifiers.new('Native waist skinning', 'ARMATURE').object = rig

    def merge_for_export(self, objects, name, rig=None):
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        copies = []
        parts = []
        for ob in objects:
            ev = ob.evaluated_get(deps)
            me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=deps)
            copy = ob.copy()
            copy.data = me
            copy.modifiers.clear()
            copy.parent = None
            self.scene.collection.objects.link(copy)
            copy.matrix_world = ob.matrix_world.copy()
            copy.hide_set(False)
            copies.append(copy)
            me.calc_loop_triangles()
            parts.append(dict(name=ob.name, vertices=len(me.vertices), triangles=len(me.loop_triangles), kind=ob.get('assembly_kind', '')))
        for ob in copies:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join()
        ob = bpy.context.object
        ob.name = name
        if rig:
            ob.parent = rig
            ob.modifiers.new('Native waist skinning', 'ARMATURE').object = rig
        return (ob, dict(vertices=len(ob.data.vertices), triangles=sum((x['triangles'] for x in parts)), parts=parts))

    def selection(self, objects):
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects:
            ob.hide_set(False)
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]

    def fbx(self, objects, path, rig=None):
        self.selection(objects + ([rig] if rig else []))
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=True, bake_anim=False, axis_forward='-Y', axis_up='Z', mesh_smooth_type='FACE', path_mode='AUTO')

    def glb(self, objects, path, rig=None):
        self.selection(objects + ([rig] if rig else []))
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_apply=False, export_animations=False, export_yup=True, export_all_influences=True)

    def neutral(self, ob, path):
        me = ob.data
        me.calc_loop_triangles()
        uv = me.uv_layers.active
        groups = {x.index: next((i for i, b in enumerate(self.bones) if b['name'] == x.name)) for x in ob.vertex_groups}
        data = dict(body=self.body, coordinate_system='UE centimetres; UV V not flipped', positions=[[v.co.x * 100, -v.co.y * 100, v.co.z * 100] for v in me.vertices], triangles=[], uv=[], normals=[], triangle_materials=[], material_slots=[m.name for m in me.materials], bones=self.bones, weights=[])
        for v in me.vertices:
            ws = [(groups[g.group], g.weight) for g in v.groups if g.weight > 1e-06]
            total = sum((w for i, w in ws))
            data['weights'].append([[i, w / total] for i, w in ws])
        for tri in me.loop_triangles:
            loops = list(reversed(tri.loops))
            data['triangles'].append(list(reversed(tri.vertices)))
            data['uv'].append([list(uv.data[i].uv) for i in loops])
            data['normals'].append([[me.corner_normals[i].vector.x, -me.corner_normals[i].vector.y, me.corner_normals[i].vector.z] for i in loops])
            data['triangle_materials'].append(tri.material_index)
        Path(path).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
