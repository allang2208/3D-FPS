"""Save charge prediction defaults after the native build, without reimporting animation."""
from pathlib import Path
import json,shutil
import unreal as u
root=Path(__file__).resolve().parent;project=root.parents[1]
if Path(u.Paths.project_dir()).resolve()!=project.resolve():raise RuntimeError('Wrong UE project')
path='/Game/Monsters/FleshHand/BP_FleshHand'
if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserving unsaved hand Blueprint changes')
bp=u.load_asset(path);cdo=u.get_default_object(bp.generated_class())
settings={'charge_lead_strength':1.,'charge_max_lead_distance':450.}
for key in settings:cdo.get_editor_property(key)
backup=(root.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/Charge/BeforePrediction/BP_FleshHand.uasset')
if not backup.exists():
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(project/'Content/Monsters/FleshHand/BP_FleshHand.uasset',backup)
bp.modify();cdo.modify()
for key,value in settings.items():cdo.set_editor_property(key,value)
u.EditorAssetLibrary.set_metadata_tag(bp,'FleshHand.ChargePrediction','MutantLead20260927')
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('Hand Blueprint save failed')
report={'state':'assets_saved','saved':[bp.get_path_name()],'settings':settings,'source':'Mutant3Feral.cpp BuildPounceVelocity',
        'sampling':'end of windup; planar intercept time only','fallbacks':[1.,.5,0.],'runtime_tested':False,'game_started':False}
(root/'Charge/prediction_installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for file in (root/'Charge/ue_installation.json',root/'ue_installation.json'):
    receipt=json.loads(file.read_text(encoding='utf-8'))
    if file.parent.name=='Charge':receipt['settings'].update(settings);receipt['prediction']=report
    else:receipt['charge_attack']['settings'].update(settings);receipt['charge_attack']['prediction']=report
    file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('FLESHHAND_CHARGE_PREDICTION_SAVED '+str(root/'Charge/prediction_installation.json'))
