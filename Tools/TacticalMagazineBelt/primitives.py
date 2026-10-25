"""Frozen project geometry helpers; executed by the belt authoring context."""
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
