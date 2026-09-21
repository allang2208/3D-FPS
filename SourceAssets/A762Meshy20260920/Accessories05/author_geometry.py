"""Fit common parts to A762's authored interfaces; keep accepted main surfaces."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;D=O/'Exports';D.mkdir(exist_ok=True)
sources=json.loads((O/'sources.json').read_text());frames=json.loads((O/'authoring_frames.json').read_text())
report={'meshes':{},'fixed_sights':[],'tested':False}
bpy.context.preferences.filepaths.save_version=0
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def export(obs,name):
 select(obs);bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
def cube(name,loc,size,mat,bevel=.0005):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 ob.data.materials.append(mat)
 if bevel:
  m=ob.modifiers.new('MachinedEdges','BEVEL');m.width=bevel;m.segments=3
  bpy.ops.object.modifier_apply(modifier=m.name)
  m=ob.modifiers.new('FaceNormals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)
 # Apply translation: all fitted accessories share one explicit local frame.
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
 return ob
def material(name):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.021,.028,.039,1);p.inputs['Metallic'].default_value=.86;p.inputs['Roughness'].default_value=.33
 return m
# Donor parts preserve original UVs, vertex masks and structural normals.
for key,info in sources['meshes'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=info['source'][0]);obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 materials={};source_slots=info['materials']
 for ob in obs:
  ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
  for i,mat in enumerate(ob.data.materials):
   # Donor import labels differ from renamed UE slots; retain their actual order.
   name='A762_'+key+'_'+str(i);mat.name=name
   materials[name]=source_slots[min(i,len(source_slots)-1)]['path']
 xf=Matrix.Identity(4)
 if key in ['vertical','prism','canted','angled','tactical_vertical','phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
  xf=Matrix.Translation((-.00024,0,0))
 elif key in ['skeleton','core_stock','qr_performance','tactical_telescopic']:
  # Stock donor +X points rearward; actual A762 receiver ends at Y=.118.
  xf=Matrix.Translation((.00056,.118,.060))@Matrix.Rotation(math.pi/2,4,'Z')
 elif key in ['laser','flashlight']:
  # Same forward station, widened to seat on A762's 46 mm handguard.
  xf=Matrix.Translation((.006,0,.005))
 for ob in obs:ob.data.transform(xf)
 if key in ['vertical','prism','canted','angled','tactical_vertical']:
  mat=material('A762_'+key+'_Interface');materials[mat.name]='A762_STEEL'
  # Small backed under-rail saddle overlaps the closed handguard, no floating rail.
  obs.append(cube('A762_UnderRailSaddle',(.00056,-.300,.0304),(.021,.067,.0038),mat))
 if key.endswith('reargrip'):
  mat=material('A762_'+key+'_Interface');materials[mat.name]='A762_STEEL'
  obs.append(cube('A762_GripUpperTang',(.00056,.021,.012),(.026,.037,.012),mat,.0012))
 if key in ['skeleton','core_stock','qr_performance','tactical_telescopic']:
  mat=material('A762_'+key+'_Interface');materials[mat.name]='A762_STEEL'
  obs.append(cube('A762_StockReceiverAdapter',(.00056,.116,.060),(.026,.010,.047),mat,.002))
 if key in ['laser','flashlight']:
  mat=material('A762_'+key+'_Interface');materials[mat.name]='A762_STEEL'
  obs.append(cube('A762_SideRailSaddle',(.025,-.310,.062),(.007,.071,.018),mat))
 if key=='drum':
  # Drum is already in this shared magazine bone's own frame. Keep contact frame.
  # Its complete closed feed tower is retained; upper neck is reshaped to A762 well.
  for ob in obs:
   for v in ob.data.vertices:
    t=max(0,min(1,(v.co.z-.045)/.030));t=t*t*(3-2*t)
    v.co.y=(1-t)*v.co.y+t*(.0448+(v.co.y-.0197)*.87)
    v.co.x=(1-t)*v.co.x+t*(.00048+(v.co.x-.00076)*.90)
 name='SM_A762_'+key
 export(obs,name)
 sockets={}
 for k,p in info.get('sockets',{}).items():
  v=xf@Vector((p[0]/100,-p[1]/100,p[2]/100));sockets[k]=[v.x*100,-v.y*100,v.z*100]
 report['meshes'][key]={'name':name,'materials':materials,'sockets':sockets,'source':info['asset']}
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
 print('A762_PART_AUTHORED',key,flush=True)

# Factory-derived extended magazine: keep its entire mouth and gripping region;
# extend the lower curved path and carry every original panel/rib with it.
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Refinement04/A762_StockJoint_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hands=bpy.data.objects['SK_Manny_Arms_Export']
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy();rest={b.name:b.matrix_local.copy() for b in r.data.bones};pose={b.name:b.matrix.copy() for b in r.pose.bones}
body=[];heads=[]
for col in ['A762_REFINED_GEOMETRY','A762_RECONSTRUCTED_02','A762_CLOSED_SURFACES_03','A762_STOCK_JOINT_04']:
 for ob in bpy.data.collections[col].objects:
  if ob.type!='MESH':continue
  (heads if ob.get('independent_folding_head') or ob.name.startswith('SM_A762_') else body).append(ob)
parts=[];materials={}
for ob in body:
 if 'WPN_SOCKET_Magazine' not in ob.vertex_groups:continue
 copy=ob.copy();copy.data=ob.data.copy();s.collection.objects.link(copy);copy.parent=None;copy.matrix_world=Matrix.Identity(4);copy.modifiers.clear()
 xf=root.inverted()@pose['WPN_SOCKET_Magazine']@rest['WPN_SOCKET_Magazine'].inverted();copy.data.transform(xf)
 for v in copy.data.vertices:
  q=max(0,min(1,(-v.co.z-.023)/.113));smooth=q*q*(3-2*q)
  v.co.z-=.044*smooth;v.co.y-=.023*smooth
 # Mesh-local magazine frame, without the unreliable reversed bind-chain product.
 copy.data.transform(pose['WPN_SOCKET_Magazine'].inverted()@root)
 for mat in copy.data.materials:materials[mat.name]='EXISTING_A762'
 parts.append(copy)
export(parts,'SM_A762_ext_mag');report['meshes']['ext_mag']={'name':'SM_A762_ext_mag','materials':materials,'source':'Refinement04 original magazine, lower curved extension','sockets':{}}
for ob in parts:bpy.data.objects.remove(ob,do_unlink=True)

# Separate the fixed sight bases from the moving heads. The old assembly's
# long shoe used to rotate up while its leaf went down, resembling a second sight.
for head in heads:
 key='RearSight' if 'Rear' in head.name else 'FrontSight';head.data=head.data.copy()
 head.data.transform(root.inverted()@pose['WPN_root']@rest['WPN_root'].inverted());head.parent=None;head.matrix_world=Matrix.Identity(4);head.modifiers.clear()
 hinge=Vector((.00056,.05576,.1065) if key=='RearSight' else (.00056,-.49144,.0935))
 bm=bmesh.new();bm.from_mesh(head.data)
 # Connected islands permit a clean separation of the rear's fixed shoe.
 seen=set();fixed_faces=set()
 if key=='RearSight':
  for v in bm.verts:
   if v in seen:continue
   group=set([v]);stack=[v];seen.add(v)
   while stack:
    w=stack.pop()
    for e in w.link_edges:
     q=e.other_vert(w)
     if q not in seen:seen.add(q);group.add(q);stack.append(q)
   zmax=max(v.co.z for v in group);yc=sum(v.co.y for v in group)/len(group)
   if zmax<.1002 or (zmax<.1057 and yc<.049):
    fixed_faces.update(f for v in group for f in v.link_faces)
 else:
  # Split the slotted upright at a real hinge above the gas tube, capping both halves.
  result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.0000001,plane_co=hinge,plane_no=Vector((0,0,1)),clear_inner=False,clear_outer=False)
  fixed_faces={f for f in bm.faces if f.calc_center_median().z<hinge.z-.0000001}
 fixed=bpy.data.meshes.new('A762_'+key+'_FixedBase');moving=bpy.data.meshes.new('A762_'+key+'_Head')
 def subset(name,faces):
  verts=list({v for f in faces for v in f.verts});idx={v:i for i,v in enumerate(verts)}
  me=bpy.data.meshes.new(name);me.from_pydata([tuple(v.co) for v in verts],[],[[idx[v] for v in f.verts] for f in faces]);me.update()
  for m in head.data.materials:me.materials.append(m)
  for p,f in zip(me.polygons,faces):p.material_index=f.material_index;p.use_smooth=True
  obj=bpy.data.objects.new(name,me);s.collection.objects.link(obj)
  b=bmesh.new();b.from_mesh(me)
  # Cap only cut boundaries; the original hood/aperture are solid annular walls.
  edges=[e for e in b.edges if e.is_boundary]
  if edges:bmesh.ops.holes_fill(b,edges=edges,sides=0)
  bmesh.ops.recalc_face_normals(b,faces=list(b.faces));b.to_mesh(me);b.free()
  select([obj]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
  mod=obj.modifiers.new('AreaWeightedNormals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
  return obj
 base=subset('A762_'+key+'_FixedBase',list(fixed_faces));move=subset('SM_A762_'+key,list(set(bm.faces)-fixed_faces));bm.free()
 move.data.transform(Matrix.Translation(-hinge));export([move],'SM_A762_'+key)
 report['meshes'][key]={'name':'SM_A762_'+key,'materials':{m.name:'EXISTING_A762' for m in move.data.materials},'sockets':{},'hinge_ue':[hinge.x,-hinge.y,hinge.z]}
 base.data.transform(rest['WPN_root']@pose['WPN_root'].inverted()@root)
 base.parent=r;base.vertex_groups.new(name='WPN_root').add(list(range(len(base.data.vertices))),1,'REPLACE');mod=base.modifiers.new('WeaponRig','ARMATURE');mod.object=r
 body.append(base);report['fixed_sights'].append(base.name)
 move.hide_set(True);move.hide_render=True;head.hide_set(True);head.hide_render=True
r.data.pose_position='REST';bpy.context.view_layer.update();select(body+[hands,r])
bpy.ops.export_scene.fbx(filepath=str(D/'SK_A762_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE';s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_AccessoryReady_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('A762_ACCESSORY_GEOMETRY_COMPLETE',flush=True)
