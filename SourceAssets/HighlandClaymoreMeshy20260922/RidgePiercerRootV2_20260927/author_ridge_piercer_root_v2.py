"""Shorten the ridge-piercer's wide root while keeping its actual V5 seat.

Author only this blade and its required menu artwork. The shared guards,
gem, grip, tip, stats and installed asset identity are unchanged.
"""
import json
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

P=Path(__file__).resolve().parent
BASE=P.parent
SOURCE=BASE/'JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend'
NAME='SM_Highland_Blade_RidgePiercer_V1'
OPTION='highland_ridge_piercer'
ICON='ue_highland_claymore_blade_1_'+OPTION+'.png'
for folder in ['Export','Icons']:(P/folder).mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
base=bpy.data.objects['SM_Highland_Blade_factory_JunctionV5']
obj=base.copy();obj.data=base.data.copy();obj.name=NAME;obj.data.name=NAME
scene.collection.objects.link(obj)
obj.hide_set(False);obj.hide_render=False
mesh=obj.data
normal_attr=mesh.attributes.get('SurfaceNormal') or mesh.attributes.new('SurfaceNormal','FLOAT_VECTOR','CORNER')
normal_attr.data.foreach_set('vector',np.array([n.vector[:] for n in mesh.corner_normals],dtype=np.float32).ravel())
bm=bmesh.new();bm.from_mesh(mesh)
# Keep the actual seat and a 1.5 mm support band, rather than the former
# full-width 10.5 cm root. Subdivision interpolates all corner attributes.
def seat_distance(co):return co.z-.058-.95*abs(co.x)
for limit,cuts in [(.012,2),(.008,1)]:
    edges=[e for e in bm.edges if e.calc_length()>limit and all(seat_distance(v.co)>.0015 for v in e.verts)]
    if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=cuts,use_grid_fill=True,smooth=0.)
faces=[f for f in bm.faces if all(seat_distance(v.co)>.0015 for v in f.verts)]
edges={e for f in faces for e in f.edges}
verts={v for f in faces for v in f.verts}
bmesh.ops.bisect_plane(bm,geom=list(verts)+list(edges)+faces,dist=1e-8,
    plane_co=(0,0,0),plane_no=(1,0,0),clear_inner=False,clear_outer=False)
bmesh.ops.triangulate(bm,faces=list(bm.faces))
bm.to_mesh(mesh);bm.free();mesh.update()
source_normals=np.array([v.vector[:] for v in mesh.attributes['SurfaceNormal'].data],dtype=np.float64)
source_normals/=np.maximum(np.linalg.norm(source_normals,axis=1)[:,None],1e-12)
points=np.array([v.co[:] for v in mesh.vertices],dtype=np.float64)
edges=np.array([e.vertices[:] for e in mesh.edges])
a,b=points[edges[:,0]],points[edges[:,1]]
tip=float(points[:,2].max())
stations=np.linspace(.088,tip-.000002,800)
left=[];right=[]
for z in stations:
    selected=(np.minimum(a[:,2],b[:,2])<=z)&(np.maximum(a[:,2],b[:,2])>z)
    aa,bb=a[selected],b[selected]
    xs=aa[:,0]+(bb[:,0]-aa[:,0])*(z-aa[:,2])/(bb[:,2]-aa[:,2])
    left.append(max(.000002,-float(xs.min())));right.append(max(.000002,float(xs.max())))

def ease(t):
    t=np.clip(t,0.,1.)
    return t*t*t*(t*(t*6.-15.)+10.)

x,y,z=points.T
source_width=np.where(x<0,np.interp(z,stations,left),np.interp(z,stations,right))
target_width=np.interp(z,[.058,.095,.11,.18,.70,.725,tip],[.0205,.020,.0195,.019,.0165,.0155,.000015])
# Follow the V seat instead of reserving a broad horizontal band. The outer
# shoulder finishes its narrowing around Z=11.5 cm instead of Z=18 cm.
distance=z-.058-.95*np.abs(x)
weight=ease((distance-.0015)/.025)
radial=np.clip(np.abs(x)/np.maximum(source_width,.000002),0,1)
shaped=points.copy()
shaped[:,0]=x*(1-weight)+np.sign(x)*radial*target_width*weight
# A supported diamond ridge has 12 mm at the spine, sloping continuously to
# a 0.5 mm cutting edge. Only the terminal 16 cm narrows in depth to the tip.
half=(.006-.00575*radial)*(1-.998*ease((z-.720)/(tip-.720)))
side=np.tanh(y/.00008)
shaped[:,1]=y*(1-weight)+side*half*weight
mesh.vertices.foreach_set('co',shaped.astype(np.float32).ravel());mesh.update()
mesh.calc_loop_triangles()
tris=np.array([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
tri_loops=np.array([t.loops[:] for t in mesh.loop_triangles],dtype=np.int32)
tri_points=shaped[tris]
cross=np.cross(tri_points[:,1]-tri_points[:,0],tri_points[:,2]-tri_points[:,0])
tri_normals=cross/np.maximum(np.linalg.norm(cross,axis=1)[:,None],1e-14)
centers=tri_points.mean(axis=1)
groups=(centers[:,0]>=0).astype(np.int32)+2*(centers[:,1]>=0).astype(np.int32)
acc=np.zeros((4,len(points),3),dtype=np.float64)
uv=mesh.uv_layers[0]
caps=np.array([all((uv.data[li].uv-Vector((.02,.02))).length<.000002 for li in tri.loops)
               for tri in mesh.loop_triangles])
for k in range(3):
    aa=tri_points[:,(k+1)%3]-tri_points[:,k]
    bb=tri_points[:,(k+2)%3]-tri_points[:,k]
    aa/=np.maximum(np.linalg.norm(aa,axis=1)[:,None],1e-14)
    bb/=np.maximum(np.linalg.norm(bb,axis=1)[:,None],1e-14)
    angles=np.arccos(np.clip(np.sum(aa*bb,axis=1),-1,1));angles[caps]=0.
    np.add.at(acc,(groups,tris[:,k]),tri_normals*angles[:,None])
acc/=np.maximum(np.linalg.norm(acc,axis=2)[:,:,None],1e-14)
normals=source_normals.copy()
for k in range(3):
    li=tri_loops[:,k];vi=tris[:,k]
    w=weight[vi,None]
    normals[li]=source_normals[li]*(1-w)+acc[groups,vi]*w
normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-14)
for face in mesh.polygons:face.use_smooth=True
mesh.update();mesh.normals_split_custom_set(normals.tolist())
mesh.attributes['SurfaceNormal'].data.foreach_set('vector',normals.astype(np.float32).ravel())
obj['option_id']=OPTION;obj['weapon']='ue_highland_claymore'
obj['interface']='V5 z=.058+.95*abs(x); exact seat plus 1.5mm support band'
obj['design']='RootV2: early narrow shoulder; straight diamond spine; native UV and PBR'

keep={NAME,'SM_Highland_Guard_factory_JunctionV5','SM_Highland_Grip_factory','SM_Highland_Pommel_factory'}
for other in list(scene.objects):
    if other.name not in keep:bpy.data.objects.remove(other,do_unlink=True)
    else:other.hide_set(False);other.hide_render=False
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
fbx=P/'Export'/(NAME+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_RidgePiercer_RootV2_Editable.blend'))

# Required menu artwork from the authored part, not an acceptance render.
for other in scene.objects:
    if other.type=='MESH':other.hide_render=other!=obj
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    gpu=[d for d in prefs.devices if d.type=='OPTIX']
    for device in prefs.devices:device.use=device in gpu
    if gpu:scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024
scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.world=bpy.data.worlds.new('Highland ridge piercer menu studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.2,.2,.2,1.);bg.inputs['Strength'].default_value=.65
camera=bpy.data.objects.new('Menu camera blade left',bpy.data.cameras.new('Menu camera blade left'))
scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.clip_start=.001
camera.rotation_euler=Matrix(((0,1,0),(0,0,-1),(-1,0,0))).to_euler()
bpy.context.view_layer.update()
corners=[Vector(v) for v in obj.bound_box];center=sum(corners,Vector())/8.
size=max(max(p.x for p in corners)-min(p.x for p in corners),max(p.z for p in corners)-min(p.z for p in corners))
camera.location=center+Vector((0,-1.5,0));camera.data.ortho_scale=size/.83
for name,offset,energy,diameter in [('Key',(.38,-.60,.35),95,.75),('Fill',(-.32,-.42,-.15),45,.65),('Rim',(.12,.28,.30),65,.5)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
    lamp.data.energy=energy;lamp.data.shape='DISK';lamp.data.size=diameter
    lamp.location=center+Vector(offset);lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'Icons'/ICON)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_RidgePiercer_RootV2_MenuIcon_Editable.blend'))
mesh.calc_loop_triangles()
spec={'weapon':'ue_highland_claymore','option':OPTION,'name':'棱脊穿甲刃','mesh':NAME,
      'source_blend':str(SOURCE),'source_object':'SM_Highland_Blade_factory_JunctionV5',
      'fbx':str(fbx),'ue_folder':'/Game/Weapons/HighlandClaymore20260922/RidgePiercer20260927',
      'icon':ICON,'units':'metres; +Z tip, X width, Y thickness',
      'revision':'RootV2_20260927',
      'design':{'body_width_cm':[3.8,3.3],'spine_thickness_mm':12,'unchanged_seat_support_mm':1.5,
                'seat_relative_transition_cm':2.5,'shoulder_end_cm_approx':11.5,
                'point_start_cm':72,'tip_cm':tip*100,'interface':'highland_hilt_v1 / JunctionV5'},
      'stats':{'combo_third_damage_mult':1.4,'combo_third_toughness_mult':1.4,'physical_armor_penetration':.1,'damage_mult':.9},
      'topology':{'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles)},
      'production_icon':{'size':[1024,1024],'direction':'tip left','background':'transparent','actual_part':NAME},
      'tested':False,'acceptance_rendered':False}
(P/'authoring.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
print('HIGHLAND_RIDGE_PIERCER_ROOT_V2_AUTHORED',flush=True)
