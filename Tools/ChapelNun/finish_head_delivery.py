import json
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/HeadQualityR2'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'saved_assets.json');capture=read(R/'EngineAfter/assets.json')
builds=[read(R/(name+'-build.json')) for name in ['FPSGAMEEditor','FPSGAME']]
active={
 'SK_Nun_Head':saved['assets']['SK_Nun_Head_R2_Final'],
 'Nun_LowBun_Core':saved['assets']['Nun_LowBun_Core_R2'],
 'Nun_LowBun_Core_Binding':saved['assets']['Nun_LowBun_Core_R2_Final_Binding'],
 'Nun_LowBun_Loose':saved['assets']['Nun_LowBun_Loose_R2'],
 'Nun_LowBun_Loose_Binding':saved['assets']['Nun_LowBun_Loose_R2_Final_Binding']}
report={
 'revision':'HeadQualityR2','completedAt':datetime.now().astimezone().isoformat(),
 'status':'assets_saved_runtime_references_integrated_both_targets_built',
 'scope':'Chapel nun crown coverage, facial geometry and imported shading',
 'findings':[
  'Original radial groom exposed the crown and swept strands across the forehead and face.',
  'Island-wise face-normal recalculation reversed source triangles; single-sided Unreal rendering exposed holes.',
  'Eye surfaces needed separate smooth wet shading with restrained subsurface response. Lit, unlit, no-hair and normal diagnostics distinguished this from missing geometry.'
 ],
 'repairs':{
  'face':read(R/'Authored/orientation_repair.json'),
  'hair':'52,000 scalp-constrained core strands and 1,600 loose strands; feathered fitted scalp foundation; natural black low bun',
  'materials':'Original 4K face base/normal textures retained. Separate skin, native neck, eye, lip and scalp materials. Smooth eye normals, roughness 0.22 and restrained subsurface shading; lip roughness 0.44.',
  'lod':'Full authored LOD0 with face-specific 0.70 and 0.42 reduction levels; bindings rebuilt against the corrected final mesh.',
  'preserved':'Native female skeleton/neck, black robe, loose-hair physics, bounds fix and altar-facing placement'
 },
 'activeAssets':active,'materialAssets':saved['materials'],
 'sourceBlend':str(R/'Authored/ChapelNun_Complete_R2.blend'),
 'headSourceBlend':str(R/'Authored/Nun_Head_Hair_R2.blend'),
 'assetSaveLog':str(P/'SourceAssets/ChapelNun20261115/ProductionR1/Logs/head-quality-final-engine.log'),
 'finalEyeMaterialSaveLog':str(P/'SourceAssets/ChapelNun20261115/ProductionR1/Logs/eye-surface-scatter-engine.log'),
 'builds':builds,
 'targetedInspection':{
  'method':'Unreal offscreen asset capture, reference pose, no BeginPlay or gameplay profile',
  'views':['front','threequarter','crown'],
  'observed':'Continuous crown coverage and visible groom strands; repaired facial holes; iris, sclera and highlights visible after eye material refinement.',
  'capture':capture,
  'images':[str(R/'EngineAfter'/(v+'.png')) for v in ['front','threequarter','crown']],
  'gameplayStarted':False,'motionOrSceneAcceptance':False
 },
 'unrelatedCompileBlocker':'Renamed a local cache-size constant in ColdSteelItemReadCache.h to avoid a unity-build name-shadowing error; capacity and behavior remain the same.',
 'runtimeTested':False
}
(R/'repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
parent=P/'SourceAssets/ChapelNun20261115/ProductionR1/delivery.json';d=read(parent)
d['activeAppearanceRevision']='HeadQualityR2';d['headQualityRepair']=str(R/'repair.json');d['sourceBlend']=report['sourceBlend'];d['savedAssets'].update(active);d['builds']=builds
d['appearance']['head']='Corrected source winding and normals, fitted native female neck, separate skin/eye/lip shading'
d['appearance']['hair']='Natural black low bun, continuous scalp coverage, 52,000 core strands and 1,600 independently simulated loose strands'
d['visualAcceptance']='Requested offscreen asset inspection completed in front, three-quarter and crown views; gameplay acceptance pending'
d['targetedHeadBoundsCheck']='Previous FaceHairFixR1 bounds repair retained; current component bounds recorded in HeadQualityR2/EngineAfter/assets.json'
d['completedAt']=report['completedAt'];parent.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HEAD_QUALITY_DELIVERED',report['status'],[b['exit_code'] for b in builds])
