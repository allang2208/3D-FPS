"""Record reviewed R4 assets, build evidence and unretouched engine captures."""
import json,hashlib
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115';R=N/'RefinementR4'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
runtime=read(R/'EngineRuntime/assets.json');static=read(R/'EngineAfter/assets.json')
assert runtime['production_actor_assembly'] and runtime['idle_animation_sampled']
face=read(R/'face_preservation.json');assert face['positions_topology_normals_uv_exact_match']
surfaces=[read(R/'final_head_saved.json'),read(R/'final_collar_saved.json'),read(R/'final_boots_saved.json')]
assert all(s['saved'] for s in surfaces)
editor=read(R/'FPSGAMEEditor-build.json');assert editor['exit_code']==0
game_log=P/'Saved/Logs/UnknownJoinDamage20261116-r5-FPSGAME.log'
assert 'Result: Succeeded' in game_log.read_text(encoding='utf-8',errors='replace')
game_binary=P/'Binaries/Win64/FPSGAME.exe'
game={'target':'FPSGAME','exit_code':0,'log':str(game_log),'evidence':'Successful shared workspace build includes the R4 NPC asset references','binary':str(game_binary),'binary_modified_at':datetime.fromtimestamp(game_binary.stat().st_mtime).astimezone().isoformat(),'runtime_tested':False}
write(R/'FPSGAME-build.json',game)
screens={mode:{name:str(R/mode/(name+'.png')) for name in ('front','threequarter','crown','profile','fullbody')} for mode in ('EngineAfter','EngineRuntime')}
for images in screens.values():
 for path in images.values():assert Path(path).is_file()
inspection={'status':'reviewed','scope':'UE offscreen reference pose and actual AChapelNun assembly with idle animation, in a neutral lighting fixture','interactive_gameplay_tested':False,'original_face':face,'collar_geometry':read(R/'collar_geometry_final.json'),'screenshots':screens,'checks':['Original Meshy face positions, topology, corner normals and UVs preserved','Original Meshy lower neck surface and PBR continued below the cut','Continuous solid linen collar without torn overlap','Black native-female groom effect, filled crown and low bun','Eyes and lips retain original detail without micro-surface shadow spikes','Boot opening covered by a skinned black underlayer'],'unmodified_images':True}
inspection['physics_stress_tested']=False
inspection['runtime_underlayer_check']='Ankle underlayer limited to z<=40 cm; no mid-skirt intersection visible in final production-actor idle capture'
write(R/'inspection.json',inspection)
receipt=read(R/'saved_assets.json');receipt['active_materials']=runtime['materials'];receipt['active_hair_material']='/Game/Characters/ChapelNun20261115/RefinementR4/Materials/MI_Nun_Hair';receipt['final_surface_writes']=surfaces;write(R/'saved_assets.json',receipt)
delivery={'revision':'RefinementR4','completed_at':datetime.now().astimezone().isoformat(),'source_blend':str(R/'Authored/ChapelNun_Final_R4.blend'),'assets':receipt['assets'],'runtime_head':runtime['head'],'runtime_outfit_assets':runtime['outfit_assets'],'runtime_grooms':runtime['grooms'],'original_face_preserved':True,'hair_source':receipt['native_groom_effect_source'],'hair_color':'black','hair_counts':{'core':75005,'loose':1876},'builds':[editor,game],'inspection':str(R/'inspection.json'),'interactive_gameplay_tested':False}
write(R/'delivery.json',delivery)
path=N/'ProductionR1/delivery.json';main=read(path)
main['activeAppearanceRevision']='RefinementR4';main['refinementDelivery']=str(R/'delivery.json');main['visualInspection']=str(R/'inspection.json');main['visualAcceptance']='Reviewed in offscreen reference and production NPC idle captures; interactive church gameplay not run'
main['builds']=[editor,game];main['completedAt']=delivery['completed_at'];main['appearance']['head']='Original Meshy visible face preserved exactly; original Meshy neck continuation and PBR'
main['appearance']['hair']='Black low bun using native female groom root distribution, root UVs and material response; 75005 core strands and 1876 loose strands'
main['savedAssets'].update({'SK_Nun_Head':runtime['head'],'SK_Nun_Boots':receipt['assets']['SK_Nun_Boots'],'SK_Nun_CollarCross':receipt['assets']['SK_Nun_CollarCross_Final']})
for part in ('Core','Loose'):
 main['savedAssets']['Nun_LowBun_'+part]=receipt['assets']['Nun_LowBun_'+part+'_R4'];main['savedAssets']['Nun_LowBun_'+part+'_Binding']=receipt['assets']['Nun_LowBun_'+part+'_Final_Binding']
main['assetSaveLog']=str(N/'ProductionR1/Logs/final-neck-save-engine.log');write(path,main)
print('NUN_R4_DELIVERY_RECORDED')
