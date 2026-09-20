import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;out={}
paths={'m4_reload':'/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload','m4_empty':'/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload_empty','m4_melee':'/Game/Weapons/M4QuickMeleeReplica20260919/Base/A_M4_QuickCombat_Base','qbz_melee':'/Game/Weapons/RifleQuickMelee20260919/QBZ191/Base/A_QBZ191_QuickCombat_Base','m16_melee':'/Game/Weapons/M16A2/Gameplay20260919/Animations/A_M16_quick_melee'}
for fam in ['base','vertical','canted','prism','angled','drum']:
 for clip in (['reload','reload_empty'] if fam=='base' else ['QuickCombat']+(['reload','reload_empty'] if fam!='drum' else [])):
  paths[f'm16_{fam}_{clip}']='/Game/Weapons/M16A2/'+('Gameplay20260919/Animations/A_M16_'+clip if fam=='base' else 'UniversalAttachments20260920/Animations/'+fam+'/A_M16_'+fam+'_'+clip)
for k,path in paths.items():
 a=u.load_asset(path);out[k]={'asset':path,'source':list(a.get_editor_property('asset_import_data').extract_filenames()),'duration':a.get_play_length()}
(O/'runtime_sources.json').write_text(json.dumps(out,indent=2));print('M16_REMOVAL_MELEE_SOURCES',len(out))
