import bpy,numpy as np,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
before='--before' in sys.argv
ids_only='--ids' in sys.argv
between='--between' in sys.argv
source=ROOT.parent/'V03/Authoring/FacelessReceptionist_V03.blend' if before else ROOT/'Authoring/FacelessReceptionist_V04.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;rig=bpy.data.objects['root'];body=bpy.data.objects['Receptionist_CompleteBody']
objects=[o for o in s.objects if o.type=='MESH' and not o.hide_render]
data=np.load(ROOT/'MotionSources/deform_attack.npz');names=list(data['names']);allmats=data['matrices']
curves=json.loads((ROOT/'corrective_curves.json').read_text()) if not before else {}
panels=[(0,0),(20,0),(40,0),(60,0),(80,0),(40,-math.pi/2)]
if between:panels=[(17,0),(37,0),(57,0),(63,0),(78,0),(57,-math.pi/2)]
snapshots=[]
packed={}
for o in objects:
 groups={}
 for v in o.data.vertices:
  for g in v.groups:
   name=o.vertex_groups[g.group].name
   if name not in names:continue
   ids,ws=groups.setdefault(names.index(name),([],[]));ids.append(v.index);ws.append(g.weight)
 packed[o.name]={bi:(np.array(ids),np.array(ws)) for bi,(ids,ws) in groups.items()}
for frame,angle in panels:
 mats=allmats[min(frame,len(allmats)-1)];copies=[]
 for o in objects:
  mesh=o.data.copy();p=np.array([v.co[:] for v in mesh.vertices],dtype=np.float64)
  if ids_only:
   color=(0,1,.1) if 'Body' in o.name else (1,.04,.02) if 'Shirt' in o.name else (.02,.15,1) if 'Yoke' in o.name else (.25,.25,.25)
   mat=bpy.data.materials.new('ID_'+o.name);mat.use_nodes=True;mat.node_tree.nodes.clear();em=mat.node_tree.nodes.new('ShaderNodeEmission');em.inputs[0].default_value=(*color,1);outnode=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(em.outputs[0],outnode.inputs['Surface']);mesh.materials.clear();mesh.materials.append(mat)
   for poly in mesh.polygons:poly.material_index=0
  if not before and o.data.shape_keys:
   for k in o.data.shape_keys.key_blocks:
    weight=curves['attack'].get(k.name,[0]*len(allmats))[frame]
    if weight:p+=(np.array([v.co[:] for v in k.data])-np.array([v.co[:] for v in o.data.vertices]))*weight
  out=np.zeros_like(p)
  for bi,(ids,w) in packed[o.name].items():
   m=mats[bi]
   out[ids]+=((p[ids]@m[:3,:3].T)+m[:3,3])*w[:,None]
  if mesh.shape_keys:
   temporary=bpy.data.objects.new('BakedPoseTemporary',mesh)
   temporary.shape_key_clear();bpy.data.objects.remove(temporary,do_unlink=True)
  mesh.vertices.foreach_set('co',out.ravel());mesh.update()
  if mesh.has_custom_normals:mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops))
  snapshots.append((frame,angle,o.name,mesh))
for o in list(s.objects):bpy.data.objects.remove(o,do_unlink=True)
for idx,(frame,angle) in enumerate(panels):
 group=[r for r in snapshots if r[0]==frame and r[1]==angle]
 trans=Matrix.Translation(((idx%3-1)*1.65,0,-(idx//3)*2.15))@Matrix.Rotation(angle,4,'Z')
 for _,_,name,mesh in group:
  o=bpy.data.objects.new(name+'_'+str(idx),mesh);s.collection.objects.link(o);o.matrix_world=trans
 def mat(name,color):
  m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
  b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);return m
 cu=bpy.data.curves.new('Label','FONT');cu.body=('V03' if before else 'V04')+' ATTACK '+str(frame)+'/100';cu.align_x='CENTER';cu.size=.065
 ob=bpy.data.objects.new('Label',cu);s.collection.objects.link(ob);ob.location=((idx%3-1)*1.65,-.5,1.93-(idx//3)*2.15);ob.rotation_euler=(math.pi/2,0,0)
 cu.materials.append(mat('Label',(.08,.08,.08)))
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.36,.38,.41,1);bg.inputs[1].default_value=.6
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for loc,power,size in [((-3,-5,5),1000,5),((4,-2,3),650,4),((0,3,4),800,4)]:
 ld=bpy.data.lights.new('Softbox','AREA');ld.energy=power;ld.shape='DISK';ld.size=size;o=bpy.data.objects.new('Softbox',ld);s.collection.objects.link(o);o.location=loc;aim(o,(0,0,0))
ca=bpy.data.cameras.new('Camera');o=bpy.data.objects.new('Camera',ca);s.collection.objects.link(o);o.location=(0,-12,-.1);aim(o,(0,0,-.1));ca.type='ORTHO';ca.ortho_scale=5.25;s.camera=o
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=2400;s.render.resolution_y=1950;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
s.render.image_settings.file_format='PNG';s.render.filepath=str(ROOT/'Preview'/('V04_attack_interpolation.png' if between else 'V04_layer_diagnosis.png' if ids_only else 'V03_attack_diagnosis.png' if before else 'V04_attack_corrected.png'))
bpy.ops.render.render(write_still=True)
print('POSE_RENDER_SAVED',s.render.filepath)
