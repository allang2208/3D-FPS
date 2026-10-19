"""Save scoped diagnosis and actual native build receipts, without running gameplay."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
builds={}
for target in ['FPSGAMEEditor','FPSGAME']:
    files=sorted(P.glob(f'build-{target}-*-receipt.json'))
    builds[target]=json.loads(files[-1].read_text(encoding='utf-8-sig')) if files else {'exit_code':None}
    if files:builds[target]['receipt']=files[-1].name
complete=all(v.get('exit_code')==0 for v in builds.values())
paths=['Source/FPSGAME/Characters/FPSBodySwordMotion.h','Source/FPSGAME/Characters/FPSBodySwordPose.inl','Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp']
result={'revision':'ZhufengWhirlwindMotionV2','source_fix_saved':True,'native_build_complete':complete,
    'editor_build_complete':builds['FPSGAMEEditor'].get('exit_code')==0,
    'game_build_complete':builds['FPSGAME'].get('exit_code')==0,
    'builds':builds,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
    'diagnosis':'Existing Start/Loop/End clips are root-neutral; Zhufeng removed the full-body turn without restoring the upper-body turn.',
    'animation_assets_changed':False,'game_tested':False,'editor_started':False,
    'live_coding_applied':False,'live_coding_attempts':['CompileNotStarted: fixed FName conditional type','connection closed during normal editor shutdown; moved to regular build'],
    'scope':['same whirlwind model turn and phase curve','upper-body rotation preserves both hand contacts','pelvis and legs retain forward gait','entry from evaluated carry pose']}
(P/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if complete:
    base=P.parent/'ZhufengBladeV1'
    file=base/'delivery.json'
    old=json.loads(file.read_text(encoding='utf-8'))
    old.update(native_build_complete=True,motion_revision='../ZhufengWhirlwindMotionV2/delivery.json',builds=builds)
    for build in old['builds'].values():build['receipt']='../ZhufengWhirlwindMotionV2/'+build['receipt']
    file.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    file=base/'import_receipt.json';old=json.loads(file.read_text(encoding='utf-8'))
    old.update(native_build_pending=False,effects_applied=True,native_build_receipt='../ZhufengWhirlwindMotionV2/delivery.json')
    file.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    file=P.parent/'ZhufengBladeConceptV1/design.json';old=json.loads(file.read_text(encoding='utf-8'))
    old.update(status='assets_and_native_build_saved',motion_revision='../ZhufengWhirlwindMotionV2/delivery.json')
    file.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'native_build_complete':complete,'game_tested':False}))
