"""Save the reaction assets on the existing M66 character after a normal DLL build."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/ReactionsV03')
DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before updating M66')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
mesh=u.load_asset(DEST+'/RigV01/SK_M66_BackCompleted');bp=u.load_asset(DEST+'/BP_M66RigPreview')
if not mesh or not bp:raise RuntimeError('M66 mesh/Blueprint missing')
motion=json.loads((ROOT/'Records/motion_import.json').read_text(encoding='utf-8'))
clips={role:u.load_asset(path) for role,path in motion['clips'].items()}
if not all(clips.values()) or len(clips)!=9:raise RuntimeError('Nine saved M66 reaction clips are required')
physics=u.M66IncineratorMonster.build_reaction_physics(mesh)
if not physics:raise RuntimeError('M66 physics body authoring failed')
if not E.save_loaded_asset(physics,False):raise RuntimeError('M66 physics save failed')
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
tags=[tag for tag in cdo.get_editor_property('tags') if str(tag)!='LocomotionStage']
for tag in ('Enemy','M66'):
    if u.Name(tag) not in tags:tags.append(u.Name(tag))
properties={'hit_clips':[clips[r] for r in ('HitFront','HitRight','HitBack','HitLeft')],
    'stun_clip':clips['Stun'],'air_clip':clips['Airborne'],'land_clip':clips['Landing'],
    'get_up_clip':clips['GetUp'],'death_clip':clips['Death'],'reaction_physics':physics,
    'max_health':6000.,'level':12,'rank':u.MonsterRank.BOSS,'experience_reward':0,
    'corpse_seconds':25.,'can_be_damaged':True,'replicates':True,'replicate_movement':True,'tags':tags}
for key,value in properties.items():cdo.set_editor_property(key,value)
component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
component.set_physics_asset(physics,True)
component.set_anim_instance_class(u.M66AnimInstance.static_class())
component.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
component.set_collision_object_type(u.CollisionChannel.ECC_PAWN)
component.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_IGNORE)
component.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY,u.CollisionResponseType.ECR_BLOCK)
cdo.get_editor_property('combat').set_editor_property('hit_clip',clips['HitFront'])
E.set_metadata_tag(bp,'M66.Stage','Navigation, locomotion, four directional stagger, explicit stun, ballistic launch/landing/get-up, death/limited corpse physics; attacks not authored')
E.set_metadata_tag(bp,'M66.Reactions','Server-owned phase/serial/start/end; shared poise gate; per-client corpse simulation')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 Blueprint save failed')
report={'complete':True,'saved':[physics.get_path_name(),bp.get_path_name()],
    'clips':motion['clips'],'physics':physics.get_path_name(),'base_health':6000,'rank':'Boss',
    'level':12,'death_lead_seconds':.9,'corpse_lifetime_seconds':25,
    'f6_entry_id':'IncineratorBossM66Rig','f6_label':'焚骸 M-66（受击·死亡）',
    'server_authoritative_reactions':True,'cosmetic_corpse_simulation':'each peer',
    'runtime_tested':False,'multiplayer_tested':False}
(ROOT/'Records/character_install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_REACTION_CHARACTER_SAVED '+json.dumps(report,ensure_ascii=False))
