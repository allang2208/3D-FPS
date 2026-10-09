"""Scoped pots and detailed open-top waste bins, authored with existing PBR assets."""
import bpy,bmesh,json,math,sys,hashlib,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;OUT=ROOT/'Authored'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(PARENT/'Scripts'));import geometry as g
profile=runpy.run_path(str(ROOT/'layout.py'));BASE=profile['BASE']
CFG=profile['revise'](json.loads((PARENT/'Config/layout.json').read_text('utf8')))
ROLES=json.loads((PARENT/'Config/materials.json').read_text('utf8'))
for key,col,rough,metal in [('SatinSteel',[.42,.45,.46],.48,.9),('BinPaint',[.034,.065,.053],.68,0),('BinLiner',[.013,.018,.016],.43,0)]:
    ROLES[key]=dict(basecolor_linear=col,roughness=rough,metallic=metal,uv_meters=1.,existing_ue_path=BASE+'/Materials/M_RHU_'+key)
ROLES['Paper']=dict(basecolor_linear=[.64,.62,.53],roughness=.8,metallic=0,uv_meters=1.,existing_ue_path='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Materials/M_RH2_Paper')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
g.G.clear();g.C.clear();g.ROOM='Reception';materials={}
for key,r in ROLES.items():
    m=bpy.data.materials.new('RHU_'+key);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*r['basecolor_linear'],1);p.inputs['Roughness'].default_value=r['roughness'];p.inputs['Metallic'].default_value=r['metallic'];materials[key]=m

def cylinder_hull(kind,c,r,h,n=24):
    vs=[(c[0]+r*math.cos(i*math.tau/n),c[1]+r*math.sin(i*math.tau/n),c[2]+z) for z in (0,h) for i in range(n)]
    fs=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    g.hull(kind,vs,fs)

def annular_profile(kind,profile,mat,segments=80):
    # Close the cross-section around the central aperture, never cap its mouth.
    vs=[(r*math.cos(i*math.tau/segments),r*math.sin(i*math.tau/segments),z) for z,r in profile for i in range(segments)]
    fs=[];uv=[]
    for k,(z,r) in enumerate(profile):
        kk=(k+1)%len(profile);zz,rr=profile[kk];circ=math.pi*(r+rr)
        for i in range(segments):
            j=(i+1)%segments;fs.append((k*segments+i,k*segments+j,kk*segments+j,kk*segments+i))
            uv.append([(i/segments*circ,z),((i+1)/segments*circ,z),((i+1)/segments*circ,zz),(i/segments*circ,zz)])
    g.poly(kind,vs,fs,mat,uv,smooth=True)

for x,y,z in CFG['pots']:
    g.lathe('Planters',(x,y,z),(0,0,1),[(0,.40),(.045,.43),(.57,.49),(.63,.49),(.63,.455),(.58,.455),(.08,.36)],'Stone',64)
    cylinder_hull('Planters',(x,y,z),.49,.63)
    g.cylinder('PlanterSoil',(x,y,z+.54),(x,y,z+.59),.446,'Soil',48)
    g.ring('PlanterTrim',(x,y,z+.612),(0,0,1),.495,.45,.018,'Brass',64)

# Keep the established 44 cm diameter / 68 cm height. Rolled mouths, a
# separate lift-off rim, liner cuff, welded seam and rubber foot add real depth.
kind='WasteBins';g.lathe(kind,(0,0,0),(0,0,1),[(.03,.204),(.043,.218),(.060,.220),(.590,.220),(.620,.216),(.632,.213),(.632,.208),(.600,.210),(.075,.210)],'SatinSteel',80)
g.lathe(kind,(0,0,0),(0,0,1),[(0,.193),(.008,.216),(.023,.222),(.043,.222),(.054,.214),(.054,.193)],'Rubber',64)
annular_profile(kind,[(.633,.214),(.642,.227),(.656,.228),(.673,.220),(.683,.204),(.683,.138),(.677,.130),(.666,.130),(.655,.141),(.646,.201)],'SatinSteel')
g.torus(kind,(0,0,.640),(0,0,1),.213,.0045,'BinLiner',80,10)
# Recessed inner bucket and a real dark bottom; the opening is not a flat cap.
g.lathe(kind,(0,0,0),(0,0,1),[(.19,.119),(.23,.124),(.63,.129),(.661,.129),(.661,.126),(.23,.119)],'BinLiner',64)
for i in range(24):
    a=i*math.tau/24;r=.126
    g.tube(kind,[(r*math.cos(a),r*math.sin(a),.27),((r+.001)*math.cos(a+.014),(r+.001)*math.sin(a+.014),.47),(r*math.cos(a+.026),r*math.sin(a+.026),.65)],.0012,'BinLiner',6)
for z in (.087,.557):g.torus(kind,(0,0,z),(0,0,1),.2197,.002,'SatinSteel',80,8)
g.ring(kind,(0,0,.311),(0,0,1),.222,.2202,.052,'BinPaint',80)
g.cylinder(kind,(0,.2205,.075),(0,.2205,.605),.0016,'SatinSteel',12)
for z in (.13,.52):
    g.cylinder(kind,(0,.220,z),(0,.225,z),.004,'SatinSteel',16)
    g.box(kind,(0,.2251,z),(.006,.0005,.001),'BinLiner')
for s in (-1,1):
    g.tube(kind,[(s*.214,-.031,.52),(s*.236,-.029,.52),(s*.241,.026,.52),(s*.213,.031,.52)],.004,'SatinSteel',12)
g.box(kind,(0,-.2215,.407),(.108,.004,.038),'BinPaint')
# Small stamped lettering with actual proportions, kept proud of the plate.
curve=bpy.data.curves.new('Waste lettering','FONT');curve.body='WASTE';curve.align_x='CENTER';curve.align_y='CENTER';curve.size=.020;curve.extrude=.00025;curve.resolution_u=3
obj=bpy.data.objects.new('Waste lettering',curve);bpy.context.collection.objects.link(obj);obj.location=(0,-.224,.407);obj.rotation_euler=(math.pi/2,0,0)
bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.convert(target='MESH')
g.poly(kind,[obj.matrix_world@v.co for v in obj.data.vertices],[tuple(p.vertices) for p in obj.data.polygons],'Paper')
bpy.data.objects.remove(obj,do_unlink=True)
prototype=g.G.pop((g.ROOM,kind));bins=[[-14,-15.9,0],[-1,15.9,0],[22.9,12,0],[-22.5,-15.8,4.5],[-22.5,15.8,4.5]]
for x,y,z in bins:
    co=-1 if y<0 else 1
    vs=[(x+co*a,y+co*b,z+c) for a,b,c in prototype['v']]
    dest=g.group(kind);offset=len(dest['v']);dest['v']+=vs;dest['f'] += [tuple(offset+i for i in f) for f in prototype['f']]
    for key in ('m','uv','smooth'):dest[key]+=prototype[key]
    cylinder_hull(kind,(x,y,z),.242,.683)

records=[]
for (_,kind),data in g.G.items():
    name='SM_RHU_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    order=list(dict.fromkeys(data['m']))
    for role in order:mesh.materials.append(materials[role])
    uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
        face.material_index=order.index(role);face.use_smooth=smooth
        axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
        scale=ROLES[role].get('uv_meters_override',ROLES[role].get('uv_meters',1))
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=coords[j] if coords else (p[axes[0]]/scale,p[axes[1]]/scale)
            local_z=p.z-(4.5 if p.z>4 else 0)
            age.data[li].color=(.10+.48*math.exp(-max(0,local_z)/.10),0,0,1)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if kind not in ('PlanterSoil',):
        mod=obj.modifiers.new('Small edge radii','BEVEL');mod.width=.0009;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(38);mod.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=obj.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('Final triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    cols=[]
    for i,(vs,fs) in enumerate(g.C.get((g.ROOM,kind),[])):
        cm=bpy.data.meshes.new('UCX_'+name+'_%03d'%i);cm.from_pydata(vs,[],fs);cm.update();co=bpy.data.objects.new(cm.name,cm);bpy.context.collection.objects.link(co);co.select_set(True);cols.append(co)
    fbx=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    for co in cols:co.hide_set(True);co.hide_render=True
    records.append(dict(name=name,kind=kind,mesh=BASE+'/Meshes/'+name,position_m=[0,0,0],fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
        materials={'RHU_'+r:ROLES[r]['existing_ue_path'] for r in order},triangles=len(obj.data.polygons),collision=bool(cols),collision_hulls=len(cols),nanite=True,cast_shadow=True))
    print('UPPER_PROP_EXPORTED',kind,len(obj.data.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ReceptionUpperProps.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records,roles=ROLES,pots=CFG['pots'],bins=bins),indent=2),encoding='utf8')
