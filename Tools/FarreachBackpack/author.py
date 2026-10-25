"""Meshy expedition pack: preserve shell, fit its worn harness to Jason garments.

Shoulder fitting below is derived from BackpackHarness/author.py's accepted
closed-envelope workflow; this new asset owns its own output and calibration.
"""
import sys,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline,PchipInterpolator
from scipy.spatial import ConvexHull,cKDTree
from scipy.ndimage import gaussian_filter1d
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024';I=R/'BodyInputs'
sys.path.insert(0,str(P/'Tools/BackpackHarness'))
import importlib.util
spec=importlib.util.spec_from_file_location('base_backpack_author',P/'Tools/BackpackHarness/author.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
read,write=base.read,base.write
Mesh,visible_mesh,envelope=base.Mesh,base.visible_mesh,base.envelope
lift_required,contact_offset,frame=base.lift_required,base.contact_offset,base.frame
smooth_lift,rounded_ring,unit=base.smooth_lift,base.rounded_ring,base.unit
DEST='/Game/Characters/FarreachBackpack20261024/SlimFitR2_20261024'
REVISION='FarreachSlimFitR2_20261024'
CALIBRATION=read(R/'calibration.json')
PROFILES={name:(shirt,asset.replace('Backpack','FarreachBackpack'),margin)
          for name,(shirt,asset,margin) in base.PROFILES.items()}
RIG='Jason'
NATIVE_ROTATION=np.eye(3)
NATIVE_TRANSLATION=np.zeros(3)
TEMPLATE=base.DEST+'/SK_Jason_Backpack.SK_Jason_Backpack'
WAIST_POINTS=np.empty((0,3))
BAG_CENTRE=np.array([0.,-18.,122.])
BAG_ROTATION=np.eye(3)
SHOULDER_SHIFT=0.


def fit_height(z):
    return z+SHOULDER_SHIFT*np.clip((np.asarray(z)-104.5)/38.,0.,1.)


def fit_cloud(body,garment):
    points=[]
    for data in [body]+([garment] if garment else []):
        geom=visible_mesh(data);ids=np.unique(geom.faces);v=geom.vertices[ids]
        torso={b['index'] for b in data['bones'] if b['name']=='pelvis' or b['name'].startswith(('spine_','clavicle'))}
        influence=np.asarray([sum(w for b,w in data['weights'][i] if b in torso) for i in ids])
        keep=(abs(v[:,0])<22)&(v[:,2]>84)&(v[:,2]<151.5)&(influence>np.where(v[:,2]>132,.25,.75))
        points.append(v[keep])
        extra=np.asarray(data.get('extra_fit_points',[])).reshape(-1,3)
        if len(extra):points.append(extra[(abs(extra[:,0])<22)&(extra[:,2]>84)&(extra[:,2]<110)])
    if len(WAIST_POINTS):points.append(WAIST_POINTS[(abs(WAIST_POINTS[:,0])<22)&(WAIST_POINTS[:,2]>84)&(WAIST_POINTS[:,2]<110)])
    return np.unique(np.round(np.vstack(points),4),axis=0)


def envelope(body,garment):
    cloud=fit_cloud(body,garment)
    # Include pelvis, trouser waist and tucked shirt routes below the old 104 cm cutoff.
    hull=ConvexHull(cloud);cells=[];bands=[]
    for low in np.arange(84,150,2):
        local=cloud[(cloud[:,2]>=low)&(cloud[:,2]<=min(low+4,151.5))]
        if len(local)>=4 and np.linalg.matrix_rank(local-local.mean(0))==3:
            cells.append(ConvexHull(local).equations)
            bands.append([float(local[:,2].min()),float(local[:,2].max())])
    import trimesh
    return {'frame':hull.equations,'cells':cells,'bands':bands},trimesh.convex.convex_hull(cloud)

def prepare_bag():
    src=np.load(R/'Authored/static_source.npz')
    v=src['positions'].astype(float).copy();f=src['triangles'];n=src['normals'].astype(float).copy()
    # Stow the input's empty shoulder/waist loops against the rear pad. A
    # positive derivative retains every face, UV, shell and material normal.
    start=CALIBRATION['stow_start_y_cm'];span=CALIBRATION['stow_depth_cm'];tail=CALIBRATION['stow_tail_derivative']
    depth=np.maximum(v[:,1]-start,0.)/span
    derivative=np.where(v[:,1]>start,(1-tail)/np.cosh(depth)**2+tail,1.)
    v[:,1]=np.where(v[:,1]>start,start+span*(1-tail)*np.tanh(depth)+tail*(v[:,1]-start),v[:,1])
    n[:,:,1]/=derivative[f];n=unit(n)
    np.savez_compressed(R/'Authored/worn_body.npz',positions=v.astype(np.float32),triangles=f,normals=n.astype(np.float32),uv=src['uv'])
    centre=BAG_CENTRE;v+=centre
    anchors={}
    # Actual folded sewn panel points; leave no empty old anchor coordinates.
    for side,tag in [(1,'l'),(-1,'r')]:
        for key,(x,local_z) in CALIBRATION['anchors_local_cm'].items():
            z=centre[2]+local_z
            near=(abs(v[:,0]-side*x)<1.5)&(abs(v[:,2]-z)<1.5)
            candidates=v[near];y=float(np.quantile(candidates[:,1],.95))
            target=np.array([side*x,y,z]);anchor=candidates[np.argmin(np.linalg.norm(candidates-target,axis=1))]
            anchors[key+'_'+tag]=anchor.tolist()
    v=(v-centre)@BAG_ROTATION+centre
    anchors={key:((np.asarray(point)-centre)@BAG_ROTATION+centre).tolist() for key,point in anchors.items()}
    write(R/('PreparedBag_'+RIG+'.json'),dict(positions=v.tolist(),triangles=[],normals=[],uv=[],cut_cap_faces=0,anchors=anchors,
          materials=[dict(slot='FarreachFabric',asset=DEST+'/M_FarreachBackpack.M_FarreachBackpack')]))
    write(R/('wearable_calibration_'+RIG+'.json'),dict(centre=centre.tolist(),anchors=anchors,retained_faces=len(f),decimation_applied=False,
          stowed_rear_max_cm=float(v[:,1].max()),dimensions_cm=np.ptp(v,axis=0).tolist()))


def add_waist(mesh,body,garment,offset,bag_bone,margin):
    cloud=fit_cloud(body,garment);cloud=cloud[(cloud[:,2]>98)&(cloud[:,2]<111)];hull=ConvexHull(cloud)
    equations={'frame':hull.equations,'cells':[hull.equations]}
    anchors=read(R/('PreparedBag_'+RIG+'.json'))['anchors']
    left=np.asarray(anchors['hip_l'])+offset+[0.,-.25,0.]
    right=np.asarray(anchors['hip_r'])+offset+[0.,-.25,0.]
    control=np.array([left,[16.,-7.,104.5],[17.,3.,104.5],
                      [13.,11.,104.5],[0.,14.,104.5],[-13.,11.,104.5],
                      [-17.,3.,104.5],[-16.,-7.,104.5],right])
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(control,axis=0),axis=1))]
    sample=np.linspace(0,arc[-1],129);path=CubicSpline(arc,control,bc_type='natural')(sample)
    widths=PchipInterpolator(arc,[6.,7.5,7.5,4.6,3.4,4.6,7.5,7.5,6.])(sample)
    thick=PchipInterpolator(arc,[.7,.95,.95,.35,.25,.35,.95,.95,.7])(sample)
    _,_,direction=frame(path,equations)
    contact=contact_offset(path,direction,equations,margin+.7)
    contact=np.where(np.isfinite(contact),np.clip(contact,-4.,5.),0.)
    blend=np.minimum(np.minimum(sample/10.,(sample[-1]-sample)/10.),1.)
    path+=direction*(gaussian_filter1d(contact,3.)*blend)[:,None]
    for _ in range(5):
        _,across,normal=frame(path,equations)
        ring=np.stack([path+across*(widths*f)[:,None]-normal*(thick*.5)[:,None] for f in [-.5,0.,.5]],axis=1)
        required=lift_required(ring.reshape(-1,3),np.repeat(direction,3,axis=0),equations,margin).reshape(-1,3).max(1)
        required[[0,-1]]=0
        lift=smooth_lift(required,pin_ends=True);lift[[0,-1]]=0
        path+=direction*lift[:,None]
    path[[0,-1]]=[left,right]
    by_name={b['name']:b['index'] for b in body['bones']}
    bindings=[]
    for f in blend:
        weights={bag_bone:1.-.8*f,by_name['spine_02']:.4*f,by_name['spine_01']:.4*f}
        bindings.append([[b,w] for b,w in weights.items() if w>1e-7])
    part=mesh.ribbon('padded_hip_belt',path,widths,thick,bindings,equations=equations)
    part['sewn_bag_points']=[left.tolist(),right.tolist()]
    tangent,across,normal=frame(path,equations);mid=len(path)//2
    mesh.hardware('hip_belt_clasp',path[mid]+normal[mid]*.45,tangent[mid],across[mid],normal[mid],4.6,4.1,bindings[mid])

def build(profile):
    shirt, asset, margin = PROFILES[profile]
    body = read(I / "body.json")
    garment = read(I / (shirt+".json")) if shirt else None
    equations, proxy = envelope(body, garment)
    write(R / "Envelopes" / (RIG+'_'+profile+".json"),
          {"positions": proxy.vertices.tolist(), "triangles": proxy.faces.tolist(),
           "frame_equations":equations["frame"].tolist(),"cells":[c.tolist() for c in equations["cells"]]})
    bag = read(R/('PreparedBag_'+RIG+'.json'))
    bv = np.asarray(bag["positions"])
    directions = np.tile([0., -1., 0.], (len(bv), 1))
    print('FARREACH_FITTING',RIG,profile,flush=True)
    # Bounded offline batches prevent the high-detail shell/plane product from
    # exhausting memory alongside an open editor.
    bag_shift=-np.inf
    for cell,(low,high) in zip(equations['cells'],equations['bands']):
        # Backward rays cannot intersect a section outside its expanded Z slab.
        points=bv[(bv[:,2]>=low-.36)&(bv[:,2]<=high+.36)]
        for start in range(0,len(points),2048):
            part=points[start:start+2048]
            contact=contact_offset(part,np.tile([0.,-1.,0.],(len(part),1)),{'cells':[cell]},.35)
            finite=contact[np.isfinite(contact)]
            if len(finite):bag_shift=max(bag_shift,float(finite.max()))
    if abs(bag_shift) > 10:
        raise RuntimeError(f"Bag fit for {profile} needs an excessive {bag_shift:.2f} cm rear shift")
    offset = np.array([0., -bag_shift, 0.])
    bv += offset
    bones = body["bones"]
    by_name = {b["name"]: b["index"] for b in bones}
    s3, s4, s5 = [by_name[name] for name in ("spine_03", "spine_04", "spine_05")]
    bag_bone = s3
    materials = [bag["materials"][0],
                 {"slot": "HarnessHardware", "asset": DEST+"/M_FarreachHarness_Hardware.M_FarreachHarness_Hardware"},
                 {"slot": "HarnessFabric", "asset": DEST+"/M_FarreachHarness_Fabric.M_FarreachHarness_Fabric"}]
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
        control[1:-1,2]=fit_height(control[1:-1,2])
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
        local_margin=margin+max(.7-margin,0)*np.clip((base[:,2]-fit_height(130))/8,0,1)
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
            local_margin=margin+max(.7-margin,0)*np.clip((path[:,2]-fit_height(130))/8,0,1)
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
                        mapped=clavicle if path[j,2]>fit_height(132) else s4
                    elif name.startswith("upperarm") and name.endswith("_"+tag):
                        mapped=upperarm if path[j,2]>fit_height(136) else s4
                    if mapped is not None:
                        weights[mapped]=weights.get(mapped,0)+w*factor
            denom=sum(weights.values())
            weights={b:w/denom for b,w in weights.items()} if denom>1e-5 else {bag_bone:1.}
            # Body muscle correctives can scale several-fold in a cast. Map
            # them to structural joints and bound arm contribution to padding.
            shoulder_blend=float(np.clip((path[j,2]-fit_height(134.))/9.,0.,1.))
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
        buckle_index = front[np.argmin(abs(path[front,2]-fit_height(126.0)))]
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
        index = front[np.argmin(abs(path[front,2]-fit_height(133.)))]
        _,across,normal=frame(path,equations)
        surface=path[index]+normal[index]*(thick[index]*.5+.10)
        # Place the crossing on the pad face, with an actual stitched tab.
        tab=surface+np.linspace(-.42,.42,9)[:,None]*widths[index]*across[index]
        mesh.ribbon('sternum_tab_'+str(side_index),tab,np.full(9,1.95),np.full(9,.14),[bindings[index]]*9)
        endpoints.append(surface+normal[index]*.06)
        weights.append(bindings[index])
    # Small chest bow accommodates pectoral corrective motion without binding
    # the tape to arm muscle helpers that can scale sharply during a cast.
    control = np.array([endpoints[0], [0., max(p[1] for p in endpoints)+1.9, fit_height(133.)], endpoints[1]])
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
    mesh.data.update(source=DEST+"/"+asset+"."+asset, revision=REVISION, profile=profile,
                     geometry_convention="cross_e1_e2",
                     bag_cap_face_count=bag["cut_cap_faces"],
                     harness_vertex_count=harness_vertices, harness_face_count=harness_faces,
                     bag_shift=offset.tolist(), contract="Closed-envelope fit; smooth bounded stations; sewn rigid bag anchors; explicit parts and three material roles")
    mask=np.zeros(harness_vertices)
    tv=np.asarray(mesh.data['triangles']);vv=np.asarray(mesh.data['positions'])
    for part in mesh.data['parts']:
        if part['name'].startswith('shoulder_return_') or part['name']=='padded_hip_belt':
            path=np.asarray(part['path']);arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
            ids=np.unique(tv[part['side_faces']+part['cap_faces']]);_,station=cKDTree(path).query(vv[ids])
            t=np.clip(np.minimum(arc[station],arc[-1]-arc[station])/12.,0.,1.)
            mask[ids]=1.-t*t*(3.-2.*t)
    mesh.data['motion_mask']=mask.tolist()
    # Author around each actual body's surface in a shared torso frame, then
    # return geometry and normals to that body's native reference coordinates.
    mesh.data['positions']=(vv@NATIVE_ROTATION+NATIVE_TRANSLATION).tolist()
    mesh.data['normals']=(np.asarray(mesh.data['normals'])@NATIVE_ROTATION).tolist()
    for part in mesh.data['parts']:
        for key in ('path','base_path','sewn_bag_points'):
            if key in part:part[key]=(np.asarray(part[key])@NATIVE_ROTATION+NATIVE_TRANSLATION).tolist()
    output=R/'Authored'/(RIG+'_'+profile+'.json')
    write(output, mesh.data)
    row = {"profile":RIG+'_'+profile, "fit_profile":profile,"rig":RIG,"template":TEMPLATE,"shirt":shirt, "asset":mesh.data["source"], "margin_cm":margin,
           "bag_shift_cm":offset.tolist(), "paths":measurements, "vertices":len(mesh.data["positions"]),
           "triangles":len(mesh.data["triangles"]), "source":str(output)}
    from scipy.spatial.transform import Rotation
    native_bag=bv@NATIVE_ROTATION+NATIVE_TRANSLATION
    row.update(rigid_location=((BAG_CENTRE+offset)@NATIVE_ROTATION+NATIVE_TRANSLATION).tolist(),
               rigid_rotation_quat=Rotation.from_matrix((BAG_ROTATION@NATIVE_ROTATION).T).as_quat().tolist(),
               body_native_rotation_quat=Rotation.from_matrix(NATIVE_ROTATION.T).as_quat().tolist(),
               bounds_min=native_bag.min(0).tolist(),bounds_max=native_bag.max(0).tolist())
    print("HARNESS_AUTHORED", json.dumps(row), flush=True)
    return row


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(P/'Tools/FarreachBackpack/author_r2.py'),run_name='__main__')
