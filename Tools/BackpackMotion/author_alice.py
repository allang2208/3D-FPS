"""Replace ALICE's rigid shoulder islands with a garment-fitted native harness."""
import sys,json,importlib.util
from pathlib import Path
import numpy as np,trimesh
from scipy.interpolate import CubicSpline,PchipInterpolator
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackMotion20261022/AliceFit';R.mkdir(parents=True,exist_ok=True)
I=P/'SourceAssets/ExpeditionBackpack20261022/BodyInputs'
spec=importlib.util.spec_from_file_location('expedition_harness',P/'Tools/ExpeditionBackpack/author.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
read,write,Mesh,visible_mesh,envelope=base.read,base.write,base.Mesh,base.visible_mesh,base.envelope
lift_required,contact_offset,frame=base.lift_required,base.contact_offset,base.frame
smooth_lift,rounded_ring,unit=base.smooth_lift,base.rounded_ring,base.unit
add_waist=base.add_waist
DEST='/Game/Characters/BackpackMotion20261022/Alice'
REVISION='AliceFittedHarness20261022'
PROFILES={k:(shirt,asset.replace('ExpeditionBackpack','AliceBackpack'),margin) for k,(shirt,asset,margin) in base.PROFILES.items()}

def prepare_bag():
    root=P/'SourceAssets/BackpacksReview20261021';data=read(root/'alice_authored.json')
    # The captured old mount is a 180-degree rotation about body Y. Preserve
    # its handedness and side details while replacing the incorrect position.
    v=np.asarray(data['positions']);v[:,[0,2]]*=-1
    triangles=np.asarray(data['triangles'])
    mesh=trimesh.Trimesh(v,triangles,process=False)
    labels=trimesh.graph.connected_component_labels(mesh.face_adjacency,node_count=len(triangles))
    removed=[];keep=np.ones(len(triangles),bool);mats=np.asarray(data['triangle_materials'])
    for label in np.unique(labels):
        ids=np.flatnonzero(labels==label);points=v[np.unique(triangles[ids])]
        if len(ids)==3194 and set(mats[ids])=={1} and points[:,1].min()>9 and np.ptp(points[:,2])>38:
            keep[ids]=False;removed.append({'component':int(label),'faces':len(ids),'bounds':[points.min(0).tolist(),points.max(0).tolist()]})
    if len(removed)!=2:raise RuntimeError('ALICE shoulder island source changed; do not cut arbitrary body faces')
    triangles=triangles[keep];used,inverse=np.unique(triangles,return_inverse=True)
    normals=np.asarray(data['normals'])[keep];normals[:,:,[0,2]]*=-1
    normals=unit(normals)
    v=v[used]+[0.,-31.,122.]
    data['positions']=v.tolist();data['triangles']=inverse.reshape(-1,3).tolist()
    data['normals']=normals.tolist();data['uv']=np.asarray(data['uv'])[keep].tolist()
    data['triangle_materials']=mats[keep].tolist()
    assets=read(root/'alice_saved_assets.json')['materials']
    data['materials']=[{'slot':name,'asset':asset} for name,asset in zip(['AliceCanvas','AliceWebbing','AliceLeather','AliceMetal','AliceLining'],assets)]
    data['anchors']={}
    for side,tag in [(1,'l'),(-1,'r')]:
        data['anchors']['top_'+tag]=[side*8.,-13.,138.]
        data['anchors']['bottom_'+tag]=[side*12.,-13.,105.5]
    data['cut_cap_faces']=0
    write(R/'PreparedBag.json',data);write(R/'removed_rigid_shoulders.json',removed)

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
                 {"slot": "HarnessHardware", "asset": "/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/M_BackpackHarness_Hardware.M_BackpackHarness_Hardware"},
                 {"slot": "HarnessFabric", "asset": "/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/M_BackpackHarness_FabricR1.M_BackpackHarness_FabricR1"}, *bag["materials"][1:]]
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
    add_waist(mesh,body,garment,offset,bag_bone,margin)
    mesh.normals()
    harness_vertices = len(mesh.data["positions"])
    harness_faces = len(mesh.data["triangles"])
    start = harness_vertices
    mesh.data["positions"].extend(bv.tolist())
    mesh.data["weights"].extend([[[bag_bone,1.]]] * len(bv))
    mesh.data["triangles"].extend((np.asarray(bag["triangles"])+start).tolist())
    mesh.data["uv"].extend(bag["uv"])
    mesh.data["normals"].extend(bag["normals"])
    mesh.data["triangle_materials"].extend([0 if m==0 else m+2 for m in bag["triangle_materials"]])
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
    rows=[build(profile) for profile in PROFILES]
    write(R/"manifest.json",{"revision":REVISION,"variants":rows})
