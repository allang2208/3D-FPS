"""Read only: current PIE owner, gun flags, quick phase and tool clip."""
import unreal as u,json,os
from pathlib import Path
P=Path(__file__).resolve().parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
state={'editor_pid':os.getpid(),'world':world.get_path_name() if world else None}
def path(x):return x.get_path_name() if x else None
if world:
    pawn=u.GameplayStatics.get_player_character(world,0)
    state['pawn']=path(pawn)
    if pawn:
        for prop in ('bUseASH12','WeaponState','ActiveInventoryWeaponDefinition','bInventoryWeaponReady'):
            try:state[prop]=str(pawn.get_editor_property(prop))
            except Exception as ex:state[prop]=str(ex)
        quick=pawn.get_editor_property('QuickCombatPistol')
        state['quick']={'phase':str(quick.get_phase()),'age':quick.get_action_age(),'occupying':quick.is_occupying_left_hand()}
        for comp in pawn.get_components_by_class(u.SkeletalMeshComponent):
            if comp.get_name()=='ProductionToolHands':
                anim=comp.get_anim_instance()
                state['tool']={'visible':comp.is_visible(),'mode':str(comp.get_editor_property('animation_mode')),'instance':path(anim)}
                if anim and hasattr(anim,'get_current_asset'):state['tool']['clip']=path(anim.get_current_asset())
                if anim and hasattr(anim,'get_current_time'):state['tool']['time']=anim.get_current_time()
asset=u.load_asset('/Game/Weapons/SteelWarhammer20261014/QuickCombatV1/A_Warhammer_QuickCombat')
state['asset']={'path':path(asset),'seconds':asset.get_play_length() if asset else None,
                'revision':u.EditorAssetLibrary.get_metadata_tag(asset,'WarhammerQuickCombat.Revision') if asset else None}
state['dirty_content']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
state['dirty_maps']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
(P/'runtime_before.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
