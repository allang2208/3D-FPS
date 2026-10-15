"""Read the loaded quick clip, its imported tracks, and current player sampling."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
asset=u.load_asset('/Game/Weapons/SteelWarhammer20261014/QuickCombatV1/A_Warhammer_QuickCombat')
def transform(t):
    p=t.translation;q=t.rotation;s=t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
out={'file':asset.get_editor_property('asset_import_data').get_first_filename(),
     'seconds':asset.get_play_length(),'metadata':dict(u.EditorAssetLibrary.get_metadata_tag_values(asset)),'samples':{}}
for t in (0.,.09,.15,.175,.33,.5):
    out['samples'][str(t)]={n:transform(u.AnimationLibrary.get_bone_pose_for_time(asset,n,t,False)) for n in ('WPN_root','upperarm_l','hand_l','upperarm_r','hand_r')}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    pawn=u.GameplayStatics.get_player_character(world,0)
    if pawn:
        out['weapon_state']=str(pawn.get_weapon_state())
        for c in pawn.get_components_by_class(u.SkeletalMeshComponent):
            if c.get_name()=='ProductionToolHands':
                out['player_position']=c.get_position()
(P/'animation_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
