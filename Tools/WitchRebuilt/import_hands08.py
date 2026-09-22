"""Import only Hands08 finger animation; keep Seams07 mesh and drapes intact."""
import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
out=root/'Revision08';folder=Path(__file__).parent;dest='/Game/Monsters/WitchRebuilt'
roles=('Idle','Walk','CastPoison','Hit','TurnLeft','TurnRight','ThrowPoisonBottle','DeathBackward')
p=folder/'import_assets.py'
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{
 '__file__':str(p),'__name__':'__main__','WITCH_REBUILT_STAGE':'animations_a','WITCH_REBUILT_ROLES':roles})
for role in roles:
 clip=u.load_asset(dest+'/Animations/A_WitchRebuilt_'+role)
 u.EditorAssetLibrary.set_metadata_tag(clip,'GripRevision','Hands08: mirrored palm flexion, local thumb hinges, separate shaft/shoulder fit')
 if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Hands08 save failed: '+role)
result={'revision':'Hands08','animations':list(roles),'changed_tracks':'30 finger joint rotations',
 'body_wrist_elbow_tracks_changed':False,'mesh_cloth_material_scale_changed':False,
 'throw_release_seconds':.75,'gameplay_tested':False,'user_visual_acceptance':False}
(out/'ue_asset_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
p=root/'ue_delivery.json';delivery=json.loads(p.read_text(encoding='utf-8'))
delivery.update(status='Hands08 animations installed; gameplay and user visual acceptance pending',revision08=result)
p.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result))
