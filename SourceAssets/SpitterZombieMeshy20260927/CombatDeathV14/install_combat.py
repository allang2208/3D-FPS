"""Save revised reach and existing ragdoll bindings; optionally finish the V13 pool."""
import unreal as u, json, os, shutil, runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
PROJECT=BASE.parents[1]
DEST='/Game/Monsters/SpitterZombie'
LIB=u.EditorAssetLibrary
settings=json.loads((ROOT/'settings.json').read_text(encoding='utf-8'))
if os.environ.get('SPITTER_HEADLESS')!='1':
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('PIE is active; no combat assets changed')
path=DEST+'/BP_SpitterZombie'
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Preserving unsaved Spitter blueprint edits')
bp=u.load_asset(path)
cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh')
if not mesh.physics_asset:raise RuntimeError('Spitter physical asset is missing')
backup=PROJECT/'trash/spitter-zombie-rollbacks'/ROOT.name/'Before'
backup.mkdir(parents=True,exist_ok=True)
for file in [PROJECT/'Content/Monsters/SpitterZombie/BP_SpitterZombie.uasset',
             BASE/'animation_contract.json',BASE/'ue_installation.json',BASE/'production_status.json']:
    if file.exists() and not (backup/file.name).exists():shutil.copy2(file,backup/file.name)
report=dict(revision=settings['revision'],saved=[],previous_attack_range=cdo.get_editor_property('attack_range'),
    runtime_tested=False,preview_rendered=False,
    movements=[a.get_path_name() if a else None for a in cdo.get_editor_property('movement_clips')],
    movement_reference_speeds=list(cdo.get_editor_property('movement_reference_speeds')))
cdo.set_editor_property('attack_range',settings['attack_range_base_cm'])
kd=cdo.get_editor_property('knockdown')
kd.set_editor_property('enabled',True)
for field,asset in [('fall_clip','Hit_Knockback'),('get_up_clip','LayToIdle'),('prone_get_up_clip','ProneToIdle')]:
    clip=u.load_asset(DEST+'/Animations/A_Spitter_'+asset)
    if clip is None:raise RuntimeError('Missing retained reaction: '+asset)
    kd.set_editor_property(field,clip)

# Both new V13 sequences were already imported. Bind those saved assets here,
# avoiding another import pass while completing the pending random-attack work.
native_pool=hasattr(u,'SpitterAttackVariant')
variant_data=json.loads((BASE/'AttackVariantsV13/authoring.json').read_text(encoding='utf-8'))
default=json.loads((BASE/'AttackD_V12/authoring.json').read_text(encoding='utf-8'))['attack']
entries={'AttackD':default,**variant_data['attacks']}
for entry in entries.values():entry.update(poison=True,poison_stacks_per_hit=1)
if native_pool:
    for entry in entries.values():
        if not u.load_asset(DEST+'/Animations/'+entry['asset_name']):raise RuntimeError('Pending pool animation missing')
        entry['attack_range_base_cm']=settings['attack_range_base_cm']
        entry['attack_damage']=cdo.get_editor_property('attack_damage')
    runpy.run_path(str(BASE/'AttackVariantsV13/install_attacks.py'))['bind_variants'](cdo,entries)
    LIB.set_metadata_tag(bp,'Spitter.AttackRevision',variant_data['revision'])
    LIB.set_metadata_tag(bp,'Spitter.AttackMode','physical_melee_random_variants')
LIB.set_metadata_tag(bp,'Spitter.CombatRevision',settings['revision'])
LIB.set_metadata_tag(bp,'Spitter.DeathPolicy',settings['death_policy'])
if not LIB.save_loaded_asset(bp,False):raise RuntimeError('Spitter combat blueprint save failed')
report['saved'].append(bp.get_path_name())
build_path=ROOT/'build-result.json'
build=json.loads(build_path.read_text(encoding='utf-8-sig')) if build_path.exists() else None
native_complete=bool(build and build['exit_code']==0)
report.update(state='reach_and_attack_pool_saved' if native_pool else 'reach_saved_attack_pool_pending',
    attack_range_base_cm=settings['attack_range_base_cm'],contact_limit_cm=settings['contact_limit_cm'],
    attack_entry_limit_cm=settings['attack_entry_limit_cm'],navigation_stop_range_cm=settings['navigation_stop_range_cm'],
    attack_damage=cdo.get_editor_property('attack_damage'),attack_pool_bound=native_pool,
    physics_asset=mesh.physics_asset.get_path_name(),death_native_build_complete=native_complete,
    death_policy=settings['death_policy'],death_clip_is_budget_fallback=True,
    corpse_seconds=cdo.get_editor_property('corpse_seconds'))
(ROOT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
contract=json.loads((BASE/'animation_contract.json').read_text(encoding='utf-8'))
contract['Attack']['attack_range_base_cm']=settings['attack_range_base_cm']
if native_pool:
    contract['AttackVariants']=dict(revision=variant_data['revision'],selection=variant_data['selection'],variants=entries)
(BASE/'animation_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
delivery=json.loads((BASE/'ue_installation.json').read_text(encoding='utf-8'))
delivery.update(combat_revision=settings['revision'],attack_range_base_cm=settings['attack_range_base_cm'],
    death_policy=settings['death_policy'],death_native_build_complete=native_complete)
if 'melee_settings' in delivery:delivery['melee_settings']['values']['attack_range']=settings['attack_range_base_cm']
if native_pool:
    delivery.update(attack_revision=variant_data['revision'],attack_mode='physical_melee_random_variants',
        attack_selection=variant_data['selection'],attack_variants={key:DEST+'/Animations/'+e['asset_name'] for key,e in entries.items()})
delivery['saved']=list(dict.fromkeys(delivery['saved']+report['saved']))
(BASE/'ue_installation.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
status=json.loads((BASE/'production_status.json').read_text(encoding='utf-8'))
status.update(combat_revision=settings['revision'],attack_range_base_cm=settings['attack_range_base_cm'],
    death_policy=settings['death_policy'],death_native_build_complete=native_complete,tested=False)
if native_pool:status.update(attack_revision=variant_data['revision'],attack_mode='physical_melee_random_variants',attack_variants_assets_saved=True)
if native_pool and native_complete:
    status.update(attack_variants_native_build='Succeeded_in_V14',attack_variants_delivery_scope='three_clip_pool_saved',
        editor_build='Succeeded',editor_build_log=build['log'])
(BASE/'production_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SPITTER_COMBAT_DEATH_SAVED '+json.dumps(report,ensure_ascii=False))
