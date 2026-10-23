"""Author a complete sewn harness against closed, visible-clothing envelopes.

No nearest-face signed-normal iteration. Each longitudinal section receives a
single bounded, smooth outward offset; the bag and its sewn endpoints share a
rigid transform. Geometry, UVs, material roles and attachment rows are explicit.
"""
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.optimize import lsq_linear
from scipy.spatial import ConvexHull, cKDTree

P = Path("D:/FPS3D/FPSGAME")
R = P / "SourceAssets/BackpackHarnessRebuild20261020"
I = R / "Inputs"
DEST = "/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003"
from bag_shell import REVISION
PROFILES = {
    "bare": (None, "SK_Jason_Backpack", .3),
    "thin_cotton": ("ue_field_sweater_charcoal", "SK_Jason_Backpack_ThinCotton", .3),
    "knit_sweater": ("ue_field_sweater", "SK_Jason_Backpack_Sweater", .4),
    "chainmail": ("ue_chainmail_shirt", "SK_Jason_Backpack_Chainmail", .4),
    "mage_robe": ("ue_blue_mage_robe", "SK_Jason_Backpack_Robe", .5),
    "st6": ("ue_st6_sleeves", "SK_Jason_Backpack_ST6", .3),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def visible_mesh(data):
    v, t = np.asarray(data["positions"]), np.asarray(data["triangles"], int)
    slots = [m["slot"].lower() for m in data["materials"]]
    keep = [not any(s in slot for s in ("exposed", "inner", "lining", "proxy", "neckseam")) for slot in slots]
    t = t[np.asarray(keep)[np.asarray(data["triangle_materials"])]]
    return trimesh.Trimesh(v, t, process=False)


def envelope(body, garment):
    points = []
    for data in [body] + ([garment] if garment else []):
        mesh = visible_mesh(data)
        ids=np.unique(mesh.faces)
        v = mesh.vertices[ids]
        torso={b["index"] for b in data["bones"] if b["name"]=="pelvis" or b["name"].startswith(("spine_","clavicle"))}
        influence=np.asarray([sum(w for b,w in data["weights"][j] if b in torso) for j in ids])
        selected = (np.abs(v[:, 0]) < 20) & (v[:, 2] > 104) & (v[:, 2] < 151.5)
        selected &= influence > np.where(v[:,2]>132,.25,.8)
        points.append(v[selected])
    cloud = np.unique(np.round(np.vstack(points), 4), axis=0)
    hull = ConvexHull(cloud)
    proxy = trimesh.convex.convex_hull(cloud)
    cells=[]
    for low in np.arange(104,148,2):
        high=min(low+4,151.5)
        local=cloud[(cloud[:,2]>=low)&(cloud[:,2]<=high)]
        if len(local)<4 or np.linalg.matrix_rank(local-local.mean(axis=0))<3:
            continue
        cells.append(ConvexHull(local).equations)
    return {"frame":hull.equations,"cells":cells}, proxy


def lift_required(points, directions, equations, margin):
    """Exit a closed convex envelope along a specified outward direction."""
    if isinstance(equations,dict):
        return np.max([lift_required(points,directions,cell,margin) for cell in equations["cells"]],axis=0)
    signed = points @ equations[:, :3].T + equations[:, 3]
    denom = directions @ equations[:, :3].T
    margin = np.broadcast_to(margin, (len(points),))
    distance = np.full_like(signed, np.inf)
    np.divide(margin[:, None] - signed, denom, out=distance, where=denom > .12)
    lift = np.maximum(distance.min(axis=1), 0)
    lift[signed.max(axis=1) >= margin] = 0
    return lift


def contact_offset(points, directions, equations, margin):
    """Signed outer ray intersection, allowing a floating route to move inward."""
    exits = []
    for cell in equations["cells"]:
        signed = points @ cell[:, :3].T + cell[:, 3]
        denom = directions @ cell[:, :3].T
        numerator = np.broadcast_to(margin,(len(points),))[:,None]-signed
        upper = np.full_like(signed, np.inf)
        lower = np.full_like(signed, -np.inf)
        np.divide(numerator, denom, out=upper, where=denom > 1e-7)
        np.divide(numerator, denom, out=lower, where=denom < -1e-7)
        hi, lo = upper.min(1), lower.max(1)
        valid = (hi >= lo) & ~np.any((abs(denom)<1e-7)&(numerator<0),axis=1)
        exits.append(np.where(valid, hi, -np.inf))
    return np.max(exits, axis=0)


def frame(path, equations=None):
    tangent = unit(np.gradient(path, axis=0))
    desired = unit(np.column_stack([path[:, 0] * .42, path[:, 1] - 2.,
                                    np.maximum(path[:, 2] - 137., 0.) * 1.65]))
    if equations is not None:
        if isinstance(equations,dict):equations=equations["frame"]
        from scipy.ndimage import gaussian_filter1d
        index=np.argmax(path@equations[:,:3].T+equations[:,3],axis=1)
        desired=unit(gaussian_filter1d(equations[index,:3],6.,axis=0))
    across = unit(np.cross(desired, tangent))
    for index in range(1, len(across)):
        if across[index] @ across[index - 1] < 0:
            across[index] *= -1
    normal = unit(np.cross(tangent, across))
    if np.mean(np.sum(normal * desired, axis=1)) < 0:
        across *= -1
        normal *= -1
    return tangent, across, normal


def smooth_lift(required, pin_ends=False):
    """Bounded quadratic smoothing; never trade clearance for a lower cost."""
    count = len(required)
    d1 = np.diff(np.eye(count), axis=0)
    d2 = np.diff(np.eye(count), n=2, axis=0)
    matrix = np.vstack([.2*np.eye(count), 2*d1, np.sqrt(30)*d2])
    if required.max() > 5:
        raise RuntimeError(f"Envelope needs {required.max():.2f} cm; revise the route instead of stretching it")
    free = slice(1,-1) if pin_ends else slice(None)
    result = lsq_linear(matrix[:,free], np.zeros(len(matrix)), bounds=(required[free], 5.0),
                        method="bvls", max_iter=200, tol=1e-10)
    if not result.success:
        raise RuntimeError("Smooth offset solve failed: " + result.message)
    offset = np.zeros(count)
    offset[free] = result.x
    return offset


def rounded_ring(width, thickness, corner_radius=None):
    radius = thickness * .42 if corner_radius is None else corner_radius
    ring = []
    for cx, cy, angle in ((width/2-radius, -thickness/2+radius, -90),
                          (width/2-radius, thickness/2-radius, 0),
                          (-width/2+radius, thickness/2-radius, 90),
                          (-width/2+radius, -thickness/2+radius, 180)):
        for a in np.radians(np.linspace(angle, angle+90, 3)):
            ring.append([cx+radius*np.cos(a), cy+radius*np.sin(a)])
    return np.asarray(ring)


def prepare_bag():
    """Restore the complete shell and remove only the old shoulder-stub islands."""
    from bag_shell import repair
    bag = repair(read(I/"bag.json"))
    write(R/"PreparedBag.json", bag)
    return bag


class Mesh:
    def __init__(self, bones, materials):
        self.data = dict(positions=[], triangles=[], weights=[], normals=[], uv=[],
                         triangle_materials=[], bones=bones, materials=materials, parts=[])

    def vertices(self, points, weights):
        start = len(self.data["positions"])
        self.data["positions"].extend(np.asarray(points).tolist())
        self.data["weights"].extend(weights)
        return list(range(start, start+len(points)))

    def face(self, ids, uv, material):
        self.data["triangles"].append(list(ids))
        self.data["uv"].append(np.asarray(uv).tolist())
        self.data["triangle_materials"].append(material)
        self.data["normals"].append([[0., 0., 1.]]*3)
        return len(self.data["triangles"])-1

    def ribbon(self, name, path, widths, thicknesses, bindings, material=2, equations=None):
        tangent, across, normal = frame(path,equations)
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        rows, uv_rows, rings = [], [], []
        first_face = len(self.data["triangles"])
        for i, centre in enumerate(path):
            ring = rounded_ring(widths[i], thicknesses[i])
            rings.append(ring)
            points = centre + ring[:, :1]*across[i] + ring[:, 1:]*normal[i]
            rows.append(self.vertices(points, [bindings[i]]*len(ring)))
            perimeter = np.r_[0., np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
            perimeter /= perimeter[-1]+np.linalg.norm(ring[-1]-ring[0])
            uv_rows.append(np.column_stack([perimeter, np.full(len(ring), arc[i]/8.)]))
        n = len(rows[0])
        for i in range(len(rows)-1):
            for j in range(n):
                k = (j+1) % n
                uv = np.array([uv_rows[i][j], uv_rows[i][k], uv_rows[i+1][k], uv_rows[i+1][j]])
                if k == 0:
                    uv[1:3, 0] = 1.
                a, b, c, d = rows[i][j], rows[i][k], rows[i+1][k], rows[i+1][j]
                self.face([a, b, c], uv[[0, 1, 2]], material)
                self.face([a, c, d], uv[[0, 2, 3]], material)
        side_end = len(self.data["triangles"])
        for i in (0, len(rows)-1):
            centre = self.vertices([path[i]], [bindings[i]])[0]
            for j in range(n):
                k = (j+1) % n
                ids = [centre, rows[i][j], rows[i][k]]
                uv = np.array([[.5, .5], rings[i][j]/[widths[i], thicknesses[i]]+.5,
                               rings[i][k]/[widths[i], thicknesses[i]]+.5])
                if i == 0:
                    ids.reverse()
                    uv = uv[::-1]
                self.face(ids, uv, material)
        part = {"name": name, "rows": rows, "path": path.tolist(),
                "side_faces": list(range(first_face, side_end)),
                "cap_faces": list(range(side_end, len(self.data["triangles"]))),
                "widths": widths.tolist(), "thicknesses": thicknesses.tolist()}
        self.data["parts"].append(part)
        return part

    def hardware(self, name, centre, across, along, normal, width, height, binding):
        """Rounded rectangular ring with an actual open centre."""
        first = len(self.data["triangles"])
        outside, inside = rounded_ring(width, height, .24), rounded_ring(width-.65, height-.65, .12)
        rings = []
        for depth in (-.18, .18):
            for ring in (outside, inside):
                points = centre+ring[:, :1]*across+ring[:, 1:]*along+normal*depth
                rings.append(self.vertices(points, [binding]*len(points)))
        n = len(outside)
        # normals corrected relative to the geometric ring surfaces below.
        for j in range(n):
            k = (j+1) % n
            quads = [(rings[0][j], rings[0][k], rings[2][k], rings[2][j]),
                     (rings[1][k], rings[1][j], rings[3][j], rings[3][k]),
                     (rings[0][k], rings[0][j], rings[1][j], rings[1][k]),
                     (rings[2][j], rings[2][k], rings[3][k], rings[3][j])]
            for a, b, c, d in quads:
                for tri in ([a,b,c], [a,c,d]):
                    pts = np.asarray(self.data["positions"])[tri]
                    relative = pts-centre
                    uv = np.column_stack([relative@across/width+.5, relative@along/height+.5])
                    # Wall faces use depth as one UV coordinate.
                    a2,b2 = uv[1]-uv[0], uv[2]-uv[0]
                    if abs(a2[0]*b2[1]-a2[1]*b2[0]) < 1e-9:
                        uv = np.column_stack([relative@along/height+relative@across/width,
                                              relative@normal/.36+.5])
                    self.face(tri, uv, 1)
        # A real centre bar forms two threading slots rather than a decorative ring.
        bar=trimesh.creation.box(extents=[.38,height-.4,.36])
        points=centre+bar.vertices[:,:1]*across+bar.vertices[:,1:2]*along+bar.vertices[:,2:]*normal
        ids=self.vertices(points,[binding]*len(points))
        for face in bar.faces:
            local=bar.vertices[face]
            normal_local=np.cross(local[1]-local[0],local[2]-local[0])
            axes=[a for a in range(3) if a!=np.argmax(abs(normal_local))]
            uv=local[:,axes]/np.array([.38,height-.4,.36])[axes]+.5
            self.face([ids[i] for i in face],uv,1)
        # Fix winding per closed hardware component without touching the fabric.
        faces = np.asarray(self.data["triangles"][first:])
        mesh = trimesh.Trimesh(np.asarray(self.data["positions"]), faces, process=False)
        fixed = mesh.copy()
        fixed.fix_normals(multibody=True)
        for i, (old, new) in enumerate(zip(faces, fixed.faces)):
            if not np.array_equal(old, new):
                self.data["triangles"][first+i] = new.tolist()
                self.data["uv"][first+i] = [self.data["uv"][first+i][list(old).index(v)] for v in new]
        self.data["parts"].append({"name": name, "hardware": True,
                                  "faces": list(range(first, len(self.data["triangles"])))})

    def normals(self):
        v = np.asarray(self.data["positions"])
        t = np.asarray(self.data["triangles"])
        for part in self.data["parts"]:
            if part.get("hardware"):
                for fi in part["faces"]:
                    a,b,c = v[t[fi]]
                    n = unit(np.cross(b-a, c-a)).tolist()
                    self.data["normals"][fi] = [n]*3
                continue
            ids = np.asarray(part["side_faces"])
            area = np.cross(v[t[ids, 1]]-v[t[ids, 0]], v[t[ids, 2]]-v[t[ids, 0]])
            sums = np.zeros_like(v)
            for k in range(3):
                np.add.at(sums, t[ids, k], area)
            sums = unit(sums)
            for fi in ids:
                self.data["normals"][fi] = sums[t[fi]].tolist()
            for fi in part["cap_faces"]:
                a,b,c = v[t[fi]]
                n = unit(np.cross(b-a, c-a)).tolist()
                self.data["normals"][fi] = [n]*3


def build(profile):
    shirt, asset, margin = PROFILES[profile]
    body = read(I / "body.json")
    garment = read(I / (shirt+".json")) if shirt else None
    equations, proxy = envelope(body, garment)
    write(R / "Envelopes" / (profile+".json"),
          {"positions": proxy.vertices.tolist(), "triangles": proxy.faces.tolist(),
           "frame_equations":equations["frame"].tolist(),"cells":[c.tolist() for c in equations["cells"]]})
    bag = read(R/"PreparedBag.json")
    bv = np.asarray(bag["positions"])
    directions = np.tile([0., -1., 0.], (len(bv), 1))
    bag_shift = float(lift_required(bv, directions, equations, .30).max())
    if bag_shift > 5:
        raise RuntimeError(f"Bag fit for {profile} needs an excessive {bag_shift:.2f} cm rear shift")
    offset = np.array([0., -bag_shift-.1, 0.])
    bv += offset
    bones = body["bones"]
    by_name = {b["name"]: b["index"] for b in bones}
    s3, s4, s5 = [by_name[name] for name in ("spine_03", "spine_04", "spine_05")]
    bag_bone = s3
    materials = [bag["materials"][0],
                 {"slot": "HarnessHardware", "asset": DEST+"/M_BackpackHarness_Hardware.M_BackpackHarness_Hardware"},
                 {"slot": "HarnessFabric", "asset": DEST+"/M_BackpackHarness_FabricR1.M_BackpackHarness_FabricR1"}]
    mesh = Mesh(bones, materials)
    anatomy = visible_mesh(body)
    point_tree = cKDTree(anatomy.vertices)
    paths = []
    measurements = {}
    for side, tag in ((1, "l"), (-1, "r")):
        top = np.asarray(bag["anchors"]["top_"+tag])+offset+[0., -.25, 0.]
        bottom = np.asarray(bag["anchors"]["bottom_"+tag])+offset+[0., -.25, 0.]
        control = np.array([top,
                            [side*11.8, -6.8, 143.5], [side*12.8, -.5, 144.0],
                            [side*12.2, 6.2, 141.6], [side*12.0, 11.8, 136.2],
                            [side*11.5, 13.2, 126.0], [side*13.8, 10., 122.0],
                            [side*15.0, 3.5, 117.2], [side*14.5, -5.5, 113.5], bottom])
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(control, axis=0), axis=1))]
        sample = np.linspace(0, arc[-1], int(np.ceil(arc[-1]/.7))+1)
        base = CubicSpline(arc, control, bc_type="natural")(sample)
        # Padding ends at the chest-side adjuster, not at a fraction of an
        # arbitrarily lengthened loop that can turn into an abdominal sling.
        widths = PchipInterpolator(arc,[2.2,4.6,4.6,4.4,4.2,3.2,2.2,2.2,2.2,2.2])(sample)
        thick = PchipInterpolator(arc,[.22,.65,.65,.65,.60,.32,.24,.24,.24,.24])(sample)
        # Start on the garment envelope instead of accepting an already
        # floating hand-authored route. Endpoints remain sewn into the bag.
        _, across, direction = frame(base,equations)
        samples=[]
        for j, centre in enumerate(base):
            ring=rounded_ring(widths[j],thick[j])
            dense=np.vstack([ring*(1-f)+np.roll(ring,-1,axis=0)*f for f in (0.,.25,.5,.75)])
            samples.append(centre+dense[:,:1]*across[j]+dense[:,1:]*direction[j])
        local_margin=margin+max(.7-margin,0)*np.clip((base[:,2]-130)/8,0,1)
        contact=contact_offset(np.vstack(samples),np.repeat(direction,48,axis=0),equations,np.repeat(local_margin,48))
        contact=contact.reshape(len(base),48).max(1)
        contact=np.where(np.isfinite(contact),np.clip(contact,-7.,4.),0.)
        from scipy.ndimage import gaussian_filter1d
        contact=gaussian_filter1d(contact,5.)
        contact*=np.minimum(np.minimum(sample/8.,(sample[-1]-sample)/18.),1.)
        base+=direction*contact[:,None]
        contact_arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(base,axis=0),axis=1))]
        sample=np.linspace(0,contact_arc[-1],int(np.ceil(contact_arc[-1]/.65))+1)
        widths=np.interp(sample,contact_arc,widths)
        thick=np.interp(sample,contact_arc,thick)
        base=CubicSpline(contact_arc,base,bc_type="natural")(sample)
        path = base.copy()
        total = np.zeros(len(path))
        _, _, direction = frame(base,equations)
        for iteration in range(4):
            _, across, normal = frame(path,equations)
            samples, ray_dirs = [], []
            for j in range(len(path)):
                ring = rounded_ring(widths[j], thick[j])
                # Include samples inside each broad face, not just the rim:
                # a wide quad can cut a convex shoulder while its corners clear.
                dense=np.vstack([ring*(1-f)+np.roll(ring,-1,axis=0)*f for f in (0.,.25,.5,.75)])
                samples.append(path[j]+dense[:, :1]*across[j]+dense[:, 1:]*normal[j])
                ray_dirs.append(np.tile(direction[j], (len(dense), 1)))
            seam_blend = np.minimum(np.minimum(sample/3., (sample[-1]-sample)/3.), 1.)
            local_margin=margin+max(.7-margin,0)*np.clip((path[:,2]-130)/8,0,1)
            row_margin = .08+(local_margin-.08)*seam_blend
            required = lift_required(np.vstack(samples), np.vstack(ray_dirs), equations,
                                     np.repeat(row_margin, 48)).reshape(len(path), -1).max(1)
            if iteration and required.max() < 1e-4:
                break
            if max(required[0], required[-1]) > .1:
                raise RuntimeError(f"{profile}/{tag}: bag seam requires {required[[0,-1]]} cm")
            total = smooth_lift(total+required, pin_ends=True)
            # Sewn ends are inside the rear bag's attachment tabs.
            if max(total[0], total[-1]) > .1:
                raise RuntimeError(f"{profile}/{tag}: bag seam needs separate fitting")
            total[[0,-1]] = 0
            path = base+direction*total[:, None]
        bindings = []
        distances, nearest = point_tree.query(path, k=8)
        bone_names={b["index"]:b["name"] for b in bones}
        clavicle=by_name["clavicle_"+tag];upperarm=by_name["upperarm_"+tag]
        for j, vertices in enumerate(nearest):
            mix=1/np.maximum(distances[j],.05)**2;mix/=mix.sum()
            weights={}
            for vi,factor in zip(vertices,mix):
                for b,w in body["weights"][vi]:
                    name=bone_names[b]
                    mapped=None
                    if name=="pelvis" or name in ("spine_01","spine_02","spine_03","spine_04","spine_05"):
                        mapped=b
                    elif name.startswith("spine_"):
                        mapped=s4
                    elif name.startswith("clavicle") and name.endswith("_"+tag):
                        mapped=clavicle if path[j,2]>132 else s4
                    elif name.startswith("upperarm") and name.endswith("_"+tag):
                        mapped=upperarm if path[j,2]>136 else s4
                    if mapped is not None:
                        weights[mapped]=weights.get(mapped,0)+w*factor
            denom=sum(weights.values())
            weights={b:w/denom for b,w in weights.items()} if denom>1e-5 else {bag_bone:1.}
            # Body muscle correctives can scale several-fold in a cast. Map
            # them to structural joints and bound arm contribution to padding.
            shoulder_blend=float(np.clip((path[j,2]-134.)/9.,0.,1.))
            shoulder_blend=shoulder_blend*shoulder_blend*(3-2*shoulder_blend)
            excess=max(weights.get(upperarm,0)-.12*shoulder_blend,0)
            if excess:weights[upperarm]-=excess;weights[clavicle]=weights.get(clavicle,0)+excess
            excess=max(weights.get(clavicle,0)-.65*shoulder_blend,0)
            if excess:weights[clavicle]-=excess;weights[s4]=weights.get(s4,0)+excess
            end_blend = min(1., sample[j]/8., (sample[-1]-sample[j])/8.)
            end_blend = end_blend*end_blend*(3-2*end_blend)
            weights = {b:w*end_blend for b,w in weights.items()}
            weights[bag_bone] = weights.get(bag_bone, 0)+1-end_blend
            bindings.append([[int(b),float(w)] for b,w in weights.items() if w>1e-7])
        # Smooth only the weights; never smooth positions after clearance.
        dense = np.zeros((len(path), len(bones)))
        for j, row in enumerate(bindings):
            for b,w in row:
                dense[j,b] = w
        from scipy.ndimage import gaussian_filter1d
        dense = gaussian_filter1d(dense, 3., axis=0)
        dense[[0,-1]]=0;dense[[0,-1],bag_bone]=1.
        bindings=[]
        for values in dense:
            ids=np.argsort(-values)[:8];values=values[ids];values/=values.sum()
            bindings.append([[int(b),float(w)] for b,w in zip(ids,values) if w>1e-7])
        part = mesh.ribbon("shoulder_return_"+tag, path, widths, thick, bindings,equations=equations)
        part["fit_lift_cm"] = total.tolist()
        part["base_path"] = base.tolist()
        part["sewn_bag_points"] = [top.tolist(), bottom.tolist()]
        tangent, across, normal = frame(path,equations)
        front = np.where(path[:,1] > 9)[0]
        buckle_index = front[np.argmin(abs(path[front,2]-126.0))]
        mesh.hardware("adjuster_"+tag, path[buckle_index]+normal[buckle_index]*.48,
                      across[buckle_index], tangent[buckle_index], normal[buckle_index], 3.15, 2.25, bindings[buckle_index])
        paths.append((path, bindings, widths, thick))
        steps = np.linalg.norm(np.diff(path, axis=0), axis=1)
        measurements[tag] = {"length_cm": float(steps.sum()), "max_step_cm": float(steps.max()),
                             "max_lift_cm": float(total.max()), "anchors_cm": [path[0].tolist(),path[-1].tolist()]}

    # The sternum tape meets the fitted shoulder pads; it cannot float at the
    # old fixed X/Y coordinates when the garment profile changes.
    endpoints, weights = [], []
    for side_index,(path, bindings, widths, thick) in enumerate(paths):
        front = np.where(path[:,1] > 8)[0]
        index = front[np.argmin(abs(path[front,2]-133.))]
        _,across,normal=frame(path,equations)
        surface=path[index]+normal[index]*(thick[index]*.5+.10)
        # Place the crossing on the pad face, with an actual stitched tab.
        tab=surface+np.linspace(-.42,.42,9)[:,None]*widths[index]*across[index]
        mesh.ribbon('sternum_tab_'+str(side_index),tab,np.full(9,1.95),np.full(9,.14),[bindings[index]]*9)
        endpoints.append(surface+normal[index]*.06)
        weights.append(bindings[index])
    # Small chest bow accommodates pectoral corrective motion without binding
    # the tape to arm muscle helpers that can scale sharply during a cast.
    control = np.array([endpoints[0], [0., max(p[1] for p in endpoints)+1.9, 133.], endpoints[1]])
    curve = CubicSpline([0.,.5,1.], control, bc_type="natural")
    sternum = curve(np.linspace(0,1,33))
    direction = np.tile([0.,1.,0.], (len(sternum),1))
    lift = lift_required(sternum, direction, equations, margin+.25)
    lift = smooth_lift(lift)
    sternum += direction*lift[:,None]
    # The two end stations are sewn into the padded strips, not separate space.
    sternum[[0,-1]] = endpoints
    middle = {}
    for row in weights:
        for b,w in row:
            middle[b] = middle.get(b,0)+w*.5
    ids=sorted(middle,key=middle.get,reverse=True)[:8];denom=sum(middle[b] for b in ids)
    sw = [[b,middle[b]/denom] for b in ids if middle[b]>1e-7]
    sb = []
    for i in range(len(sternum)):
        f=i/(len(sternum)-1)
        a={b:w for b,w in weights[0]};b={b:w for b,w in weights[1]}
        row_weights={k:(1-f)*a.get(k,0)+f*b.get(k,0) for k in a.keys()|b.keys()}
        keep=sorted(row_weights,key=row_weights.get,reverse=True)[:8];denom=sum(row_weights[k] for k in keep)
        sb.append([[k,row_weights[k]/denom] for k in keep if row_weights[k]>1e-7])
    mesh.ribbon("sternum", sternum, np.full(33,1.65), np.full(33,.20), sb)
    tangent, across, normal = frame(sternum)
    mid = len(sternum)//2
    mesh.hardware("sternum_adjuster", sternum[mid]+normal[mid]*.34, tangent[mid], across[mid],
                  normal[mid], 3.4, 2.35, sw)
    mesh.normals()
    harness_vertices = len(mesh.data["positions"])
    harness_faces = len(mesh.data["triangles"])
    start = harness_vertices
    mesh.data["positions"].extend(bv.tolist())
    mesh.data["weights"].extend([[[bag_bone,1.]]] * len(bv))
    mesh.data["triangles"].extend((np.asarray(bag["triangles"])+start).tolist())
    mesh.data["uv"].extend(bag["uv"])
    mesh.data["normals"].extend(bag["normals"])
    mesh.data["triangle_materials"].extend([0]*len(bag["triangles"]))
    mesh.data.update(source=DEST+"/"+asset+"."+asset, revision=REVISION, profile=profile,
                     geometry_convention="cross_e1_e2",
                     bag_cap_face_count=bag["cut_cap_faces"],
                     harness_vertex_count=harness_vertices, harness_face_count=harness_faces,
                     bag_shift=offset.tolist(), contract="Closed-envelope fit; smooth bounded stations; sewn rigid bag anchors; explicit parts and three material roles")
    write(R / "Authored" / (profile+".json"), mesh.data)
    row = {"profile":profile, "shirt":shirt, "asset":mesh.data["source"], "margin_cm":margin,
           "bag_shift_cm":offset.tolist(), "paths":measurements, "vertices":len(mesh.data["positions"]),
           "triangles":len(mesh.data["triangles"]), "source":str(R/"Authored"/(profile+".json"))}
    print("HARNESS_AUTHORED", json.dumps(row), flush=True)
    return row


if __name__ == "__main__":
    prepare_bag()
    rows = [build(profile) for profile in PROFILES]
    write(R/"manifest.json", {"revision":REVISION,"variants":rows,"accepted_by_user":False})
