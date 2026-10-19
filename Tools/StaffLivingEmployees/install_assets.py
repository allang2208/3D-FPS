"""Save three independent original-body employee Blueprints; never spawn actors."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/StaffLivingEmployees20261017')
DEST='/Game/Monsters/StaffLiving'
LIB=u.EditorAssetLibrary
SOURCE=json.loads((ROOT/'source_inputs.json').read_text(encoding='utf-8'))
VARIANTS=[
    ('LivingStaffMale','男性员工 M-01','FacelessSecurity',270.,24.,94.),
    ('LivingStaffFemaleA','女性员工A M-01','FacelessReceptionist',230.,20.,92.),
    ('LivingStaffFemaleB','女性员工B M-01','FacelessResearcher',250.,22.,90.),
]
report={'stage':'saving','saved':[],'variants':{},'runtime_tested':False,'rendered':False,
        'encounter_placement':'Monster definitions and F6 entries only; staff_living encounters unchanged.'}
def record():
    (ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

# These are new packages, so the active PIE world and every donor remain untouched.
for identity,label,donor,hp,damage,speed in VARIANTS:
    target=DEST+'/BP_'+identity
    if LIB.does_asset_exist(target):raise RuntimeError('Target already exists; preserve it: '+target)
record()
for identity,label,donor,hp,damage,speed in VARIANTS:
    source_bp=u.load_asset(SOURCE['characters'][donor]['blueprint'])
    body=u.load_asset(SOURCE['body_meshes'][donor]['path'])
    if not source_bp or not body:raise RuntimeError('Missing donor for '+identity)
    bp=LIB.duplicate_asset(source_bp.get_path_name(),DEST+'/BP_'+identity)
    if not bp:raise RuntimeError('Cannot duplicate '+identity)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('visual_mesh',body)
    mesh=cdo.get_editor_property('mesh');mesh.set_skeletal_mesh_asset(body)
    mesh.set_editor_property('override_materials',[])
    tags=list(cdo.get_editor_property('tags'))
    for tag in [identity,'StaffLivingEmployee','StaffLiving']:
        if tag not in [str(t) for t in tags]:tags.append(u.Name(tag))
    cdo.set_editor_property('tags',tags)
    for prop,value in [('max_health',hp),('attack_damage',damage),('walk_speed',speed),
                       ('level',3),('rank',u.MonsterRank.NORMAL),('experience_reward',241)]:
        cdo.set_editor_property(prop,value)
    # The complete source bodies already carry their native skin material,
    # skeleton and physics asset. Only remove the guard's visible accessory.
    subsystem=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    library=u.SubobjectDataBlueprintFunctionLibrary
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj=library.get_object_for_blueprint(library.get_data(handle),bp)
        if isinstance(obj,u.SecurityHatComponent):
            obj.set_static_mesh(None)
            obj.set_editor_property('override_materials',[])
    LIB.set_metadata_tag(bp,'ProductionSource','StaffLivingEmployees20261017; original complete body and current donor actions')
    LIB.set_metadata_tag(bp,'MonsterDisplayName',label)
    LIB.set_metadata_tag(bp,'MSeriesNumber','M-01')
    LIB.set_metadata_tag(bp,'IntendedRegion','staff_living')
    LIB.set_metadata_tag(bp,'Vitals','Final Blueprint values; StaffLivingEmployee bypasses donor job multiplier')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    report['variants'][identity]={
        'name':label,'blueprint':bp.get_path_name(),'source_blueprint':source_bp.get_path_name(),
        'body_mesh':body.get_path_name(),'skeleton':SOURCE['body_meshes'][donor]['skeleton'],
        'physics_asset':SOURCE['body_meshes'][donor]['physics_asset'],
        'stats':{'health':hp,'attack':damage,'walk_cm_s':speed,'level':3,'rank':'Normal',
                 'physical_defense':0,'magical_defense':0,'critical_resistance':0,'experience_base':241},
        'shared_clips':SOURCE['characters'][donor]['clips'],
        'attack_timing':{key:SOURCE['characters'][donor]['stats'][key] for key in ['contact_time','contact_end','recovery_time','attack_range']},
        'family_tag':donor,'capsule_and_mesh_transform':'Inherited unchanged from the donor.'}
    record()
    print('EMPLOYEE_SAVED '+label+' '+bp.get_path_name(),flush=True)
report['stage']='saved';record()
print('STAFF_LIVING_EMPLOYEES_SAVED '+str(len(report['saved'])),flush=True)
