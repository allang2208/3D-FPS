import bpy,bmesh,json,math,runpy
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sources=json.loads((O/'sources.json').read_text());raw={}
for key,spec in sources.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=spec['source'])
 ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');raw[key]={'verts':[tuple(ob.matrix_world@v.co) for v in ob.data.vertices],'faces':[list(p.vertices) for p in ob.data.polygons],'indices':[p.material_index for p in ob.data.polygons],'uv':[tuple(x.uv) for x in ob.data.uv_layers.active.data],'materials':[m.copy() for m in ob.data.materials]}
 # Material data are reconstructed after each file load; source slot ordering is retained.
 raw[key]['materials']=[m.name for m in ob.data.materials]
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/AKMSoviet20260911/AKM_Soviet_Editable.blend')
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.copy();mag=r.pose.bones['WPN_SOCKET_Magazine'].matrix.copy()
gun=bpy.data.objects['AKM_Soviet_Native'];mat=gun.data.materials[0].copy();mat.name='M_AKM_Soviet_Magazine';gun.data.materials.append(mat);vg=gun.vertex_groups['WPN_SOCKET_Magazine'].index
ids={v.index for v in gun.data.vertices if any(g.group==vg and g.weight>.99 for g in v.groups)}
for p in gun.data.polygons:
 if p.vertices[0] in ids:p.material_index=1
bpy.ops.object.select_all(action='DESELECT')
for ob in [r,gun,bpy.data.objects['SK_Manny_Arms_Export']]:ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'SK_AKM_MannyNative.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
fits={};transforms={};turn=Matrix.Rotation(-math.pi/2,4,'Z')
for key in ['prism','angled']:
 fit=json.loads((O/f'Reference/{key}_fit.json').read_text());old=Matrix(fit['grip_in_root']);new=old.copy()
 new.translation=Vector((.0008,-.30,.0186)) if key=='prism' else old.translation+Vector((-.0105,-.01,.017))
 fit['hand_in_root']=[list(x) for x in new@old.inverted()@Matrix(fit['hand_in_root'])];fit['grip_in_root']=[list(x) for x in new];fits[key]=fit
 transforms[key]=new if key=='prism' else new@Matrix(fit['grip_matrix']).inverted()
transforms['optic']=Matrix.Translation((.0008,-.055,.113))@turn
for key in ['suppressor','brake','titanium_brake']:transforms[key]=Matrix.Translation((.0008,-.577,.0508883))@Matrix.Rotation(math.pi,4,'Z')
transforms['drum']=Matrix.Translation((.0008,-.002,-.022))@Matrix(json.loads((O/'m4_root_inverse.json').read_text()))
materials={};parts={}
def material(name):
 if name not in materials:
  m=bpy.data.materials.new(name);m.diffuse_color=(.08,.09,.1,1);materials[name]=m
 return materials[name]
def box(name,center,size):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material('AKM_AdapterSteel'));b=o.modifiers.new('MachinedEdges','BEVEL');b.width=.0007;b.segments=2;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=b.name);return o
for key,d in raw.items():
 me=bpy.data.meshes.new('AKM_'+key);me.from_pydata([transforms[key]@Vector(v) for v in d['verts']],[],d['faces']);me.update()
 for name in d['materials']:me.materials.append(material(key+'_'+name))
 for p,i in zip(me.polygons,d['indices']):p.material_index=i;p.use_smooth=True
 layer=me.uv_layers.new(name='UVMap')
 for dst,src in zip(layer.data,d['uv']):dst.uv=src
 if key=='angled':
  # The M4 clamp extends through the AKM wooden handguard. Terminate it at the new rail.
  bm=bmesh.new();bm.from_mesh(me)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,.0226),plane_no=(0,0,1),clear_outer=True,clear_inner=False)
  rim=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-.0226)<.00001 for v in e.verts)]
  if rim:bmesh.ops.holes_fill(bm,edges=rim,sides=0)
  bm.to_mesh(me);bm.free();me.update()
 ob=bpy.data.objects.new('AKMA_'+key,me);s.collection.objects.link(ob);group=[ob]
 if key=='optic':
  group+=[box('AKM_receiver_bridge',(.0008,-.055,.105),(.043,.122,.010)),box('AKM_top_rail',(.0008,-.055,.111),(.021,.12,.004))]
  group.append(box('AKM_bridge_saddle',(.0008,-.055,.095),(.028,.118,.014)))
  for y in [-.085,-.025]:group.append(box('AKM_bridge_support',(-.0205,y,.085),(.006,.018,.030)))
 elif key in ['prism','angled']:
  group.append(box('AKM_under_rail',(.0008,-.30,.0226),(.023,.130 if key=='angled' else .085,.008)))
  for y in [-.33,-.27]:group.append(box('AKM_rail_fastener',(.0008,y,.025),(.030,.009,.010)))
 if key=='drum':
  # Root-space geometry must follow the existing magazine's idle-to-rest motion.
  xf=mag.inverted()@root
  for o in group:
   o.data.transform(xf@o.matrix_world);o.matrix_world=Matrix.Identity(4)
 bpy.ops.object.select_all(action='DESELECT')
 for o in group:o.select_set(True)
 bpy.context.view_layer.objects.active=ob;bpy.ops.object.join();ob.name='SM_AKM_'+key
 bpy.ops.export_scene.fbx(filepath=str(O/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
 # Place authored parts on the live rig for visual review.
 xf=r.matrix_world@(mag if key=='drum' else root);ob.matrix_world=xf;world=ob.matrix_world.copy();ob.parent=r;ob.parent_type='BONE';ob.parent_bone='WPN_SOCKET_Magazine' if key=='drum' else 'WPN_root';bpy.context.view_layer.update();ob.matrix_world=world;parts[key]=ob.name
(O/'fits.json').write_text(json.dumps(fits,indent=2));(O/'parts.json').write_text(json.dumps(parts,indent=2))
for act in bpy.data.actions:act.use_fake_user=True
runpy.run_path(str(O/'preview_visibility.py'))['configure_preview']()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_Attachments_Editable.blend'));print('AKM_PARTS_BUILD_PASS')

