import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;report={'stocks':{},'animations':{}}
for key in ['skeleton','qr_performance','core_stock','tactical_telescopic']:
 path='/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_'+key;a=u.load_asset(path)
 report['stocks'][key]={'asset':path,'source':list(a.get_editor_property('asset_import_data').extract_filenames()),'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in a.static_materials]}
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
for fam in ['base','drum','vertical','canted','prism','angled']:
 for kind in (['idle','reload','reload_empty','drum_reload','drum_reload_empty'] if fam=='base' else ['idle'] if fam=='drum' else ['idle','reload','reload_empty','drum_reload','drum_reload_empty']):
  path='/Game/Weapons/M16A2/'+('Gameplay20260919/Animations/A_M16_'+kind if fam=='base' and not kind.startswith('drum') else 'UniversalAttachments20260920/Animations/'+fam+'/A_M16_'+fam+'_'+kind)
  a=u.load_asset(path)
  if not a:continue
  row={'asset':path,'source':list(a.get_editor_property('asset_import_data').extract_filenames()),'duration':a.get_play_length(),'samples':[]}
  for t in ([0.] if kind=='idle' else [max(0,a.get_play_length()-dt) for dt in [.35,.25,.15,.1,.05,0]]):
   p=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opts);sample={'t':t,'bones':{}}
   for n in ['WPN_root','hand_l','hand_r']:
    v=u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD);sample['bones'][n]={'p':[v.translation.x,v.translation.y,v.translation.z],'q':[v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w]}
   row['samples'].append(sample)
  report['animations'][fam+'/'+kind]=row
(O/'runtime_sources.json').write_text(json.dumps(report,indent=2));print('M16_RECOVERY_STOCK_SOURCES',len(report['stocks']),len(report['animations']))
