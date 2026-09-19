import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'M4_DrumGrip_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
d=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(d['source_to_component']);center=Vector(d['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
hand=bpy.data.objects['SK_Manny_Arms_Export'];ids=[v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7]
report={}
for clip,frames in [('reload',[25,50,76,95]),('reload_empty',[43,54,80])]:
 a=bpy.data.actions['A_M4_DrumGrip_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center);inv=D.inverted()
  obj=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());m=obj.to_mesh();p=[inv@obj.matrix_world@m.vertices[i].co for i in ids];obj.to_mesh_clear()
  # Conservative core solid excludes decorative ridges and the magazine neck.
  depths=[min(.033-abs(v.y),.067-Vector((v.x,0,v.z+.085)).length) for v in p]
  worst=sorted(range(len(p)),key=lambda i:depths[i],reverse=True)[:8]
  rows.append({'frame':f,'deepest_core_penetration_cm':max(0,max(depths))*100,'core_penetrating_vertices':sum(x>.002 for x in depths),'hand_vertices':len(p),'worst':[{'p':list(p[i]),'groups':[(hand.vertex_groups[g.group].name,g.weight) for g in hand.data.vertices[ids[i]].groups if g.weight>.1]} for i in worst]})
 report[clip]=rows
(OUT/'mesh_contact_report.json').write_text(json.dumps(report,indent=2));print(report)
r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
for o in r.children:
 if o.type=='MESH' and 'Magazine' not in o.name:o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_M4_DrumGripPreview.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
