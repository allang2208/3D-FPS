"""Restore segment B from its untouched A counterpart with an explicit yaw."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
world=UE.get_editor_world()
if UE.get_game_world() or not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_AuthoredExpansion':raise RuntimeError('Open owned expansion in editor before applying')
actors=list(AA.get_all_level_actors())
def label(a):return next((str(t)[12:] for t in a.tags if str(t).startswith('SourceLabel:')),None)
source={label(a):a for a in actors if a.get_actor_label().startswith('DGN_A_')}
targets=[a for a in actors if a.get_actor_label().startswith('DGN_B_')]
if len(source)!=164 or len(targets)!=164:raise RuntimeError('Segment contents changed; preserve current edit')
delta=u.Transform()
delta.translation=u.Vector(2600,-1800,94)
delta.rotation=u.Rotator(pitch=0,yaw=-90,roll=0).quaternion()
group=set(targets)
for a in targets:
    origin=source[label(a)]
    if a.get_attach_parent_actor() not in group:
        a.modify()
        a.set_actor_transform(u.MathLibrary.compose_transforms(origin.get_actor_transform(),delta),False,True)
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('External actor save failed')
if not ED.save_current_level():raise RuntimeError('Map save failed')
receipt=json.loads((ROOT/'Receipts/assembly.json').read_text(encoding='utf-8'))
receipt['rotation_fix']={'reason':'Rotator positional args applied pitch instead of yaw','pitch':0,'yaw':-90,'roll':0,'actors':len(targets),'saved':True}
(ROOT/'Receipts/assembly.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('B_SEGMENT_YAW_FIXED_AND_SAVED',len(targets))
print('OWNED_PACKAGES_SAVED',len(owned))
print('ROTATION_APPLIED',str(next(a for a in targets if a.get_actor_label()=='DGN_B_AV2_MainCorridor_Floor').get_actor_rotation()))
