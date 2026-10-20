"""Rebuild curved sight/muzzle mechanisms at their measured native interfaces."""
import bpy,bmesh,json,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
O=Path(__file__).parent;BASE=O.parent;SRC=BASE.parent/'SVCHSketchfab20261017'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(BASE/'SVCH_Refined.blend'))
rig=bpy.data.objects['SK_M4_Infima'];body=bpy.data.objects['SM_SVCH_Body']
hold=json.loads((SRC/'Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm'])
islands=json.loads((SRC/'audit/measurements.json').read_text())['scene_inventory']['islands']
raw=json.loads((O/'mechanism_geometry.json').read_text())
replace={6,7,8,11,12,14,38,39,40,43}
report={'replaced':{},'native_axis':'X forward, Y lateral, Z up; centimetres','materials_preserved':True}
def to_native(v):
    g=(np.array((v.co.x*100,-v.co.y*100,v.co.z*100))-HT)@HR
    return np.array((g[0]+18.7444,g[2],g[1]+1.5268))
def to_blender(p):
    g=np.array((p[0]-18.7444,p[2]-1.5268,p[1]));q=g@HR.T+HT
    return (q[0]/100,-q[1]/100,q[2]/100)
bm=bmesh.new();bm.from_mesh(body.data);remaining=set(bm.verts);removed=set()
while remaining:
    seed=remaining.pop();group={seed};stack=[seed]
    while stack:
        for edge in stack.pop().link_edges:
            for v in edge.verts:
                if v in remaining:remaining.remove(v);group.add(v);stack.append(v)
    points=np.array([to_native(v) for v in group]);lo,hi=points.min(0),points.max(0)
    item=min(islands,key=lambda d:np.linalg.norm(lo-d['bbox_native_units']['min'])+np.linalg.norm(hi-d['bbox_native_units']['max']))
    error=float(np.linalg.norm(lo-item['bbox_native_units']['min'])+np.linalg.norm(hi-item['bbox_native_units']['max']))
    if item['id'] in replace and error<.12:
        removed.add(item['id']);report['replaced'][str(item['id'])]={'name':item['part'],'old_vertices':len(group),'match_error_cm':error}
        bmesh.ops.delete(bm,geom=list(group),context='VERTS')
assert removed==replace,(removed,replace-removed)
bm.to_mesh(body.data);bm.free();body.data.update()
created=[]
def mesh_object(name,verts,faces,material='Body'):
    me=bpy.data.meshes.new(name);me.from_pydata([to_blender(p) for p in verts],[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    ob.data.materials.append(bpy.data.materials['SVCH_'+material])
    return ob
def finish(ob,width_cm=.02):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.normal_update();edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle(0)>math.radians(35)]
    if edges and width_cm:bmesh.ops.bevel(bm,geom=edges,offset=width_cm/100,segments=3,affect='EDGES',clamp_overlap=True,material=0)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-9,edges=list(bm.edges))
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bad=[f for f in bm.faces if f.calc_area()<5e-13]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
    bm.normal_update()
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle(math.pi)<math.radians(35)
    boundary=sum(not e.is_manifold for e in bm.edges)
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    uv=ob.data.uv_layers.new(name='UVMap')
    for f in ob.data.polygons:
        axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=[k for k in range(3) if k!=axis]
        for li in f.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[a]/.25,p[b]/.25)
    ob.vertex_groups.new(name='WPN_root').add(list(range(len(ob.data.vertices))),1,'REPLACE')
    ob.parent=rig;created.append(ob)
    report.setdefault('new_parts',{})[ob.name]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.polygons),'bevel_cm':width_cm,'nonmanifold_edges':boundary}
def ring(name,x0,x1,yc,zc,ryo,rzo,ryi,rzi,opened=False):
    count=72;angles=np.linspace(math.radians(135),math.radians(405),count+1) if opened else np.arange(count)*2*math.pi/count
    verts=[];n=len(angles)
    for x,ry,rz in ((x0,ryo,rzo),(x1,ryo,rzo),(x0,ryi,rzi),(x1,ryi,rzi)):
        for index,a in enumerate(angles):
            y,z=yc+ry*math.cos(a),zc+rz*math.sin(a)
            if opened and ry==ryo:
                # Preserve the source prong tips; curve the lower protective U.
                t=index/(n-1);w=max(0,1-min(t,1-t)/.12)**2
                y-=math.copysign(.0277,y-yc)*w;z-=.0740*w
            verts.append((x,y,z))
    faces=[]
    for i in range(n-1 if opened else n):
        j=(i+1)%n
        faces.extend(((i,j,n+j,n+i),(2*n+j,2*n+i,3*n+i,3*n+j),
                      (j,i,2*n+i,2*n+j),(n+i,n+j,3*n+j,3*n+i)))
    if opened:
        for i in (0,n-1):faces.append((i,n+i,3*n+i,2*n+i))
    ob=mesh_object(name,verts,faces);finish(ob,.018 if opened else .025)
ring('R5_RearAperture',-3.0031,-2.5451,0,14.1552,.4915,.6095,.2278,.2825)
ring('R5_FrontProtectiveU',50.60045,51.4214,0,14.1544,.529,.656,.3922,.4864,True)
def cylinder(name,axis,sections,center,material='Body',segments=48,bevel=.015):
    # sections = axial location, the two measured semi-axes; hollow loops can
    # be supplied as a closed section path (barrel). Ordinary rods get caps.
    across=[a for a in range(3) if a!=axis];verts=[];faces=[]
    for along,r1,r2 in sections:
        for i in range(segments):
            a=i*2*math.pi/segments;p=list(center);p[axis]=along
            p[across[0]]+=r1*math.cos(a);p[across[1]]+=r2*math.sin(a);verts.append(p)
    for j in range(len(sections)-1):
        for i in range(segments):
            k=(i+1)%segments;faces.append((j*segments+i,j*segments+k,(j+1)*segments+k,(j+1)*segments+i))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple((len(sections)-1)*segments+i for i in range(segments)))
    ob=mesh_object(name,verts,faces,material);finish(ob,bevel)
for ident,axis in ((6,1),(7,1),(38,1),(39,1),(40,1),(43,0)):
    points=np.array(raw[str(ident)]['vertices']);lo,hi=points.min(0),points.max(0);center=(lo+hi)/2
    axes=[i for i in range(3) if i!=axis];r=(hi-lo)/2
    cylinder('R5_Pin_'+str(ident),axis,[(lo[axis],r[axes[0]],r[axes[1]]),(hi[axis],r[axes[0]],r[axes[1]])],center)
cylinder('R5_FrontPost',2,[(13.5768,.1228,.0858),(13.7748,.1228,.0858),(13.7748,.0741,.0517),(14.1528,.0741,.0517)],(51.0153,0,0),bevel=.008)

# Continuous hollow barrel and brake, with the original three transverse port
# stations. Ports remain actual holes and the muzzle plane stays unchanged.
outer=[(19.1428,1.0985,1.57295),(25.6565,1.0985,1.57295),(28.199,.7089,1.0151),
       (66.2483,.7089,1.0151),(66.378,.8294,1.18765),(67.6267,.8294,1.18765),
       (67.6267,.9682,1.38645),(73.048,.9682,1.38645),(73.327,.7293,1.04425)]
inner=[(19.1428,.7071,1.01245),(25.6565,.7071,1.01245),(28.199,.3717,.53225),
       (67.719,.3717,.53225),(67.719,.8008,1.14665),(72.990,.8008,1.14665),(73.327,.5768,.8259)]
section=outer+list(reversed(inner));n=64;v=[];f=[]
for x,ry,rz in section:
    for i in range(n):
        a=i*2*math.pi/n;v.append((x,ry*math.cos(a),5.57555+rz*math.sin(a)))
for j in range(len(section)):
    jj=(j+1)%len(section)
    for i in range(n):ii=(i+1)%n;f.append((j*n+i,j*n+ii,jj*n+ii,jj*n+i))
barrel=mesh_object('R5_BarrelAndBrake',v,f,'BarrelSteel')
bm=bmesh.new();bm.from_mesh(barrel.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(barrel.data);bm.free()
for station,(x0,x1) in enumerate(((68.458,69.067),(70.018,70.627),(71.578,72.187))):
    z0,z1=4.5008,6.6503;radius=.18;outline=[]
    for cx,cz,start in ((x1-radius,z1-radius,0),(x0+radius,z1-radius,90),(x0+radius,z0+radius,180),(x1-radius,z0+radius,270)):
        for k in range(9):
            a=math.radians(start+k*90/8);outline.append((cx+radius*math.cos(a),cz+radius*math.sin(a)))
    cv=[(x,y,z) for y in (-2.,2.) for x,z in outline];m=len(outline)
    cf=[tuple(reversed(range(m))),tuple(m+i for i in range(m))]
    cf.extend((i,(i+1)%m,m+(i+1)%m,m+i) for i in range(m))
    cutter=mesh_object('BrakePortCutter',cv,cf)
    bm=bmesh.new();bm.from_mesh(cutter.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cutter.data);bm.free()
    bpy.context.view_layer.objects.active=barrel
    mod=barrel.modifiers.new('RoundedPort','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
finish(barrel,.018)

bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
for ob in created:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
for mod in list(body.modifiers):body.modifiers.remove(mod)
bm=bmesh.new();bm.from_mesh(body.data);bm.normal_update()
for face in bm.faces:face.smooth=True
for edge in bm.edges:edge.smooth=edge.is_manifold and edge.calc_face_angle(math.pi)<math.radians(35)
bm.to_mesh(body.data);bm.free();body.data.update()
wn=body.modifiers.new('MachinedWeightedNormals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50
dg=bpy.context.evaluated_depsgraph_get();finished=bpy.data.meshes.new_from_object(body.evaluated_get(dg),depsgraph=dg)
body.modifiers.clear();body.data=finished;body.modifiers.new('NativeRigidBinding','ARMATURE').object=rig
body.vertex_groups.clear();body.vertex_groups.new(name='WPN_root').add(list(range(len(body.data.vertices))),1,'REPLACE')
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    ob.data.calc_loop_triangles()
    report.setdefault('final_objects',{})[ob.name]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles)}
report['triangles']=sum(v['triangles'] for v in report['final_objects'].values())
report['sight_centres_native_cm']={'rear':[-2.7741,0,14.1552],'front':[51.0153,0,14.1528]}
report['curve_segments']={'rear_aperture':72,'front_guard_arc':72,'pins_and_post':48,'barrel_brake':64}
(O/'model_receipt_r5.json').write_text(json.dumps(report,indent=1))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.objects:
    if ob==rig or ob.type=='MESH':ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVCH_Refined_R5.blend'))
bpy.ops.export_scene.fbx(filepath=str(O/'SK_SVCH_Refined_R5.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
print('SVCH_R5_MECHANISMS_SAVED',json.dumps({'triangles':report['triangles'],'new_parts':report['new_parts']}),flush=True)
