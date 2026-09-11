import bpy,json,sys,math,bmesh
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;out=O/'akm';out.mkdir(exist_ok=True)
sources={'canted':('CantedGripMigration20260911/m4/canted','Canted','CG_'),'vertical':('VerticalGripErgonomic20260911/vertical','Vertical','VG_'),'prism':('VerticalGripErgonomic20260911/prism','Prism','PH_'),'angled':('AngledForegrip20260910/WristNatural','Foregrip','FG_')}
oldfits=json.loads((S/'AKMAttachments20260911/fits.json').read_text());report={}
for key,(folder,title,prefix) in sources.items():
 path=S/folder;fit=json.loads((path/'fit_final.json').read_text());file=path/f'A_M4_{title}_idle.blend'
 bpy.ops.wm.open_mainfile(filepath=str(file));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};G=p['WPN_root']@Matrix(fit['grip_in_root']);new=Matrix(oldfits['angled' if key=='angled' else 'prism']['grip_in_root'])
 # Vertical/canted top pivots use the same wooden-handguard saddle as prism.
 if key in ['vertical','canted']:new.translation.z+=.0007
 if key=='angled':new.translation.z-=.032
 local=G.inverted();digits={n:[list(x) for x in p['hand_l'].inverted()@m] for n,m in p.items() if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))}
 report[key]={'source':str(file),'source_fit':str(path/'fit_final.json'),'prefix':prefix,'grip_in_root':[list(x) for x in new],'hand_in_root':[list(x) for x in new@local@p['hand_l']],'digits_in_hand':digits,'rest':{n:[list(x) for x in m] for n,m in rest.items()},'m4_hand_in_grip':[list(x) for x in local@p['hand_l']]}
 if key in ['vertical','canted','angled']:
  # Copy evaluated geometry with original UV and materials; no grip resizing.
  meshes=[]
  for ob in [x for x in s.objects if x.type=='MESH' and x.name.startswith(prefix)]:
   e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(e);me.transform(new@local@e.matrix_world);obj=bpy.data.objects.new('AKM_'+key+'_part',me);s.collection.objects.link(obj);meshes.append(obj)
  if key=='angled':
   for obj in meshes:
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,-.0094),plane_no=(0,0,1),clear_outer=True,clear_inner=False);rim=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z--.0094)<.00001 for v in e.verts)]
    if rim:bmesh.ops.holes_fill(bm,edges=rim,sides=0)
    bm.to_mesh(obj.data);bm.free();obj.data.update()
  mat=bpy.data.materials.new('AKM_AdapterSteel')
  if key=='angled':
   for y in [-.35]:
    bpy.ops.mesh.primitive_cube_add(size=1,location=(.0008,y,.0046));ob=bpy.context.object;ob.scale=(.023,.022,.030);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(mat);b=ob.modifiers.new('StandoffEdge','BEVEL');b.width=.0007;b.segments=2;bpy.ops.object.modifier_apply(modifier=b.name);meshes.append(ob)
  for center,size in [((.0008,-.30,.0226),(.023,.120 if key=='angled' else .055 if key=='canted' else .085,.008)),((.0008,-.32 if key=='canted' else -.33,.033 if key=='canted' else .025),(.030,.009,.006 if key=='canted' else .010)),((.0008,-.28 if key=='canted' else -.27,.033 if key=='canted' else .025),(.030,.009,.006 if key=='canted' else .010))]:
   bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(mat);b=ob.modifiers.new('MachinedEdge','BEVEL');b.width=.0007;b.segments=2;bpy.ops.object.modifier_apply(modifier=b.name);meshes.append(ob)
  bpy.ops.object.select_all(action='DESELECT')
  for ob in meshes:ob.select_set(True)
  bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_AKM_'+key
  bpy.ops.export_scene.fbx(filepath=str(out/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
  report[key]['materials']=[m.name for m in ob.data.materials]
  # Separate editable install part in root-local metres.
  bpy.data.libraries.write(str(out/(ob.name+'.blend')),{ob},fake_user=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'AKMAttachments20260911/AKM_Attachments_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
for key,f in report.items():
 diffs={}
 for b in r.data.bones:
  if b.name not in f['rest'] or not b.parent:continue
  before=(Matrix(f['rest'][b.name]).translation-Matrix(f['rest'][b.parent.name]).translation).length;after=(b.head_local-b.parent.head_local).length
  if b.name.endswith('_l'):diffs[b.name]=after-before
 f['bone_length_delta_m']=diffs
(out/'fits.json').write_text(json.dumps(report,indent=2));print('AKM_M4_REST_COMPARE',{k:max(abs(v) for v in f['bone_length_delta_m'].values()) for k,f in report.items()},flush=True)
