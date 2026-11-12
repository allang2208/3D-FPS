"""Restore pre-Beast06 melee references, preserving pounce and other settings."""
from pathlib import Path
import json
import unreal as u

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
ROOT = BASE/'ClawV17'
ROOT.mkdir(parents=True,exist_ok=True)
MAIN = '/Game/Monsters/MantisM27/BP_MantisM27'
TARGETS = [MAIN, '/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1',
           '/Game/Monsters/MantisM27/ArmChainV15/BP_MantisM27_ArmChainReviewV15']
SLOTS = {'attack_clip':'LeftSlash','left_slash_clip':'LeftSlash','right_slash_clip':'RightSlash'}
old = json.loads((BASE/'Beast06V2/activation_receipt.json').read_text(encoding='utf-8'))['blueprints'][MAIN]['previous']
report = {'scope':'Restore ordinary melee only','restored_revision':'ClawV16','blueprints':{},
          'runtime_tested':False,'offline_validated':False,'rendered':False}
L = u.EditorAssetLibrary

def path(obj): return obj.get_path_name() if obj else None
def receipt():
    (ROOT/'rollback_melee_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        conflicts = dirty.intersection(TARGETS)
        if conflicts: raise RuntimeError('Preserve unsaved targets: '+', '.join(sorted(conflicts)))
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Preserve running PIE; defer melee rollback')
    restored = {prop:u.load_asset(asset) for prop,asset in old.items()}
    if not all(restored.values()): raise RuntimeError('Missing original ClawV16 clips')
    pending = []
    for target in TARGETS:
        bp = u.load_asset(target)
        if not bp:
            if target == MAIN: raise RuntimeError('Missing formal M27 Blueprint')
            report['blueprints'][target] = {'skipped':'Review Blueprint no longer exists'}
            continue
        cdo = u.get_default_object(bp.generated_class())
        previous = {prop:path(cdo.get_editor_property(prop)) for prop in SLOTS}
        for prop, role in SLOTS.items():
            allowed = {old[prop]}
            for revision in ['Beast06V1','Beast06V2','ArmChainV15']:
                name = 'A_M27_'+role+'_'+revision
                allowed.add('/Game/Monsters/MantisM27/'+revision+'/Animations/'+name+'.'+name)
            if previous[prop] not in allowed:
                raise RuntimeError('Unrecognized concurrent melee change; preserve '+target+':'+prop)
        report['blueprints'][target] = {'saved':False,'previous':previous,'restored':old,
            'retained_clips':{prop:path(cdo.get_editor_property(prop)) for prop in
                ['idle_clip','walk_clip','death_clip','pounce_windup_clip','pounce_flight_clip','pounce_land_clip']},
            'retained_timing':{prop:cdo.get_editor_property(prop) for prop in ['contact_time','contact_end','recovery_time']}}
        pending.append((target,bp,cdo))
    receipt()
    for target,bp,cdo in pending:
        for prop,clip in restored.items(): cdo.set_editor_property(prop,clip)
        L.set_metadata_tag(bp,'AttackRevision','ClawV16 restored to pre-Beast06 melee after user feedback; pounce preserved')
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        if not L.save_loaded_asset(bp,False): raise RuntimeError('Save failed: '+target)
        report['blueprints'][target]['saved'] = True; receipt()
        print('M27_ORIGINAL_MELEE_RESTORED '+target,flush=True)
    report['rollback_saved'] = True; receipt()
except Exception as error:
    report['error'] = str(error); receipt(); raise
