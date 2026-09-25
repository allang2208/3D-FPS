"""Continuous anatomical forearms and hands, retaining native UE skeleton binding.

Only surface data is authored here. Native UE skeletons, inverse binds and animation
assets are retained by import_native_skin.py, without an FBX skeleton round trip.
"""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
REFERENCE=ROOT/'NativeSkin';OUT=REFERENCE/'SmoothWristV3';OUT.mkdir(exist_ok=True)
DONOR=ROOT/'Donor/BareHands'
only=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def point(v):return Vector((v[0],-v[1],v[2]))*.01
def ue(v):return [v.x*100,-v.y*100,v.z*100]
def frame(a,b,across):
    x=(b-a).normalized();z=x.cross(across).normalized();y=z.cross(x).normalized()
    m=Matrix((x,y,z)).transposed().to_4x4();m.translation=a;return m
def normalize(w):
    w=dict(sorted(((n,v) for n,v in w.items() if v>1e-5),key=lambda x:-x[1])[:8])
    s=sum(w.values());return {n:v/s for n,v in w.items()} if s else {}
def mesh(name,points,faces,weights,uvs,regions):
    data=bpy.data.meshes.new(name);data.from_pydata(points,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    for n in sorted({n for w in weights for n in w}):obj.vertex_groups.new(name=n)
    for i,w in enumerate(weights):
        for n,v in normalize(w).items():obj.vertex_groups[n].add([i],v,'REPLACE')
    for n in ('DefaultSleeves','SkinArms','SkinHands','SkinTorso','SkinRest'):
        data.materials.append(bpy.data.materials.get(n) or bpy.data.materials.new(n))
    layer=data.uv_layers.new(name='UVMap')
    for p in data.polygons:
        p.use_smooth=True;p.material_index=regions[p.index]
        for li,t in zip(p.loop_indices,uvs[p.index]):layer.data[li].uv=t
    return obj
def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
def surface_weights(obj,v):return {obj.vertex_groups[g.group].name:g.weight for g in v.groups}
def loops(edges):
    remaining=set(edges);out=[]
    while remaining:
        e=remaining.pop();seq=[e.verts[0],e.verts[1]]
        while seq[-1]!=seq[0]:
            following=next((q for q in seq[-1].link_edges if q in remaining),None)
            if following is None:break
            remaining.remove(following);seq.append(following.other_vert(seq[-1]))
        if seq[-1]==seq[0]:out.append(seq[:-1])
    return out
def ring_order(ring,origin,axis):
    x=(ring[0].co-origin);x=(x-axis*x.dot(axis)).normalized();y=axis.cross(x).normalized()
    return sorted(ring,key=lambda v:math.atan2((v.co-origin).dot(y),(v.co-origin).dot(x)))

coords=[];tex=[];faces=[];uvs=[];group=''
for line in (DONOR/'base.obj').read_text().splitlines():
    t=line.split()
    if not t:continue
    if t[0]=='v':coords.append(Vector((float(t[1]),-float(t[3]),float(t[2])))*.1)
    elif t[0]=='vt':tex.append((float(t[1]),float(t[2])))
    elif t[0]=='g':group=t[1]
    elif t[0]=='f' and group=='body':
        parts=[s.split('/') for s in t[1:]]
        faces.append([int(s[0])-1 for s in parts]);uvs.append([tex[int(s[1])-1] for s in parts])
skel=json.loads((DONOR/'default.mhskel').read_text());sw=[{} for _ in coords]
for n,values in json.loads((DONOR/'default_weights.mhw').read_text())['weights'].items():
    for i,w in values:sw[i][n]=w
def joint(n):return sum((coords[i] for i in skel['joints'][n]),Vector())/len(skel['joints'][n])
def head(n):return joint(skel['bones'][n]['head'])
def tail(n):return joint(skel['bones'][n]['tail'])

for path in REFERENCE.glob('*_source.json'):
    key=path.name.removesuffix('_source.json');d=json.loads(path.read_text())
    if only and key not in only:continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    native=[point(v) for v in d['positions']];nw=d['weights']
    native_bvh=BVHTree.FromPolygons(native,d['triangles'],all_triangles=True)
    target={n:point(b['position']) for n,b in d['bones'].items()}
    sides=[s for s in ('l','r') if any(w.get('hand_'+s,0)>.5 for w in nw)]
    axes={s:(target['hand_'+s]-target['lowerarm_'+s]).normalized() for s in sides}
    lengths={s:(target['hand_'+s]-target['lowerarm_'+s]).length for s in sides}
    source_cut={s:-lengths[s]*.93 for s in sides}
    skin_cut={s:-lengths[s]*.85 for s in sides}
    def axial(p,s):return (p-target['hand_'+s]).dot(axes[s])
    regions=[]
    for f,m in zip(d['triangles'],d['triangle_materials']):
        if key!='Body':regions.append(0 if d['materials'][m]['slot']=='MI_Manny_01' else 1)
        else:
            arm=sum(v for i in f for n,v in nw[i].items() if any(x in n for x in ('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')))/3
            torso=sum(v for i in f for n,v in nw[i].items() if 'spine' in n or 'clavicle' in n)/3
            regions.append(1 if arm>.3 else 3 if torso>.35 else 4)
    original=mesh('NativeForearms_'+key,native,[f[::-1] for f in d['triangles']],nw,[v[::-1] for v in d['uv']],regions)
    bm=bmesh.new();bm.from_mesh(original.data)
    # UE splits render vertices at UV seams; reconnect identical surface points
    # before cutting a closed forearm ring. Loop UVs remain separate.
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    deform=bm.verts.layers.deform.active
    names={g.index:g.name for g in original.vertex_groups}
    for s in sides:
        select=[v for v in bm.verts if sum(w for g,w in v[deform].items() if names[g].endswith('_'+s) and any(x in names[g] for x in ('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')))>.5]
        selected=set(select)
        es=[e for e in bm.edges if all(v in selected for v in e.verts)]
        fs=[f for f in bm.faces if all(v in selected for v in f.verts)]
        bmesh.ops.bisect_plane(bm,geom=select+es+fs,plane_co=target['hand_'+s]+axes[s]*source_cut[s],
            plane_no=axes[s],dist=1e-7,clear_outer=True,clear_inner=False)
    bm.to_mesh(original.data);bm.free()

    transforms={};mapping={}
    for s in sides:
        S=s.upper();wrist='wrist.'+S
        across=head('finger2-1.'+S)-head('finger5-1.'+S)
        ta=target['index_01_'+s]-target['pinky_01_'+s]
        definitions={wrist:('hand_'+s,head(wrist),head('finger3-1.'+S),target['hand_'+s],target['middle_01_'+s])}
        for j in (1,2):
            definitions['lowerarm0'+str(j)+'.'+S]=('lowerarm_'+s,head('lowerarm01.'+S),head(wrist),target['lowerarm_'+s],target['hand_'+s])
            definitions['upperarm0'+str(j)+'.'+S]=('upperarm_'+s,head('upperarm01.'+S),head('lowerarm01.'+S),target['upperarm_'+s],target['lowerarm_'+s])
        for f,stem in enumerate(('thumb','index','middle','ring','pinky'),1):
            for j in (1,2,3):
                src=f'finger{f}-{j}.{S}';dst=f'{stem}_{j:02}_{s}';a=target[dst]
                if j<3:b=target[f'{stem}_{j+1:02}_{s}']
                else:
                    direction=(a-target[f'{stem}_02_{s}']).normalized()
                    reach=max(((p-a).dot(direction) for p,w in zip(native,nw) if w.get(dst,0)>.5),default=.022)
                    b=a+direction*max(.014,min(.04,reach-.001))
                definitions[src]=(dst,head(src),tail(src),a,b)
        for src,(dst,a,b,c,e) in definitions.items():
            scale=(e-c).length/(b-a).length
            transforms[src]=frame(c,e,ta)@Matrix.Diagonal((scale,scale,scale,1))@frame(a,b,across).inverted();mapping[src]=dst
        for j in range(1,5):
            n=f'metacarpal{j}.{S}';transforms[n]=transforms[wrist];mapping[n]='hand_'+s
    hp=[];hw=[]
    for p,w in zip(coords,sw):
        valid={n:v for n,v in w.items() if n in transforms};total=sum(valid.values())
        hp.append(sum((transforms[n]@p*v for n,v in valid.items()),Vector())/total if total else p)
        ws={}
        for n,v in valid.items():ws[mapping[n]]=ws.get(mapping[n],0)+v
        hw.append(normalize(ws))
    # Keep the accepted forearm twist distribution through the wrist junction.
    # MakeHuman supplies finger anatomy; native sleeve-side weights supply the
    # lowerarm/twist blend, so turning the wrist cannot unwind the new seam.
    for i,(p,w) in enumerate(zip(hp,hw)):
        if not w:continue
        s=max(sides,key=lambda s:sum(v for n,v in w.items() if n.endswith('_'+s)))
        distance=axial(p,s)
        if not -lengths[s]*1.05<distance<-.003:continue
        blend=max(0,min(1,(-distance-.003)/.029));blend=blend*blend*(3-2*blend)
        origin=target['hand_'+s]+axes[s]*distance;radial=p-origin
        near,normal,ti,_=native_bvh.ray_cast(origin,radial.normalized(),.15)
        if near is None:near,normal,ti,_=native_bvh.find_nearest(p)
        face=d['triangles'][ti];a,b,c=(native[v] for v in face)
        bc=barycentric_transform(near,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        merged={n:v*(1-blend) for n,v in w.items()}
        for vi,factor in zip(face,bc):
            for n,v in nw[vi].items():merged[n]=merged.get(n,0)+max(0,factor)*v*blend
        hw[i]=normalize(merged)
    chosen=[]
    for i,f in enumerate(faces):
        s='l' if sum(coords[v].x for v in f)>0 else 'r'
        if s in sides and all(sum(v for n,v in sw[j].items() if n in transforms)>.99 for j in f) and any(axial(hp[j],s)>-lengths[s]*1.05 for j in f):chosen.append(i)
    ids=sorted({v for i in chosen for v in faces[i]});remap={v:i for i,v in enumerate(ids)}
    bare=mesh('AnatomicalHands_'+key,[hp[i] for i in ids],[[remap[v] for v in faces[i]] for i in chosen],
        [hw[i] for i in ids],[uvs[i] for i in chosen],[2]*len(chosen))
    activate(bare);sub=bare.modifiers.new('AnatomicalSurface','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    bm=bmesh.new();bm.from_mesh(bare.data);deform=bm.verts.layers.deform.active;names={g.index:g.name for g in bare.vertex_groups}
    for s in sides:
        vs=[v for v in bm.verts if sum(w for g,w in v[deform].items() if names[g].endswith('_'+s))>.99];vsset=set(vs)
        es=[e for e in bm.edges if all(v in vsset for v in e.verts)];fs=[f for f in bm.faces if all(v in vsset for v in f.verts)]
        bmesh.ops.bisect_plane(bm,geom=vs+es+fs,plane_co=target['hand_'+s]+axes[s]*skin_cut[s],plane_no=axes[s],dist=1e-7,clear_outer=False,clear_inner=True)
        for f in bm.faces:
            if all(sum(w for g,w in v[deform].items() if names[g].endswith('_'+s))>.99 for v in f.verts) and axial(f.calc_center_median(),s)<-.008:f.material_index=1
    bm.to_mesh(bare.data);bm.free()
    activate(original);bare.select_set(True);bpy.ops.object.join();obj=original
    bm=bmesh.new();bm.from_mesh(obj.data);deform=bm.verts.layers.deform.active
    group_names={g.index:g.name for g in obj.vertex_groups}
    for s in sides:
        h=target['hand_'+s];axis=axes[s]
        native_edges=[e for e in bm.edges if e.is_boundary and all(abs(axial(v.co,s)-source_cut[s])<.00002 for v in e.verts)]
        hand_edges=[e for e in bm.edges if e.is_boundary and all(abs(axial(v.co,s)-skin_cut[s])<.00002 for v in e.verts)]
        nloops=loops(native_edges);hloops=loops(hand_edges)
        if not nloops or not hloops:raise RuntimeError(f'No closed forearm junction: {key} {s}, edges={len(native_edges)}/{len(hand_edges)}, loops={len(nloops)}/{len(hloops)}')
        perimeter=lambda ring:sum((ring[i].co-ring[(i+1)%len(ring)].co).length for i in range(len(ring)))
        nr=max(nloops,key=perimeter);hr=max(hloops,key=perimeter)
        # The seam is now near the elbow, with continuous donor topology from
        # mid-forearm through the wrist. Keep the accepted palm/fingers untouched.
        across=target['index_01_'+s]-target['pinky_01_'+s]
        x=(across-axis*across.dot(axis)).normalized();y=axis.cross(x).normalized();tau=math.tau
        def angle(p):return math.atan2((p-h).dot(y),(p-h).dot(x))%tau
        def ordered(r):return sorted(r,key=lambda v:angle(v.co))
        nr=ordered(nr);hr=ordered(hr)
        def sample(r,theta):
            angles=[angle(v.co) for v in r]
            k=next((i for i,a in enumerate(angles) if a>theta),len(r))
            j=(k-1)%len(r);k%=len(r);lo=angles[j];hi=angles[k]
            if hi<=lo:hi+=tau
            if theta<lo:theta+=tau
            t=(theta-lo)/max(1e-8,hi-lo)
            return r[j].co.lerp(r[k].co,t),normalize({g:r[j][deform].get(g,0)*(1-t)+r[k][deform].get(g,0)*t for g in set(r[j][deform])|set(r[k][deform])})
        samples=[sample(nr,tau*i/64)[0] for i in range(64)]
        radii=[(p-h-axis*axial(p,s)).length for p in samples]
        # Remove cloth-scale folds from the proximal cut without circularizing
        # the arm: retain the broad offset and elliptical cross-section terms.
        coeff=[sum(radii)/64]
        for harmonic in (1,2):
            coeff.extend([sum(radii[i]*math.cos(harmonic*tau*i/64) for i in range(64))/32,
                          sum(radii[i]*math.sin(harmonic*tau*i/64) for i in range(64))/32])
        def radius(theta):return coeff[0]+coeff[1]*math.cos(theta)+coeff[2]*math.sin(theta)+coeff[3]*math.cos(2*theta)+coeff[4]*math.sin(2*theta)
        def smooth(t):t=max(0,min(1,t));return t*t*t*(t*(t*6-15)+10)
        adjustments=[]
        for v in bm.verts:
            if sum(w for g,w in v[deform].items() if group_names[g].endswith('_'+s))<.9:continue
            distance=axial(v.co,s);theta=angle(v.co);origin=h+axis*distance;radial=v.co-origin
            if radial.length<1e-6:continue
            if source_cut[s]-.035<distance<=source_cut[s]+.00002 and all(f.material_index==1 for f in v.link_faces):
                old,_=sample(nr,theta);old_radius=(old-h-axis*source_cut[s]).length
                delta=(radius(theta)-old_radius)*smooth((distance-source_cut[s]+.035)/.035)
                adjustments.append((v,v.co+radial.normalized()*delta))
            elif skin_cut[s]-.00002<=distance<skin_cut[s]+.09:
                old,_=sample(hr,theta);old_radius=(old-h-axis*skin_cut[s]).length
                delta=(radius(theta)*.975-old_radius)*(1-smooth((distance-skin_cut[s])/.09))
                adjustments.append((v,v.co+radial.normalized()*delta))
        for v,p in adjustments:v.co=p
        rings=[nr]
        for step in (1,2,3):
            t=step/4;ring=[]
            for i in range(64):
                theta=tau*i/64;a,wa=sample(nr,theta);b,wb=sample(hr,theta)
                v=bm.verts.new(a.lerp(b,t));v[deform].update(normalize({g:wa.get(g,0)*(1-t)+wb.get(g,0)*t for g in set(wa)|set(wb)}));ring.append(v)
            rings.append(ordered(ring))
        rings.append(hr)
        for first,second in zip(rings,rings[1:]):
            i=j=0
            while i<len(first) or j<len(second):
                next_a=angle(first[(i+1)%len(first)].co)+(tau if i+1>=len(first) else 0)
                next_b=angle(second[(j+1)%len(second)].co)+(tau if j+1>=len(second) else 0)
                if i<len(first) and (j>=len(second) or next_a<=next_b):vs=(first[i%len(first)],first[(i+1)%len(first)],second[j%len(second)]);i+=1
                else:vs=(first[i%len(first)],second[(j+1)%len(second)],second[j%len(second)]);j+=1
                face=bm.faces.new(vs);face.material_index=1;face.smooth=True
        for ring in nloops+hloops:
            if ring is nr or ring is hr:continue
            # Other nested source shells are already hidden by the outer bridge.
            # Only cap rings not consumed by the chosen bridge.
            edges=[e for v in ring for e in v.link_edges if e.is_boundary and all(q in ring for q in e.verts)]
            if edges:bmesh.ops.holes_fill(bm,edges=list(set(edges)),sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
    obj.data.calc_loop_triangles()
    # Duplicate UV-seam vertices only, retaining weights and smooth normals.
    verts=[];normals=[];uv=[];ws=[];tris=[];mats=[];lookup={};layer=obj.data.uv_layers.active.data
    for tri in obj.data.loop_triangles:
        ids=[]
        for vi,li in zip(tri.vertices,tri.loops):
            n=obj.data.vertices[vi].normal;t=layer[li].uv;identity=(vi,round(t.x,7),round(t.y,7))
            if identity not in lookup:
                lookup[identity]=len(verts);v=obj.data.vertices[vi]
                verts.append(ue(v.co));normals.append([n.x,-n.y,n.z]);uv.append([t.x,t.y]);ws.append(normalize(surface_weights(obj,v)))
            ids.append(lookup[identity])
        # DynamicMesh uses UE's front-face convention. Reflecting Y already
        # converts the Blender winding; reversing the indices a second time
        # produces faces opposite the preserved outward vertex normals.
        tris.append(ids);mats.append(obj.data.polygons[tri.polygon_index].material_index)
    data={'surface_export_version':2,'anatomy_revision':3,'profile':key,'source':d['source'],'vertices':verts,'normals':normals,'uv':uv,'weights':ws,'triangles':tris,'materials':mats,'sides':sides}
    (OUT/(key+'_skin.json')).write_text(json.dumps(data,separators=(',',':')))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'_BareSkin.blend')))
    print('NATIVE_BARE_SKIN_AUTHORED',key,len(verts),len(tris),flush=True)
