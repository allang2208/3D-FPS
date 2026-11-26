"""Record the saved R8 groom and actual NPC offscreen images without changing the face."""
import json,hashlib,shutil
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115'
R=N/'HairNativeCombR9';H=N/'HairReferenceR5'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
saved=read(H/'saved_assets.json');author=read(R/'authoring.json')
if not saved['completed']:raise RuntimeError('Groom save incomplete')
capture=read(H/'EngineRuntime/assets.json')
if not capture.get('production_actor_assembly') or not capture.get('offscreen_hair_guide_updates'):
 raise RuntimeError('Actual NPC guide-update capture missing')
if capture['grooms'][0]['curves']!=author['core_curves']:
 raise RuntimeError('Capture belongs to another hair revision')
retained=read(R/'retained_assets.json')
for key,info in retained.items():
 info['current_sha256']=hashlib.sha256(Path(info['path']).read_bytes()).hexdigest()
 info['unchanged']=info['sha256']==info['current_sha256']
 if not info['unchanged']:raise RuntimeError(key+' was changed outside this hair geometry update')
shutil.copytree(H/'EngineRuntime',R/'EngineRuntime',dirs_exist_ok=True)
now=datetime.now().astimezone().isoformat()
source=R/'Authored/ChapelNun_OriginalFace_NativeComb_R9.blend'
delivery={'revision':'NativeCombR9','completed_at':now,'reference':str(N/'Design/NunHead_R2.png'),
 'assets':saved['assets'],'material':saved['material'],'authoring':author,'source_blend':str(source),
 'retained_assets':retained,'runtime_capture':capture,'save_log':str(N/'ProductionR1/Logs/native-comb-r9-engine.log'),
 'head_geometry_restoration_receipt':str(N/'FaceOriginalRestoreR6/original_face_verified.json'),
 'interactive_gameplay_tested':False,'dynamic_physics_stress_tested':False,'runtime_gameplay_code_changed':False,'inspection_tool_changed':True,'editor_build':read(R/'FPSGAMEEditor-build.json'),
 'images':{v:str(R/'EngineRuntime'/(v+'.png')) for v in ('front','threequarter','crown','profile','back','fullbody')}}
write(R/'delivery.json',delivery)
write(H/'delivery.json',{'revision':'NativeCombR9','active_package_folder':'HairReferenceR5','completed_at':now,
 'assets':saved['assets'],'material':saved['material'],'source_blend':str(source),'delivery':str(R/'delivery.json'),
 'interactive_gameplay_tested':False})
main=read(N/'ProductionR1/delivery.json')
main.update(activeHairRevision='NativeCombR9',sourceBlend=str(source),hairReferenceDelivery=str(R/'delivery.json'),
 completedAt=now,visualInspection=str(R/'EngineRuntime/assets.json'),runtimeTested=False)
main['appearance']['hair']='Dense continuous black fibres; asymmetric waved forehead sweep, layered ear-top sides, full crown and interwoven low chignon; accepted native female hair material unchanged'
main['visualAcceptance']='Actual NPC offscreen idle images; interactive church gameplay and dynamic physics remain for user testing'
main['assetSaveLog']=delivery['save_log']
write(N/'ProductionR1/delivery.json',main)
print('FULL_REFERENCE_HAIR_DELIVERED',str(R/'delivery.json'))
