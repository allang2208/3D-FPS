"""Read the reported M4 activation failure in an existing session only."""
import json
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME/Saved/M4BareActivation20260925')
root.mkdir(parents=True,exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report={'playing':bool(world),'bare_switch':u.SystemLibrary.get_console_variable_int_value('fps.Outfit.BareArmsCandidate'),
        'components':[]}
report['world_body_suppressed']=u.SystemLibrary.get_console_variable_int_value('fps.body.WorldBodySuppress')
pawn=u.GameplayStatics.get_player_pawn(world,0) if world else None
if not pawn:
    cdo=u.get_default_object(u.FPSGAMECharacter)
    report['default_components']=[c.get_name() for c in cdo.get_components_by_class(u.ActorComponent)]
    for c in cdo.get_components_by_class(u.SkeletalMeshComponent):
        if c.get_name()=='AKMViewmodel':
            mesh=c.skeletal_mesh_asset
            report['default_m4']={'mesh':mesh.get_path_name() if mesh else None,
                                 'only_owner':c.get_editor_property('only_owner_see')}
if pawn:
    report['pawn']=pawn.get_path_name()
    outfit=pawn.get_component_by_class(u.FPSModularOutfitComponent)
    report['outfit_component']=outfit.get_path_name() if outfit else None
    report['outfit_tick']=outfit.is_component_tick_enabled() if outfit else None
    body=pawn.get_component_by_class(u.FPSPlayerBodyComponent)
    report['body_tick']=body.is_component_tick_enabled() if body else None
    for c in pawn.get_components_by_class(u.SkeletalMeshComponent):
        mesh=c.skeletal_mesh_asset
        if not mesh:continue
        if 'M4' not in mesh.get_path_name() and 'ModularOutfit' not in [str(x) for x in c.component_tags]:continue
        report['components'].append({'name':c.get_name(),'mesh':mesh.get_path_name(),
            'visible':c.is_visible(),'hidden':c.get_editor_property('hidden_in_game'),
            'only_owner':c.get_editor_property('only_owner_see'),
            'owner_no_see':c.get_editor_property('owner_no_see'),
            'parent':c.get_attach_parent().get_path_name() if c.get_attach_parent() else None,
            'tags':[str(x) for x in c.component_tags],
            'materials':[m.get_path_name() if m else '' for m in c.get_materials()],
            'sections_lod0':[c.is_material_section_shown(i,0) for i in range(c.get_num_materials())]})
(root/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M4_BARE_ACTIVATION',json.dumps(report,ensure_ascii=False))
