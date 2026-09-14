import json
from pathlib import Path
P=Path(__file__).resolve().parent;S=P.parent
inv=json.loads((P/'source_paths.json').read_text())
rows=[];aliases={}
def add(key,source,objects,frame='X',**kw):
 rows.append(dict(key=key,source=inv[source]['path'],objects=objects if isinstance(objects,list) else [objects],frame=frame,**kw))
def alias(key,target,reason):aliases[key]={'target':target,'reason':reason}
rig={'rig':'SK_M4_Infima'}
add('optic_false','M4',['SM_M4_RearSight','M4_M4 Body_Export'],'rig',selectors={'M4_M4 Body_Export':{'components':[9,15,19,20,23]}},**rig)
add('magazine_false','M4','M4_Magazine Light.003_Export','rig',**rig)
add('muzzle_false','M4','M4_Flash Hider Unreal_Export','rig',**rig)
add('reargrip_false','M4','M4_Grip Default Unreal_Export','rig',**rig)
add('barrel_false','M4','M4_Handguard Kmode Unreal_Export','rig',selectors={'M4_Handguard Kmode Unreal_Export':{'components':[8]}},**rig)
add('trigger_false','M4','M4_Trigger Straight Unreal_Export','rig',**rig)
for slot,key,ob in [('optic','holographic','M4_holographic'),('optic','panoramic_red_dot','M4_panoramic_red_dot'),('optic','prism_scope_2x','M4_prism_scope_2x'),('optic','lpvo_1_6x',['M4_lpvo_1_6x','M4_lpvo_ring']),('underbarrel','prism_handstop','M4_prism')]:
 add(slot+'_'+key,'attachment_finish',ob,'X',finish='M4',offsets={'M4_lpvo_ring':[-.071,0,.04]} if key=='lpvo_1_6x' else {})
add('magazine_large_drum','attachment_finish','M4_drum','m4_bind',finish='M4')
for key in ['suppressor','brake','titanium_brake']:
 add('muzzle_'+('true' if key=='suppressor' else key),key,'SM_M4_'+key,'Y')
add('muzzle_tactical_suppressor','tactical_game','SM_TacticalSuppressor_M4','Y')
for key,source,ob in [('phantom_reargrip','phantom','SM_PhantomRearGrip'),('balanced_reargrip','balanced','SM_BalancedRearGrip'),('stable_antislip_reargrip','stable','SM_StableAntiSlipRearGrip')]:add('reargrip_'+key,source,ob,'-Y')
add('underbarrel_angled_foregrip','angled','SM_ResonanceGrip','m4_bind')
for key,source,ob in [('vertical_foregrip','vertical','VG_Grip'),('canted_foregrip','canted','CG_GeneratedProfile_Refined')]:
 add('underbarrel_'+key,source,ob,'fit',fit=str(Path(inv[source]['path']).parent/'fit_final.json'))
add('tactical_laser','laser','SM_TacticalDevice','-Y')
add('tactical_flashlight','flashlight','SM_TacticalDevice','-Y')
rows.append({'key':'underbarrel_false','source':'state:empty','objects':[],'frame':'none'})
alias('tactical_false','underbarrel_false','No mounted device; neutral empty-state symbol.')
# Current weapon-specific factory geometry. AKM topology indices are inherited unchanged from its source build.
akcomp=str(S/'AKMSoviet20260911/components.json')
for slot,sel in [('optic',{'components':[3,5,6]}),('reargrip',{'material':['M_AKM_FactoryRearGrip']}),('stock',{'material':['M_AKM_FactoryStock']}),('barrel',{'components':[31]})]:
 add('ue_akm_'+slot+'_false','AKM_current','AKM_Soviet_Native','rig',selectors={'AKM_Soviet_Native':sel},**rig)
add('ue_akm_magazine_false','AKM_current','AKM_FactoryMagazine_Preview','rig',**rig)
alias('ue_akm_muzzle_false','ue_akm_barrel_false','Current AKM has an integral bare barrel muzzle, not an M4 flash hider.')
for slot,ob in [('optic','SM_QBZ191_RearSight'),('magazine','QBZ_Magazine'),('reargrip','QBZ_PistolGrip'),('stock',['QBZ_Stock','QBZ_Part12']),('barrel','QBZ_Part19')]:
 add('ue_qbz191_'+slot+'_false','QBZ_current',ob,'rig',**rig)
add('ue_qbz191_muzzle_false','QBZ_current','QBZ_Part19','rig',selectors={'QBZ_Part19':{'material':['M_QBZ191_Flash_Hider']}},**rig)
for family,source,rig_name,rear,trigger,barrel in [
 ('ue_m1911','M1911','SK_M1911_Manny','M1911_RearSight','M1911_Trigger',['M1911_Barrel_Rebuilt','M1911_ChamberHood','M1911_Bore_ShadowInsert','M1911_ChamberRearShadow']),
 ('ue_dan_wesson715','DW715','SK_DW715_Manny','DW715_RearSight','DW715_DW_Trigger0',['DW715_BarrelShroud','DW715_Muzzle_128','DW715_MuzzleInterior'])]:
 for slot,ob in [('optic',rear),('trigger',trigger),('barrel',barrel)]:add(family+'_'+slot+'_false',source,ob,'root',rig=rig_name)
add('ue_m1911_muzzle_false','M1911',['M1911_MuzzleBushing','M1911_RecoilPlug'],'root',rig='SK_M1911_Manny')
for slot,key,source,ob,frame in [
 ('optic','holographic','pistol_optics','M1911_holographic','X'),
 ('optic','panoramic_red_dot','pistol_red_dot','M1911_panoramic_red_dot','X'),
 ('muzzle','true','pistol_optics','M1911_suppressor','Y'),
 ('muzzle','brake','pistol_brake','M1911_brake','Y'),
 ('muzzle','tactical_suppressor','tactical_game','SM_TacticalSuppressor_M1911','Y'),
 ('tactical','laser','pistol_laser','SM_TacticalDevice','-Y'),
 ('tactical','flashlight','pistol_light','SM_TacticalDevice','-Y')]:add('ue_m1911_'+slot+'_'+key,source,ob,frame)
for slot,key,source,ob,frame in [
 ('optic','holographic','dw_optic','SM_DW715_holographic','X'),
 ('optic','panoramic_red_dot','dw_red_dot','SM_DW715_panoramic_red_dot','X'),
 ('tactical','laser','dw_laser','SM_TacticalDevice','-Y'),
 ('tactical','flashlight','dw_light','SM_TacticalDevice','-Y')]:add('ue_dan_wesson715_'+slot+'_'+key,source,ob,frame)
add('reload_device_dw715_speedloader','DW715',['DW715_LoaderBody','DW715_LoaderKnob']+['DW715_LoaderSocket_'+str(i) for i in range(6)],'root',rig='SK_DW715_Manny')
add('reload_device_false','DW715',['DW715_Case_0','DW715_Projectile_0','DW715_Primer_0'],'root',rig='SK_DW715_Manny')
for row in rows:
 if row['key']=='ue_qbz191_optic_false':
  row['objects'].append('QBZ_Sight_FixedMounts');row['selectors']={'QBZ_Sight_FixedMounts':{'components':[0,2]}}
for family in ['', 'ue_akm_','ue_qbz191_','ue_m1911_','ue_dan_wesson715_']:
 for key in ['short','long']:alias(family+'barrel_'+key,family+'barrel_false','Numeric-only barrel tuning; current runtime barrel has no mesh swap.')
for family,key in [('ue_m1911','m1911_lightweight_fast'),('ue_dan_wesson715','dw715_lightweight_fast')]:
 alias('trigger_'+key,family+'_trigger_false','Numeric-only trigger tuning; use the actual trigger of this weapon.')
for slot,target in {'optic':'optic_false','muzzle':'muzzle_false','magazine':'magazine_false','underbarrel':'underbarrel_vertical_foregrip','barrel':'barrel_false','reargrip':'reargrip_false','stock':'stock_false','trigger':'ue_m1911_trigger_false','tactical':'tactical_laser','reload_device':'reload_device_dw715_speedloader'}.items():
 alias('category_'+slot,target,'Navigation category representative, one actual part and transparent level side view.')
for family in ['ue_akm','ue_qbz191','ue_m1911','ue_dan_wesson715']:
 for slot in ['optic','muzzle','magazine','barrel','reargrip','stock','trigger']:
  target=family+'_'+slot+'_false'
  if any(r['key']==target for r in rows) or target in aliases:alias(family+'_category_'+slot,target,'Weapon-specific factory category representative.')
manifest={'rule':'Actual current model, horizontal orthographic front-left, one attachment assembly, transparent 1024 RGBA; upright parts retain up.',
 'preserve':['stock_false','stock_skeleton','stock_core_stock','stock_qr_performance','stock_tactical_telescopic'],
 'renders':rows,'aliases':aliases,'note':'No gameplay changes or runtime tests. Shared rifle accessory bodies use the actual M4 variant; factory silhouettes and pistol compact adapters use overrides.'}
(P/'render_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('MANIFEST',len(rows),'renders',len(aliases),'explicit aliases')
