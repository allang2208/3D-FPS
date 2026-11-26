"""Record the actual saved character, readback and final UE capture evidence."""
import json,hashlib,shutil
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115';R=N/'FaceOriginalRestoreR6';H=N/'HairReferenceR5'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
head=read(R/'final_head_saved.json');collar=read(R/'final_collar_saved.json');groom=read(H/'saved_assets.json');verified=read(R/'original_face_verified.json')
if not head['saved'] or not collar['saved'] or not groom['completed']:raise RuntimeError('Asset save incomplete')
for directory,target in [('EngineRuntime','EngineRuntime')]:
 shutil.copytree(H/directory,R/target,dirs_exist_ok=True)
capture=read(R/'EngineRuntime/assets.json')
if not capture.get('production_actor_assembly'):raise RuntimeError('Runtime assembly capture missing')
if not capture.get('offscreen_hair_guide_updates'):raise RuntimeError('Offscreen groom guide updates missing')
if capture['grooms'][0]['curves']!=groom['authoring']['core_curves']:raise RuntimeError('Capture contains an older hair revision')
binaries=[]
for name in ('UnrealEditor-FPSGAME.dll','FPSGAME.exe'):
 file=P/'Binaries/Win64'/name;data=file.read_bytes();path='/Game/Characters/ChapelNun20261115/HairReferenceR5/Grooms/Nun_LowBun_Core_R5'
 found=path.encode('utf-16-le') in data or path.encode() in data
 if not found:raise RuntimeError('Active hair reference absent in '+name)
 binaries.append({'path':str(file),'modified_at':datetime.fromtimestamp(file.stat().st_mtime).astimezone().isoformat(),'contains_active_hair_reference':found})
now=datetime.now().astimezone().isoformat();source=R/'Authored/ChapelNun_OriginalFace_ReferenceHair_R6.blend'
delivery={'revision':'FaceOriginalRestoreR6','completed_at':now,'head':head,'collar':collar,'grooms':groom,'source_blend':str(source),'source_restoration':read(R/'restoration.json'),'geometry_verification':verified,'runtime_capture':capture,'binaries':binaries,'native_code_changed_in_this_face_repair':False,'interactive_gameplay_tested':False,'dynamic_physics_stress_tested':False,'source_lip_microgeometry_retained':True,'images':{v:str(R/'EngineRuntime'/(v+'.png')) for v in ('front','threequarter','crown','profile','back','fullbody')}}
delivery['hair_shape_revision']='Young R2 side-swept fringe and variable-length temple locks; native black hair shading retained'
delivery['hair_material_settings']=read(R/'hair_render_settings.json')['after']['material']
delivery['inspection_tool_fix']='Isolated scene view runs groom guide updates; SceneCapture normally skips these and cannot validate animated hair by itself'
delivery['editor_build']=read(R/'FPSGAMEEditor-build.json')
write(R/'delivery.json',delivery)
write(H/'delivery.json',{'revision':'HairReferenceR5','completed_at':now,'reference':groom['authoring']['reference'],'assets':groom['assets'],'material':groom['material'],'source_blend':str(source),'active_surface_revision':'FaceOriginalRestoreR6','runtime_grooms':capture['grooms'],'binaries':binaries,'delivery':str(R/'delivery.json'),'interactive_gameplay_tested':False})
main=read(N/'ProductionR1/delivery.json');main.update(activeAppearanceRevision='FaceOriginalRestoreR6',activeHairRevision='HairReferenceR5',sourceBlend=str(source),refinementDelivery=str(R/'delivery.json'),hairReferenceDelivery=str(H/'delivery.json'),completedAt=now,visualInspection=str(R/'EngineRuntime/assets.json'),runtimeTested=False)
main['appearance']['head']='Original Meshy face and complete chin restored; only lower neck at z=139.1-142.5 cm fitted beneath collar; source PBR retained'
main['appearance']['hair']='Black off-centre swept waves, temple wisps and compact crossed low bun from approved R2 concept; native female hair shader and loose strand physics'
for part in ('Core','Loose'):
 key='Nun_LowBun_'+part;main['savedAssets'][key]=groom['assets'][key+'_R5'];main['savedAssets'][key+'_Binding']=groom['assets'][key+'_R5_Binding']
main['assetSaveLog']=str(N/'ProductionR1/Logs/restored-face-save-engine.log');main['visualAcceptance']='Original source and UE saved LOD0 geometry compared; actual NPC offscreen idle captures reviewed; no interactive church gameplay'
write(N/'ProductionR1/delivery.json',main)
diagnosis=read(N/'FaceDiagnosisR1/diagnosis.json');diagnosis['status']='confirmed_chin_deformation_restored_and_engine_readback_completed';diagnosis['repair_delivery']=str(R/'delivery.json');diagnosis['pending']=[];diagnosis['engine_blocker']=None;write(N/'FaceDiagnosisR1/diagnosis.json',diagnosis)
print('RESTORED_CHARACTER_DELIVERY_RECORDED',str(R/'delivery.json'))
