"""Read only the actor defaults needed to author reach and death integration."""
import unreal as u, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
roles={'Spitter':'/Game/Monsters/SpitterZombie/BP_SpitterZombie','Nurse':'/Game/Monsters/NurseZombie/BP_NurseZombie'}
objects={key:u.get_default_object(u.load_asset(path).generated_class()) for key,path in roles.items()}
objects['Fat']=u.get_default_object(u.FatZombie)
report={'actors':{},'random_attack_native_loaded':hasattr(u,'SpitterAttackVariant')}
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
report['pie']=bool(level and level.is_in_play_in_editor())
report['dirty_spitter']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if p.get_path_name().startswith('/Game/Monsters/SpitterZombie/')]
for role,cdo in objects.items():
    mesh=cdo.get_editor_property('visual_mesh')
    data={key:cdo.get_editor_property(key) for key in ['attack_range','attack_damage','contact_time','contact_end','recovery_time','corpse_seconds']}
    data['attack_clip']=cdo.get_editor_property('attack_clip').get_path_name()
    data['physics_asset']=mesh.physics_asset.get_path_name() if mesh and mesh.physics_asset else None
    kd=cdo.get_editor_property('knockdown')
    data['knockdown']={key:str(kd.get_editor_property(key)) for key in ['enabled','fall_clip','get_up_clip','prone_get_up_clip','corpse_settle_deadline']}
    report['actors'][role]=data
(ROOT/'inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SPITTER_COMBAT_DEATH_INPUTS '+json.dumps(report,ensure_ascii=False))
