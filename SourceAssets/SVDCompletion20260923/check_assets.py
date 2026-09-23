import unreal as u,json,math
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923');B='/Game/Weapons/SVDDragunov20260922/Complete20260923';auth=json.loads((O/'authoring.json').read_text());report={'clips':{},'materials':{},'audio':{},'scope':'Asset readback only; no gameplay acceptance'}
mesh=u.load_asset(B+'/SK_SVD_Manny');assert isinstance(mesh,u.SkeletalMesh)
sk=mesh.skeleton;report['mesh']=mesh.get_path_name();report['skeleton']=sk.get_path_name()
for slot in mesh.materials:
 m=slot.material_interface;parent=m
 while isinstance(parent,u.MaterialInstance):parent=parent.get_editor_property('parent')
 report['materials'][str(slot.material_slot_name)]={'asset':m.get_path_name(),'skeletal_usage':bool(parent.get_editor_property('used_with_skeletal_mesh'))};assert report['materials'][str(slot.material_slot_name)]['skeletal_usage']
for key,info in auth['clips'].items():
 a=u.load_asset(B+'/Animations/A_SVD_'+key);assert isinstance(a,u.AnimSequence),key
 duration=a.get_play_length();report['clips'][key]={'duration':duration,'expected':info['duration'],'skeleton_matches':a.get_editor_property('skeleton')==sk,'saved':u.EditorAssetLibrary.does_asset_exist(a.get_path_name())};assert abs(duration-info['duration'])<.015,(key,duration);assert a.get_editor_property('skeleton')==sk
for i in range(1,5):
 a=u.load_asset(B+f'/Audio/S_SVD_Fire_{i:02d}');assert isinstance(a,u.SoundWave);report['audio'][a.get_name()]={'duration':a.get_editor_property('duration')};assert a.get_editor_property('duration')>0
report['ok']=True;(O/'asset_check.json').write_text(json.dumps(report,indent=2));print('SVD_ASSETS_OK',len(report['clips']),'clips',len(report['materials']),'materials',len(report['audio']),'voices')
