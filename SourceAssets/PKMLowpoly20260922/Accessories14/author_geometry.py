"""Fit shared accessory geometry to PKM, retaining source UVs/masks/normals."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent;S=R.parent;E=O/'Exports';E.mkdir(exist_ok=True)
src=json.loads((S/'A762Meshy20260920/Accessories05/sources.json').read_text())
src['meshes'].pop('drum',None)
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
bpy.context.preferences.filepaths.save_version=0
report={'meshes':{},'factory_slots':{},'source':'Feed13','game_tested':False}
grips=['vertical','tactical_vertical','canted','prism','angled']
stocks=['skeleton','core_stock','qr_performance','tactical_telescopic']
optics=['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']
grip_xf=Matrix.Translation(fit@Vector((0,-.120,-.005))-Vector((.0008,-.300,.030)))

def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def export(obs,name):
 select(obs)
 bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
def cube(name,p,size,mat,bevel=.0006):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=name;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
 mod=o.modifiers.new('MachinedEdge','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=o.modifiers.new('AreaNormals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4);o['pkm_interface']=True
 return o
def coat_uv(o):
 while len(o.data.uv_layers)<3:o.data.uv_layers.new(name='PKM_CoatingUV' if len(o.data.uv_layers)==2 else 'SourceUV')
 uv=o.data.uv_layers[2]
 for face in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
  for loop in face.loop_indices:
   p=o.data.vertices[o.data.loops[loop].vertex_index].co
   uv.data[loop].uv=(p[axes[0]]/.05,p[axes[1]]/.05)
 if o.get('pkm_interface'):
  for a,b in zip(o.data.uv_layers[0].data,uv.data):a.uv=b.uv
 o.data.uv_layers.active_index=0

# Freeze the existing right-hand contact frame, used to fit replacement grips.
bpy.ops.wm.open_mainfile(filepath=str(R/'Feed13/PKM_FiringFeed_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];r.animation_data.action=bpy.data.actions['PKM_Game_idle_Wrist12'];r.animation_data.action_slot=r.animation_data.action.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
right_pkm=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_r'].matrix
donor=Path(src['animations']['vertical/idle']['source'][0]).with_suffix('.blend')
bpy.ops.wm.open_mainfile(filepath=str(donor));d=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
right_donor=d.pose.bones['WPN_root'].matrix.inverted()@d.pose.bones['hand_r'].matrix
rear_xf=right_pkm@right_donor.inverted()
report['grip_transform']=list(map(list,grip_xf));report['rear_grip_transform']=list(map(list,rear_xf))

for key,info in src['meshes'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=info['source'][0]);obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];bindings={}
 for ob in obs:
  ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
  for i,m in enumerate(ob.data.materials):
   m.name=f'PKM14_{key}_{i}';bindings[m.name]={'path':info['materials'][min(i,len(info['materials'])-1)]['path'],'source_slot':info['materials'][min(i,len(info['materials'])-1)]['slot'],'index':i}
 xf=Matrix.Identity(4)
 if key in grips:xf=grip_xf
 elif key.endswith('reargrip'):xf=rear_xf
 elif key in stocks:xf=fit@Matrix.Translation((0,.305,.038))@Matrix.Rotation(math.pi/2,4,'Z')
 elif key in ['laser','flashlight']:
  # The donor's right-side rail is moved ahead of the feed port and support hand.
  xf=Matrix.Translation(fit@Vector((.020,-.235,.036))-Vector((.019,-.310,.057)))
 for o in obs:o.data.transform(xf)
 mat=bpy.data.materials.new('PKM14_Interface');mat.use_nodes=True
 bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.025,.029,.033,1);bs.inputs['Metallic'].default_value=.72;bs.inputs['Roughness'].default_value=.35
 bindings[mat.name]={'path':'PKM_INTERFACE','source_slot':'MetalInterface','index':-1}
 if key in grips:
  obs.append(cube('PKM_UnderRailFoot',fit@Vector((0,-.120,-.003)),(.026,.085,.007),mat))
 if key in stocks:
  obs.append(cube('PKM_StockAdapter',fit@Vector((0,.303,.029)),(.029,.012,.053),mat,.0012))
 if key.endswith('reargrip'):
  obs.append(cube('PKM_GripTang',fit@Vector((0,.251,-.009)),(.027,.042,.012),mat,.001))
 if key in ['laser','flashlight']:
  obs.append(cube('PKM_SideRailClamp',fit@Vector((.018,-.235,.026)),(.009,.069,.025),mat))
 for o in obs:coat_uv(o)
 name='SM_PKM_'+key;export(obs,name)
 sockets={}
 for n,p in info.get('sockets',{}).items():
  v=xf@Vector((p[0]/100,-p[1]/100,p[2]/100));sockets[n]=[v.x*100,-v.y*100,v.z*100]
 report['meshes'][key]={'name':name,'materials':bindings,'sockets':sockets,'source':info['asset']}
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
 print('PKM14_PART_EXPORTED',key,flush=True)

# Private cover rail in cover-bone coordinates; follows the existing reload.
bpy.ops.wm.read_factory_settings(use_empty=True)
mat=bpy.data.materials.new('PKM14_Interface');mat.use_nodes=True
cover=Vector((0,-.021,.070))
obs=[]
for y in [.012,.127]:obs.append(cube('PKM_CoverRailFoot',Vector((0,y,.102))-cover,(.026,.018,.018),mat))
obs.append(cube('PKM_CoverRailSpine',Vector((0,.070,.115))-cover,(.018,.173,.008),mat))
for i in range(18):obs.append(cube('PKM_CoverRailTooth',Vector((0,-.009+i*.009,.121))-cover,(.021,.0055,.005),mat,.00035))
for o in obs:coat_uv(o)
export(obs,'SM_PKM_optic_rail');bpy.ops.wm.save_as_mainfile(filepath=str(O/'SM_PKM_optic_rail.blend'))
report['meshes']['optic_rail']={'name':'SM_PKM_optic_rail','source':'authored PKM cover mounting interface','sockets':{},'materials':{'PKM14_Interface':{'path':'PKM_INTERFACE','source_slot':'MetalInterface','index':-1}}}

# Split replacement identity into material sections without changing geometry,
# weights, rest pose, old/new belt sections or the calibrated hands.
bpy.ops.wm.open_mainfile(filepath=str(R/'Feed13/PKM_FiringFeed_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig']
groups={'FactoryStock':[66,130,131,132,133,135],'FactoryRearGrip':[45,46],'FactoryMuzzle':[93]}
for group,ids in groups.items():
 for i in ids:
  ob=bpy.data.objects[f'PKM_Part_{i:03}']
  for j,m in enumerate(ob.data.materials):
   name=m.name+'__'+group
   copy=bpy.data.materials.get(name) or m.copy();copy.name=name;ob.data.materials[j]=copy
   report['factory_slots'][name]=m.name
sys.path.insert(0,str(R/'Belt08'));from mesh_export import export_mesh
export_mesh(r,E/'SK_PKM_Manny_Modular.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_Modular_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PKM14_GEOMETRY_COMPLETE',flush=True)
