"""Author the Cloven guard from the actual Highland mounting geometry.

No acceptance renders. The single render is the shipped menu texture.
"""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
NAME='SM_Highland_Guard_Cloven'
ICON='ue_highland_claymore_guard_highland_cloven_guard.png'
for folder in ['Export','Icons']:(P/folder).mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'Integration/HighlandClaymore_Modular_Editable.blend'))
scene=bpy.context.scene
base=bpy.data.objects['SM_Highland_Guard_factory']
obj=base.copy();obj.data=base.data.copy();obj.name=NAME;obj.data.name=NAME
scene.collection.objects.link(obj);obj.hide_set(False);obj.hide_render=False
mesh=obj.data
attr=mesh.attributes.get('SurfaceNormal') or mesh.attributes.new('SurfaceNormal','FLOAT_VECTOR','CORNER')
attr.data.foreach_set('vector',np.array([tuple(n.vector) for n in mesh.corner_normals],dtype=np.float32).ravel())
bm=bmesh.new();bm.from_mesh(mesh)
edges=[e for e in bm.edges if e.calc_length()>.008 and all(abs(v.co.x)>.055 for v in e.verts)]
if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=2,use_grid_fill=True,smooth=0.)
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
points=np.array([tuple(v.co) for v in mesh.vertices],dtype=np.float64)
normals=np.array([tuple(v.vector) for v in mesh.attributes['SurfaceNormal'].data],dtype=np.float64)
sections=json.loads((P/'source_guard.json').read_text())['sections']
xs=np.array([r['x']+.005 for r in sections]);zs=np.array([sum(r['z'])/2 for r in sections])

def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def center(t):
    return .055+.234*t-.102*t**3, .008+.027*t+.105*t*t

def shape(p):
    q=p.copy();x,y,z=p.T;r=np.abs(x)
    t=np.clip((r-.055)/.123,0,1);w=smooth((r-.055)/.035)
    cx,cz=center(t);dx=.234-.306*t*t;dz=.027+.21*t
    length=np.sqrt(dx*dx+dz*dz);nx=-dz/length;nz=dx/length
    local=z-np.interp(r,xs,zs)
    # Substantial shoulders flow into an inward-hooked tip, with a shallow
    # receiving notch on the inner edge; the original middle 11 cm stays exact.
    thickness=1+.50*np.sin(np.pi*t)
    radial=local*thickness-.0035*np.exp(-((t-.25)/.085)**2)*smooth(local/.012)
    target_x=np.sign(x)*(cx+nx*radial);target_z=cz+nz*radial
    q[:,0]=x+(target_x-x)*w
    q[:,2]=z+(target_z-z)*w
    q[:,1]=y*(1+.32*w*(1-.5*t))
    return q

eps=1e-6;jac=np.empty((len(points),3,3))
for axis in range(3):
    d=np.zeros(3);d[axis]=eps;jac[:,:,axis]=(shape(points+d)-shape(points-d))/(2*eps)
indices=np.array([l.vertex_index for l in mesh.loops])
normals=np.einsum('nij,nj->ni',np.linalg.inv(jac).transpose(0,2,1)[indices],normals)
normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-10)
mesh.vertices.foreach_set('co',shape(points).astype(np.float32).ravel())
for face in mesh.polygons:face.use_smooth=True
mesh.update();mesh.normals_split_custom_set(normals.tolist())
mesh.attributes['SurfaceNormal'].data.foreach_set('vector',normals.astype(np.float32).ravel())

def material(name,color,metal,rough,glow=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    p.inputs['Emission Color'].default_value=(1,.018,.006,1);p.inputs['Emission Strength'].default_value=glow
    return m

recess=material('M_Cloven_Recess',(.018,.022,.025),.88,.42)
inlay=material('M_Cloven_Inlay',(.18,.006,.003),.48,.29,.07)
created=[obj]
bpy.context.view_layer.update()

def ribbon(name,side,front,t0,t1,width,mat,offset):
    verts=[];faces=[];uv=[];steps=16
    for i in range(steps+1):
        u=i/steps;t=t0+(t1-t0)*u
        cx,cz=center(t);dx=.234-.306*t*t;dz=.027+.21*t
        normal=Vector((-dz,0,dx)).normalized()
        half=width*(.18+.82*math.sin(math.pi*u)**.45)
        for sign in [-1,1]:
            x=side*(cx+normal.x*half*sign);z=cz+normal.z*half*sign
            ok,hit,n,idx=obj.ray_cast(Vector((x,front*.5,z)),Vector((0,-front,0)))
            if not ok:raise RuntimeError('Inlay placement left the authored guard: '+name)
            verts.append((x,hit.y+front*offset,z));uv.append((u,(sign+1)/2))
    for i in range(steps):
        a=i*2;quad=(a,a+1,a+3,a+2)
        faces.append(quad if side*front>0 else tuple(reversed(quad)))
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.materials.append(mat);m.update()
    layer=m.uv_layers.new(name='UVMap');color=m.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for face in m.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            vi=m.loops[li].vertex_index;layer.data[li].uv=uv[vi]
            color.data[li].color=(float((abs(verts[vi][0])-.08)/.12),0,0,1)
    ob=bpy.data.objects.new(name,m);scene.collection.objects.link(ob);created.append(ob)

for side in [-1,1]:
    for front in [-1,1]:
        for index,(a,b) in enumerate([(.29,.38),(.46,.55),(.63,.72)]):
            tag=f'{side}_{front}_{index}'
            ribbon('Dark cut '+tag,side,front,a-.01,b+.01,.0025,recess,.00010)
            ribbon('Crimson inlay '+tag,side,front,a,b,.00135,inlay,.00024)

# Join the new inserts into the guard module, leaving the other modules intact.
bpy.ops.object.select_all(action='DESELECT')
for ob in created:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
obj.name=NAME
tri=obj.modifiers.new('Game triangles','TRIANGULATE');tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
obj['interface']='highland_hilt_v1: original central |X| <= 55 mm, V blade seat and grip collar'
obj['source']='Selected Meshy Highland guard, original UV and corner normals retained'
obj['effect']='Parry token: red inlays light center to tips, fade after consumption/expiry'
for other in scene.objects:
    if other.type=='MESH':
        visible=other==obj or other.name in ['SM_Highland_Blade_factory','SM_Highland_Grip_factory','SM_Highland_Pommel_factory']
        other.hide_render=not visible;other.hide_set(not visible)
bpy.context.view_layer.objects.active=obj
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/f'{NAME}.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_ClovenGuard_Editable.blend'))
spec={'weapon':'ue_highland_claymore','slot':'guard','option':'highland_cloven_guard','mesh':NAME,
      'ue_folder':'/Game/Weapons/HighlandClaymore20260922/ClovenGuard','icon':ICON,
      'source':str(P.parent/'Integration/HighlandClaymore_Modular_Editable.blend'),
      'source_object':base.name,'materials':[m.name for m in obj.data.materials],
      'stats':{'block_stamina_mult':.9,'cloven_seconds':4,'cloven_physical_mult':1.25,'cloven_toughness_mult':1.4},
      'mount':{'location_cm':[0,0,0],'interface':'highland_hilt_v1'},
      'icon_orientation':'blade +Z left, front -Y, no mirroring; actual guard only',
      'production_only':True,'tested':False}
(P/'production.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')

# Deliverable icon: same camera/lighting convention as the existing Highland set.
for other in scene.objects:
    if other.type=='MESH':other.hide_render=other!=obj
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='OPTIX']
    for d in prefs.devices:d.use=d in devices
    if devices:scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.world=bpy.data.worlds.new('Cloven neutral menu studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.2,.2,.2,1);bg.inputs['Strength'].default_value=.65
camera=bpy.data.objects.new('Menu camera blade left',bpy.data.cameras.new('Menu camera blade left'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.clip_start=.001;camera.rotation_euler=Matrix(((0,1,0),(0,0,-1),(-1,0,0))).to_euler()
points=[Vector(v) for v in obj.bound_box];middle=sum(points,Vector())/8
size=max(max(p.x for p in points)-min(p.x for p in points),max(p.z for p in points)-min(p.z for p in points))
camera.location=middle+Vector((0,-1.5,0));camera.data.ortho_scale=size/.83
for name,offset,energy,size in [('Key',(.38,-.60,.35),95,.75),('Fill',(-.32,-.42,-.15),45,.65),('Rim',(.12,.28,.30),65,.5)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
    lamp.data.energy=energy;lamp.data.shape='DISK';lamp.data.size=size;lamp.location=middle+Vector(offset)
    lamp.rotation_euler=(middle-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'Icons'/ICON)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_ClovenGuard_MenuIcon_Editable.blend'))
bpy.ops.render.render(write_still=True)
print('CLOVEN_GUARD_AUTHORED '+str(P),flush=True)
