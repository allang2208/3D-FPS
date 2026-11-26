"""Record the saved R5 appearance and its actual offscreen capture evidence."""
import json
from datetime import datetime
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'HairReferenceR5'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
saved=read(R/'saved_assets.json');authored=read(R/'authoring.json');capture=read(R/'EngineRuntime/assets.json')
builds=[read(R/(name+'-build.json')) for name in ('FPSGAMEEditor','FPSGAME')]
if not saved['completed'] or any(b['exit_code']!=0 for b in builds):raise RuntimeError('Save/build not completed')
images={view:str(R/'EngineRuntime'/(view+'.png')) for view in ('front','threequarter','profile','back','crown','fullbody')}
inspection={'scope':'Offscreen UE captures of the actual NPC assembly and sampled idle pose','capture':capture,'images':images,'interactive_gameplay_tested':False,'dynamic_hair_physics_stress_tested':False}
write(R/'inspection.json',inspection)
delivery={'revision':'HairReferenceR5','completed_at':datetime.now().astimezone().isoformat(),'reference':authored['reference'],
 'source_blend':str(R/'Authored/ChapelNun_ReferenceHair_R5.blend'),'groom_source_blend':str(R/'Authored/Nun_ReferenceHair_R5.blend'),
 'assets':saved['assets'],'runtime_head':saved['head'],'material':saved['material'],'native_material_source':saved['native_hair_material'],
 'hair_design':authored['design'],'hair_color':'black','hair_counts':{'core':authored['core_curves'],'loose':authored['loose_curves']},
 'source_hashes':saved['source_hashes'],'surface_revision':'RefinementR4','face_and_outfit_edited':False,
 'runtime_grooms':capture['grooms'],'builds':builds,'inspection':str(R/'inspection.json'),'interactive_gameplay_tested':False}
write(R/'delivery.json',delivery)
main=read(N/'ProductionR1/delivery.json');main['activeHairRevision']='HairReferenceR5';main['hairReferenceDelivery']=str(R/'delivery.json')
main['sourceBlend']=delivery['source_blend'];main['appearance']['hair']='Black off-centre swept waves and compact crossed low bun, matching the approved R2 design; native female hair material and separate simulated wisps'
for key in ['Nun_LowBun_Core','Nun_LowBun_Loose']:
 main['savedAssets'][key]=saved['assets'][key+'_R5'];main['savedAssets'][key+'_Binding']=saved['assets'][key+'_R5_Binding']
main['builds']=builds;main['visualInspection']=str(R/'inspection.json');main['completedAt']=delivery['completed_at']
main['assetSaveLog']=str(N/'ProductionR1/Logs/reference-hair-save-engine.log')
main['visualAcceptance']='Offscreen production NPC idle captures reviewed; interactive church gameplay not run'
write(N/'ProductionR1/delivery.json',main)
print('REFERENCE_HAIR_DELIVERY_RECORDED')
