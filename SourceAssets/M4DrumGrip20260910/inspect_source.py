import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Drum_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
report={'objects':[(o.name,o.type,o.parent.name if o.parent else None) for o in s.objects], 'actions':[(a.name,list(a.frame_range)) for a in bpy.data.actions], 'samples':{}}
d=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(d['source_to_component']);center=Vector(d['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
for name,frames in [('A_M4_HK416_drum_reload',[0,15,29,50,65,76,85,95,110,126]),('A_M4_HK416_drum_reload_empty',[0,12,21,40,54,65,80,100,130,162])]:
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];result=[]
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center)
  result.append({'frame':f,'drum_matrix':[list(v) for v in D],'bones':{n:{'in_drum':list(D.inverted()@r.pose.bones[n].head),'matrix':[list(v) for v in r.pose.bones[n].matrix],'basis':[list(v) for v in r.pose.bones[n].matrix_basis]} for n in ['hand_l','index_01_l','index_03_l','middle_01_l','middle_03_l','thumb_01_l','thumb_03_l','pinky_03_l']}})
 report['samples'][name]=result
(OUT/'source_inspection.json').write_text(json.dumps(report,indent=2))
print('INSPECT_DONE',report['objects'])
