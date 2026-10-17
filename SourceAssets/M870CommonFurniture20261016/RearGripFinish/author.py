"""Continuous native-neck fit, seated end lips and valid UV0 tangent frames."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.geometry import convex_hull_2d
O=Path(__file__).parent;P=O.parent;S=P.parent
sys.path.insert(0,str(S/'HK416CommonAttachments20260930'))
from reargrip_interfaces import remember_normals,restore_normals
KEYS=('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip')
C=json.loads((P/'inputs.json').read_text());R=json.loads((P/'models.json').read_text());REPORT={}
bpy.context.preferences.filepaths.save_version=0
def load_native():
    with bpy.data.libraries.load(str(P/'NativeFurniture.blend'),link=False) as (_,d):d.objects=['NativeFurniture']
    ob=d.objects[0];bpy.context.collection.objects.link(ob);return ob
def uv0(mesh):
    # Both material graphs consume UV0. Keep its original corner coordinates;
    # remove unused FBX lightmap/duplicate diffuse channels before joining.
    while len(mesh.uv_layers)>1:mesh.uv_layers.remove(mesh.uv_layers[-1])
    if not mesh.uv_layers:mesh.uv_layers.new(name='UV0')
    mesh.uv_layers[0].name='UV0';mesh.uv_layers.active_index=0;mesh.uv_layers[0].active_render=True
def planar(mesh,face):
    axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
    origin=mesh.vertices[face.vertices[0]].co.copy()
    for li in face.loop_indices:
        p=mesh.vertices[mesh.loops[li].vertex_index].co-origin;mesh.uv_layers[0].data[li].uv=(p[axes[0]]/.04,p[axes[1]]/.04)
def cut(ob,axis,value,positive):
    bm=bmesh.new();bm.from_mesh(ob.data);normal=[0,0,0];normal[axis]=1;point=[0,0,0];point[axis]=value
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=point,plane_no=normal,clear_inner=positive,clear_outer=not positive)
    bm.to_mesh(ob.data);bm.free()
def outline(mesh,axis,value):
    axes=[i for i in range(3) if i!=axis];hits=[]
    for e in mesh.edges:
        a,b=[mesh.vertices[i].co for i in e.vertices]
        if (a[axis]-value)*(b[axis]-value)<0:hits.append(a.lerp(b,(value-a[axis])/(b[axis]-a[axis])))
    if not hits:raise RuntimeError('Missing manufacturing section '+str(value))
    return [Vector((p[axes[0]],p[axes[1]])) for p in hits]
def radial(points,count=128):
    hull=[points[i] for i in convex_hull_2d(points)]
    center=Vector(((min(p.x for p in hull)+max(p.x for p in hull))*.5,(min(p.y for p in hull)+max(p.y for p in hull))*.5));out=[]
    cross=lambda a,b:a.x*b.y-a.y*b.x
    for i in range(count):
        a=math.tau*i/count;ray=Vector((math.cos(a),math.sin(a)));ds=[]
        for p,q in zip(hull,hull[1:]+hull[:1]):
            e=q-p;den=cross(ray,e)
            if abs(den)<1e-12:continue
            d=cross(p-center,e)/den;t=cross(p-center,ray)/den
            if d>0 and -1e-6<=t<=1.000001:ds.append(d)
        if not ds:raise RuntimeError('Open section')
        out.append(center+ray*max(ds))
    return center,out
bpy.ops.wm.read_factory_settings(use_empty=True);native=load_native()
Y0=-.166;STEP=.0005
stations=[radial(outline(native.data,1,Y0-i*STEP)) for i in range(109)]
def native_point(y,angle):
    a=(angle%math.tau)*128/math.tau;j=int(a);u=a-j
    pos=(Y0-y)/STEP;i=min(len(stations)-2,max(0,int(pos)));v=max(0,min(1,pos-i))
    def at(k):
        c,ring=stations[k];p=ring[j%128].lerp(ring[(j+1)%128],u)
        return c,p
    c0,p0=at(i);c1,p1=at(i+1);c=c0.lerp(c1,v);p=p0.lerp(p1,v)
    return Vector((p.x,y,p.y)),Vector((p.x-c.x,0,p.y-c.y)).normalized()

for key in KEYS:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    bpy.ops.import_scene.fbx(filepath=str(P/'Inputs'/(key+'.fbx')),use_anim=False)
    donor=next(o for o in bpy.context.scene.objects if o.type=='MESH');donor.data.transform(donor.matrix_world);donor.parent=None;donor.matrix_world=Matrix.Identity(4);donor.modifiers.clear()
    for ob in list(bpy.context.scene.objects):
        if ob!=donor:bpy.data.objects.remove(ob,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(donor.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES');bm.to_mesh(donor.data);bm.free()
    # Remove the original rifle collar and curved bottom before fitting. Clamping
    # those caps onto a single native ring caused folded/zero-area triangles.
    zhi=-.012;zlo=-.061 if key=='balanced_reargrip' else -.065
    source=[]
    for i in range(129):
        z=zlo+(zhi-zlo)*i/128;pts=outline(donor.data,2,z)
        lo=Vector((min(p.x for p in pts),min(p.y for p in pts)));hi=Vector((max(p.x for p in pts),max(p.y for p in pts)))
        source.append(((lo+hi)*.5,(hi-lo)*.5))
    cut(donor,2,zlo,True);cut(donor,2,zhi,False);uv0(donor.data)
    bm=bmesh.new();bm.from_mesh(donor.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.to_mesh(donor.data);bm.free()
    donor.data.materials.clear();donor.data.materials.append(bpy.data.materials.new('M870_GripBody'));donor.data.materials.append(bpy.data.materials.new('M870_NeckTransition'))
    for f in donor.data.polygons:f.material_index=0
    for v in donor.data.vertices:
        t=(zhi-v.co.z)/(zhi-zlo);p=max(0,min(128,(1-t)*128));i=min(127,int(p));u=p-i
        c=source[i][0].lerp(source[i+1][0],u);half=source[i][1].lerp(source[i+1][1],u)
        x=(v.co.x-c.x)/max(.001,half.x);z=(v.co.y-c.y)/max(.001,half.y)
        y=-.170-.042*t;point,axis=native_point(y,math.atan2(z,x))
        relief=.00045*math.atan((math.sqrt(x*x+z*z)-1)*3.)
        if 0<=t<=1:offset=.00028+relief
        else:
            fade=min(1,(abs(t) if t<0 else t-1)*(zhi-zlo)/.003);offset=(.00028+relief)*(1-fade)-.00015*fade
        v.co=point+axis*offset
    # Topology cleanup follows triangulation, so n-gon microtriangles cannot
    # survive the pass. This only removes sub-micron fitting remnants.
    donor.data.normals_split_custom_set([(0,0,0)]*len(donor.data.loops))
    bm=bmesh.new();bm.from_mesh(donor.data);bmesh.ops.triangulate(bm,faces=list(bm.faces))
    before=len(bm.faces);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_area()<1e-12 or 2*f.calc_area()/max(e.calc_length() for e in f.edges)<1e-6],context='FACES')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(donor.data);bm.free();donor.data.update()
    for f in donor.data.polygons:
        f.use_smooth=True
        q=[donor.data.uv_layers[0].data[i].uv for i in f.loop_indices]
        if f.material_index==1 or abs((q[1]-q[0]).cross(q[2]-q[0]))<1e-9:planar(donor.data,f)
    # Rebuild the deformed donor's normal space only after topology is final.
    # Pre-deformation custom-normal fan encodings cannot survive this warp.
    donor.data.normals_split_custom_set([(0,0,0)]*len(donor.data.loops));donor.data.update()
    # Build closed, regular seam bands from measured native sections. Extruding
    # every fragmented donor edge creates micrometre-wide collar triangles.
    # These seated lofts cover both cuts without moving the hand contact.
    bands=[]
    for center in (-.170,-.212):
        points=[];faces=[];count=128
        sections=[(-.0025,-.00015),(-.0025,.00010),(-.0015,.00085),(0,.00110),(.0015,.00085),(.0025,.00010),(.0025,-.00015)]
        for dy,offset in sections:
            for j in range(count):
                p,axis=native_point(center+dy,math.tau*j/count);points.append(p+axis*offset)
        for k in range(len(sections)):
            kk=(k+1)%len(sections)
            faces.extend((k*count+j,k*count+(j+1)%count,kk*count+(j+1)%count,kk*count+j) for j in range(count))
        me=bpy.data.meshes.new('M870_ClosedContactLip');me.from_pydata(points,[],faces);me.update();me.materials.append(bpy.data.materials.get('M870_NeckTransition'));me.uv_layers.new(name='UV0')
        for face in me.polygons:
            # Individual physical-scale UV quads keep the wrap seam explicit.
            k=face.index//count;j=face.index%count
            for li,(u,v) in zip(face.loop_indices,((j/count,k*.02),((j+1)/count,k*.02),((j+1)/count,(k+1)*.02),(j/count,(k+1)*.02))):me.uv_layers[0].data[li].uv=(u*3,v)
            face.use_smooth=True
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
        band=bpy.data.objects.new('ClosedContactLip',me);bpy.context.collection.objects.link(band);bands.append(band)
    # Preserve the original rigid native neck and exact rear interface plane.
    neck=load_native();uv0(neck.data);remember_normals(neck.data);cut(neck,1,-.22,True)
    neck.data.materials.clear();neck.data.materials.append(bpy.data.materials.new('M870_NativeContact'));neck.data.materials.append(bpy.data.materials.get('M870_NeckTransition'))
    for f in neck.data.polygons:f.material_index=0
    bm=bmesh.new();bm.from_mesh(neck.data)
    bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if abs(v.co.y+.22)<1e-6],dist=1e-7)
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y+.22)<1e-6 for v in e.verts)]
    for f in bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']:f.material_index=1
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(neck.data);bm.free();restore_normals(neck.data);neck.data.update()
    for f in neck.data.polygons:
        if f.material_index==1:planar(neck.data,f)
    if key==KEYS[0]:
        samples=[]
        for face in neck.data.polygons:
            y=sum(neck.data.vertices[i].co.y for i in face.vertices)/len(face.vertices)
            if face.material_index==0 and -.214<y<-.168:
                q=[neck.data.uv_layers[0].data[i].uv for i in face.loop_indices];samples.append([sum(v.x for v in q)/len(q),sum(v.y for v in q)/len(q)])
        (O/'native_contact_uv.json').write_text(json.dumps(samples))
    bpy.ops.object.select_all(action='DESELECT');donor.select_set(True);neck.select_set(True)
    for band in bands:band.select_set(True)
    bpy.context.view_layer.objects.active=donor;bpy.ops.object.join()
    ob=donor;ob.name='SM_M870_'+key;m=ob.data;m.update()
    # MikkTSpace can cancel a split corner normal at a folded source microface.
    # Use that face's actual normal at affected corners, then derive its tangent.
    normals=[n.vector.copy() for n in m.corner_normals];fixed=0
    for f in m.polygons:
        for li in f.loop_indices:
            if normals[li].length_squared<.5:normals[li]=f.normal.copy();fixed+=1
    m.update();m.normals_split_custom_set(normals);m.update();m.calc_tangents(uvmap='UV0')
    bad=[l.index for l in m.loops if l.tangent.length_squared<.5 or l.bitangent.length_squared<.5]
    if bad:
        affected=set(bad)
        for f in m.polygons:
            if any(i in affected for i in f.loop_indices):
                planar(m,f);f.use_smooth=False
                for i in f.loop_indices:normals[i]=f.normal.copy()
        m.update();m.normals_split_custom_set(normals);m.update();m.calc_tangents(uvmap='UV0')
    bad=[l.index for l in m.loops if l.tangent.length_squared<.5 or l.bitangent.length_squared<.5]
    if bad:
        for f in m.polygons:
            if any(i in bad for i in f.loop_indices):print('BAD_TANGENT_FACE',key,f.index,f.area,[list(m.vertices[i].co) for i in f.vertices],[(list(m.corner_normals[i].vector),list(m.loops[i].tangent)) for i in f.loop_indices],flush=True)
        raise RuntimeError(key+' still has invalid authored tangent corners: '+str(len(bad)))
    f=P/'Meshes'/(ob.name+'.fbx');bpy.data.libraries.write(str(f.with_name(ob.name+'_Editable.blend')),{ob},fake_user=True)
    bpy.ops.export_scene.fbx(filepath=str(f),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    base='/Game/Weapons/M870/CommonFurniture20261016/Materials/'
    bindings={'M870_GripBody':base+'MI_M870_'+key,'M870_NeckTransition':base+'MI_M870_RearGripTransition','M870_NativeContact':base+'M_M870_RearGripNativeContact'}
    R['parts'].setdefault(key,{'source':C['assets'][key]['path']}).update(file=str(f),bindings=bindings,slots=[s.name for s in m.materials],triangles=len(m.polygons),explicit_tangents=True,revision='RearGripFinish',fit='Continuous native-neck sleeve with seated physical lips; original native web and right-hand pose preserved')
    area=sum(f.area for f in m.polygons if f.material_index==0)*10000;uvarea=0.
    for face in m.polygons:
        if face.material_index==0:
            a,b,c=[m.uv_layers[0].data[i].uv for i in face.loop_indices];uvarea+=abs((b-a).cross(c-a))*.5
    REPORT[key]={'bead_scale':math.sqrt(area/max(uvarea,1e-8))/.42,'triangles':len(m.polygons),'zero_tangent_corners':len(bad),'repaired_corner_normals':fixed,'uv0':'source UV for body/native contact; physical planar UV for new seam lips/cap','native_cap_material':'M870_NeckTransition','native_contact_vertices_edited':False,'grip_envelope_offset_m':[-.00043,.00110]}
    print('M870_REAR_FINISH_AUTHORED',key,REPORT[key],flush=True)
(P/'models.json').write_text(json.dumps(R,indent=2));(O/'authoring.json').write_text(json.dumps(REPORT,indent=2))
