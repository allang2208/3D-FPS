"""Keep shared attachment bodies and UVs; author ASH rail contact shoes."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
I=json.loads((O/'authoring_inputs.json').read_text());sources=json.loads((O/'sources.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
for name in ('Meshes','Textures'): (O/name).mkdir(exist_ok=True)
F=Matrix(I['rail_frame']);R=Matrix(I['root_rest']);report={'parts':{},'material_reference':'ASH12/Surface20260919','rail_crown_z_m':{'upper':-.00295,'lower':-.140265}}
outcol=bpy.data.collections.new('ASH_attachment_sources');bpy.context.scene.collection.children.link(outcol)
def mat(name,color,metal=.7,rough=.45):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 return m
metal=mat('ASH_GripMetal',(.09,.095,.103));poly=mat('ASH_GripPolymer',(.025,.026,.028),.03,.62)
topmat=mat('ASH_OpticShoe',(.065,.068,.072),.65,.50)
def activate(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def box(name,center,size,m):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 mod=o.modifiers.new('Machined edges','BEVEL');mod.width=.00035;mod.segments=3;mod.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=mod.name)
 return o
def wedge(name,x0,x1,section,m):
 verts=[(x,y,z) for x in (x0,x1) for y,z in section];n=len(section)
 faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(m);ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 activate([ob]);be=ob.modifiers.new('Clamp edge bevel','BEVEL');be.width=.0002;be.segments=2;bpy.ops.object.modifier_apply(modifier=be.name)
 return ob
def screw(name,x,y,z,m):
 bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0021,depth=.0013,location=(x,y,z),rotation=(math.pi/2,0,0));o=bpy.context.object;o.name=name;o.data.materials.append(m)
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 be=o.modifiers.new('Fastener chamfer','BEVEL');be.width=.0002;be.segments=2;bpy.ops.object.modifier_apply(modifier=be.name)
 return o
def make_uv(ob,index):
 while len(ob.data.uv_layers)<=index:ob.data.uv_layers.new(name='ASH_SurfaceUV'+str(len(ob.data.uv_layers)))
 uv=ob.data.uv_layers[index]
 for f in ob.data.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=[k for k in range(3) if k!=axis]
  for li in f.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[a]/.04,p[b]/.04)
def new_part(key):
 if key=='angled':
  file=S/'ResonanceGrip20260913/MeshyIntegration/M4/ResonanceGrip_Surface_Editable.blend'
  with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=['SM_ResonanceGrip']
  ob=dst.objects[0];bpy.context.collection.objects.link(ob)
  ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
  ob.data.transform(Matrix(I['donors']['angled']['mount']).inverted())
  for i,m in enumerate(list(ob.data.materials)):ob.data.materials[i]=poly if 'Polymer' in m.name else metal
  return ob
 before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=sources[key]['fbx'],use_custom_normals=True)
 obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
 for ob in obs:
  ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
 activate(obs)
 if len(obs)>1:bpy.ops.object.join()
 return bpy.context.object
optic_x={'holographic':.11,'panoramic_red_dot':.10,'prism_scope_2x':.10,'lpvo_1_6x':.11,'lpvo_ring':.11}
feet={'holographic':(-.043,.025),'panoramic_red_dot':(-.026,.026),'prism_scope_2x':(-.024,.024),'lpvo_1_6x':(-.045,.019)}
for key in sources:
 ob=new_part(key);grip=key in I['donors'];add=[];bindings={}
 if grip:
  for i,m in enumerate(list(ob.data.materials)):
   if key=='prism' and i==0:continue
   if key!='angled':ob.data.materials[i]=metal
  # Crown touches the underside, without changing body proportions or handedness.
  lift=-max(v.co.z for v in ob.data.vertices)
  for v in ob.data.vertices:v.co.z+=lift
  x=.32 if key=='angled' else .30
  center_y=.000439
  # Open middle follows the measured 20.6 mm rail, with angled side shoulders.
  x0,x1=(-.029,.026) if key in ('angled','prism') else (-.016,.016)
  add.append(box('Underside contact pad',((x0+x1)/2,0,-.0017),(x1-x0,.0211,.0034),metal))
  for side in (-1,1):
   section=[(side*y,z) for y,z in [( .0105,-.004),(.0153,-.004),(.0153,.0015),(.0129,.0045),(.0105,.0015)]]
   if side<0:section.reverse()
   add.append(wedge('Rail shoulder jaw',x0,x1,section,metal))
   for px in (x0+.007,x1-.007):add.append(screw('Clamp screw',px,side*.0159,-.001,metal))
  M=F@Matrix.Translation((x,center_y,-.140265));H=Matrix(I['donors'][key]['hand_in_mount']);H.translation.z+=lift
  report['parts'][key]={'mount_rail_m':[x,center_y,-.140265],'hand_in_mount': [list(row) for row in H],'body_z_shift_m':lift,'mount_in_root':[list(row) for row in R.inverted()@M]}
 else:
  for i,m in enumerate(ob.data.materials):bindings[m.name]=sources[key]['slots'][i]['material']
  if key!='lpvo_ring':
   x0,x1=feet[key]
   add.append(box('Rail crown shoe',((x0+x1)*.5,0,-.001475),(x1-x0,.0209,.00295),topmat))
   for side in (-1,1):
    section=[(side*y,z) for y,z in [(.01055,-.0027),(.01055,-.0047),(.0120,-.0068),(.0144,-.0047),(.0144,-.0002),(.0122,.0002)]]
    if side<0:section.reverse()
    add.append(wedge('Rail dovetail jaw',x0+.001,x1-.001,section,topmat))
    for px in (x0+.006,x1-.006):add.append(screw('Optic rail screw',px,side*.0146,-.003,topmat))
  report['parts'][key]={'mount_rail_m':[optic_x[key],0,0],'original_optical_frame_retained':True}
 while len(ob.data.uv_layers)<4:ob.data.uv_layers.new(name='ASH_SurfaceUV'+str(len(ob.data.uv_layers)))
 for p in add:
  make_uv(p,0);make_uv(p,3)
  for i in range(4):p.data.uv_layers[i].name=ob.data.uv_layers[i].name
 activate([*add,ob])
 if add:bpy.ops.object.join()
 if grip:make_uv(ob,3)
 if key in ('vertical','canted'):make_uv(ob,0)
 ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
 ob.name='SM_ASH12_'+key
 # Do not recalculate the shared body's imported normals or its optical UVs.
 for c in list(ob.users_collection):c.objects.unlink(ob)
 outcol.objects.link(ob)
 activate([ob]);path=O/'Meshes'/(ob.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 report['parts'][key].update({'file':str(path),'name':ob.name,'bindings':bindings,'slots':[m.name for m in ob.data.materials],'source':sources[key]['source'],'coat_uv':3})
 ob.hide_set(True);ob.hide_render=True

# Fine coating maps: 4 cm tile, with restrained roughness variation and micro-normal.
N=1024;rng=np.random.default_rng(91912);noise=rng.random((N,N)).astype(np.float32)
height=(noise-.5)*.0025;dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.5;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.5
norm=np.dstack((-dx,dy,np.ones_like(dx)));norm/=np.linalg.norm(norm,axis=2,keepdims=True)
maps={'NormalDX':np.dstack((norm*.5+.5,np.ones_like(dx))), 'ORM':np.dstack((np.ones_like(dx),.45+(noise-.5)*.025,np.full_like(dx,.70),np.ones_like(dx)))}
for key,rgba in maps.items():
 im=bpy.data.images.new('T_ASH12_AttachmentCoat_'+key,width=N,height=N,alpha=True);im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(rgba.astype(np.float32).ravel());im.filepath_raw=str(O/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save()
report['coat']={'uv':3,'tile_metres':.04,'base_color_linear':[.09,.095,.103],'roughness':.45,'metallic':.7}
(O/'models.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_Attachment_Models_Editable.blend'))
print('ASH_ATTACHMENT_MODELS_AUTHORED',flush=True)
