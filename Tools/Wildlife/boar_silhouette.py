"""Shape tusks and a layered bristle crest in the pig's reference pose (UE centimetres)."""
from math import cos, exp, pi, sin
import random
import unreal as u


class BackSurface:
    """Vertical intersections with body triangles, excluding the pack's hair cards."""
    def __init__(self, mesh):
        q = u.GeometryScript_MeshQueries
        lists = u.GeometryScript_List
        pos = lists.convert_vector_list_to_array(q.get_all_vertex_positions(mesh, False)[1])
        triangles = lists.convert_triangle_list_to_array(q.get_all_triangle_indices(mesh, False)[1])
        self.faces = []
        self.weights = {}
        self.mesh = mesh
        for index, tri in enumerate(triangles):
            ids = (tri.x, tri.y, tri.z)
            a, b, c = (pos[i] for i in ids)
            if min(a.z, b.z, c.z) < 65 or min(a.x, b.x, c.x) > 22 or max(a.x, b.x, c.x) < -22:
                continue
            if u.GeometryScript_Materials.get_triangle_material_id(mesh, index)[0] != 0:
                continue
            ab, ac = b-a, c-a
            det = ab.x*ac.y-ab.y*ac.x
            if abs(det) > 1.e-6:
                self.faces.append((a, ab, ac, 1./det, ids))

    def at(self, x, y):
        best = None
        for a, ab, ac, inverse, ids in self.faces:
            dx, dy = x-a.x, y-a.y
            b, c = (dx*ac.y-dy*ac.x)*inverse, (ab.x*dy-ab.y*dx)*inverse
            if min(1.-b-c, b, c) < -.00001:
                continue
            z = a.z+b*ab.z+c*ac.z
            if best is None or z > best[0]:
                best = (z, ids, (1.-b-c, b, c))
        if best is None:
            raise RuntimeError(f'No dorsal body surface at {x}, {y}')
        weights = {}
        for vid, coefficient in zip(best[1], best[2]):
            if vid not in self.weights:
                self.weights[vid] = u.GeometryScript_BoneWeights.get_vertex_bone_weights(self.mesh, vid)[1]
            for w in self.weights[vid]:
                weights[w.bone_index] = weights.get(w.bone_index, 0.) + coefficient*w.weight
        weights = {b:w for b,w in weights.items() if w > .001}
        total = sum(weights.values())
        return u.Vector(x,y,best[0]), [u.GeometryScriptBoneWeight(bone_index=b, weight=w/total) for b,w in weights.items()]


class Surface:
    def __init__(self):
        self.p, self.n, self.uv, self.w, self.faces = [], [], [], [], []

    def vertex(self, p, n, uv, weights):
        self.p.append(p)
        self.n.append(n.normal())
        self.uv.append(u.Vector2D(*uv))
        self.w.append(weights)
        return len(self.p)-1

    def face(self, a, b, c):
        # UE front faces use clockwise winding. Match the authored surface normal.
        normal = (self.p[c]-self.p[a]).cross(self.p[b]-self.p[a])
        if normal.dot(self.n[a]+self.n[b]+self.n[c]) < 0:
            b,c = c,b
        self.faces.append((a,b,c))

    def bridge(self, a, b, closed=False):
        for i in range(len(a) if closed else len(a)-1):
            j = (i+1)%len(a)
            self.face(a[i],a[j],b[j])
            self.face(a[i],b[j],b[i])

    def append(self, mesh, slot):
        q, edits = u.GeometryScript_MeshQueries, u.GeometryScript_MeshEdits
        buf = u.GeometryScriptSimpleMeshBuffers(vertices=self.p, normals=self.n,
            triangles=[u.IntVector(*f) for f in self.faces])
        for i in range(max(1,q.get_num_uv_sets(mesh))):
            buf.set_editor_property('uv'+str(i), self.uv)
        _,new = edits.append_buffers_to_mesh(mesh,buf,slot,True)
        indices = u.GeometryScript_List.convert_index_list_to_array(new)
        if len(indices)!=len(self.faces) or min(indices)<0:
            raise RuntimeError('Unable to append boar geometry')
        bound = set()
        for face, tid in zip(self.faces, indices):
            if all(i in bound for i in face):
                continue
            tri, valid = q.get_triangle_indices(mesh,tid)
            if not valid:
                raise RuntimeError('Missing boar triangle')
            for i,vid in zip(face,(tri.x,tri.y,tri.z)):
                if i not in bound:
                    _,ok = u.GeometryScript_BoneWeights.set_vertex_bone_weights(mesh,vid,self.w[i])
                    if not ok:
                        raise RuntimeError('Could not bind boar vertex')
                    bound.add(i)


def shape_eyes(mesh):
    # The eye, lids and brow share the original head surface and skin weights.
    # Work along the eye opening, which runs diagonally across the tapered face.
    queries = u.GeometryScript_MeshQueries
    positions = u.GeometryScript_List.convert_vector_list_to_array(
        queries.get_all_vertex_positions(mesh, False)[1])
    moved = set()
    for index, p in enumerate(positions):
        dx, dy, dz = abs(p.x)-9.8, p.y-99.45, p.z-54.1
        along = .84*dx-.54*dy  # positive towards the temple
        depth = .54*dx+.84*dy
        if abs(along) >= 8. or abs(depth) >= 4.6 or not -3.3 < dz < 7.:
            continue
        # A compact falloff brings the edit to zero at the edge of the orbit.
        falloff = (1.-(along/8.)**2)**2 * (1.-(depth/4.6)**2)**2
        falloff *= (1.-(dz/(7. if dz>0. else 3.3))**2)**2
        ridge = exp(-((dz-2.6-.22*along)/1.65)**2)
        upper_lid = exp(-((dz-1.20)/1.35)**2)
        opening = exp(-(dz/2.85)**2)
        drop = .73*upper_lid+.38*ridge
        height = (.24*along*opening-drop)*falloff
        project = 1.12*ridge*falloff
        normal_x = .54 if p.x>0 else -.54
        offset = u.Vector(normal_x*project,.84*project,height)
        _, valid = u.GeometryScript_MeshEdits.set_vertex_position(mesh,index,p+offset,True)
        if not valid:
            raise RuntimeError('Could not shape orbital vertex')
        moved.add(index)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(
        queries.get_all_triangle_indices(mesh,False)[1])
    affected = [i for i,t in enumerate(triangles) if t.x in moved or t.y in moved or t.z in moved]
    if affected:
        _, selection = u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(
            mesh,affected,u.GeometryScriptMeshSelectionType.TRIANGLES)
        u.GeometryScript_Normals.recompute_normals_for_mesh_selection(
            mesh,selection,u.GeometryScriptCalculateNormalsOptions(),True)


def tusks(lod, jaw):
    out = Surface()
    sides, rows = ((18,20),(14,15),(10,10),(8,7))[min(lod,3)]
    weights = [u.GeometryScriptBoneWeight(bone_index=jaw,weight=1.)]
    for sign in (-1,1):
        # The first section is buried behind the lower lip at Y=98, Z=31.
        a,b,c,d = (u.Vector(sign*x,y,z) for x,y,z in (
            (5.5,98,30.8),(18.5,102.5,30.8),(25.6,100.6,42.),(21.8,94.4,51.8)))
        previous = None
        for i in range(rows):
            t = i/rows
            s = 1.-t
            p = a*(s**3)+b*(3*s*s*t)+c*(3*s*t*t)+d*(t**3)
            tangent = ((b-a)*(s*s)+(c-b)*(2*s*t)+(d-c)*(t*t)).normal()
            across = tangent.cross(u.Vector(0,1,0)).normal()
            along = tangent.cross(across).normal()
            radius = 2.75*(1.-t)**.76
            ring = []
            for j in range(sides+1):
                angle = 2*pi*j/sides
                ridge = 1.+.045*cos(3*angle+.4)
                offset = (across*cos(angle)+along*(.81*sin(angle)))*radius*ridge
                n = across*cos(angle)+along*(sin(angle)/.81)+tangent*.075
                ring.append(out.vertex(p+offset,n,(j/sides,1.-t),weights))
            if previous:
                out.bridge(previous,ring)
            previous=ring
        tip=out.vertex(d,(d-c).normal(),(.5,0.),weights)
        for j in range(sides):
            out.face(previous[j],previous[j+1],tip)
    return out


def mane(lod, back):
    mesh = Surface()
    rows, across, segments = ((73, 8, 3), (48, 6, 3), (32, 5, 2), (20, 4, 2))[min(lod, 3)]
    rng = random.Random(34891)
    for row in range(rows):
        for col in range(across):
            t = (row+rng.uniform(.06,.94))/rows
            y = -48. + 123.*t
            taper = sin(pi*t)**.78
            shoulder = exp(-((y-43.)/28.)**2)
            lateral = 2*(col+rng.uniform(.04,.96))/across-1.
            spread = 1.4+taper*(10.+4.3*shoulder)
            x = lateral*spread+.65*sin(y*.085)*taper
            root, weights = back.at(x,y)
            rear, _ = back.at(x,y-2.)
            dorsal_slope = (rear.z-root.z)*.5
            root.z -= .75
            edge = (1.-abs(lateral)**1.45)
            plume = .82+.18*sin(y*.30+1.4*sin(y*.09)+lateral)
            rise = (1.7+taper*(3.+5.6*shoulder)*(.34+.66*edge))*plume*rng.uniform(.65,1.2)
            sweep = (2.8+taper*(5.8+4.3*shoulder))*rng.uniform(.75,1.25)
            drift = sweep*(lateral*.34+.11*sin(y*.16)+rng.uniform(-.14,.14))
            half_width = (.78+.49*spread/across)*rng.uniform(.74,1.24)
            twist = rng.uniform(-.62,.62)+.52*lateral
            tile = rng.randrange(8)
            reverse = rng.choice((-1.,1.))
            previous = None
            for k in range(segments+1):
                h = k/segments
                travel = sweep*(.64*h+.36*h*h)
                center = root+u.Vector(drift*h, -travel, rise*(1.55*h-.55*h*h)+travel*dorsal_slope)
                # Broad, genuinely transparent cards: the individual fibre tips
                # and the staggered shoulder clumps define the animal's outline.
                width = half_width*(1.-.32*h)
                ring = []
                for side in (-1.,1.):
                    p = center+u.Vector(side*width, side*width*(twist+.16*h), -side*width*lateral*.32)
                    n = u.Vector(lateral*.28, .56-.13*h, 1.)
                    uv = ((tile+.5+reverse*side*.485)/8., h)
                    ring.append(mesh.vertex(p,n,uv,weights))
                if previous is not None:
                    mesh.bridge(previous,ring)
                previous=ring
    return mesh
