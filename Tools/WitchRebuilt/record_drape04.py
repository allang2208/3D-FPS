import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'DrapeGrip20260922';DEST='/Game/Monsters/WitchRebuilt'
mesh=u.load_asset(DEST+'/SK_WitchRebuilt');cloth=list(mesh.get_editor_property('mesh_clothing_assets'))
result={'cloth':[c.get_name() for c in cloth],'clips':{},'runtime_tested':False,'simulation_tested':False,
    'native_build':'Saved/BuildEditor/build-20260922-140814.log',
    'dirty':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)]}
for role in ('Idle','Walk','CastPoison','ThrowPoisonBottle','Hit','TurnLeft','TurnRight'):
    clip=u.load_asset(DEST+'/Animations/A_WitchRebuilt_'+role)
    result['clips'][role]={'duration':clip.get_editor_property('sequence_length')}
expected=('WitchRebuilt_LowerDrape05','WitchRebuilt_UpperDrape05')
if len(cloth)!=2 or any(not any(c.get_name().startswith(n) for c in cloth) for n in expected):raise RuntimeError('Drape05 not installed: '+str(result['cloth']))
(OUT/'ue_asset_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
report_path=ROOT/'ue_delivery.json';report=json.loads(report_path.read_text())
report.update({'status':'Drape05/Carry04 imported and saved; actual cloth dynamics and hand contact await user test',
    'drape_grip_revision':{'date':'2026-09-22','cloth':result['cloth'],'lower_skin':'continuous pelvis anchor, no calf/foot pulling',
        'upper_cloth':'pinned collar, shoulders and cuffs; loose sleeves/cape','grip_fix':'UE palm cross-product reflection corrected, 5.4 cm placement error removed',
        'source_inspection':'DrapeGrip20260922/source_after.json','native_build':result['native_build'],'runtime_tested':False},
    'runtime_tested':False,'visual_tested':False})
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
