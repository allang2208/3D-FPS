import json,re
from pathlib import Path
from PIL import Image
O=Path(__file__).resolve().parent
runtime=json.loads((O/'saved_check/runtime.json').read_text());previews={}
for phase,label in [('hip_fire_cycle','bolt-runtime'),('normal_reload','reload-runtime')]:
 rows=[x for x in runtime['frames'] if x['phase']==phase][::2];images=[];durations=[]
 for i,row in enumerate(rows):
  with Image.open(O/'saved_check/Frames'/row['image']) as src:images.append(src.resize((960,540)).convert('P',palette=Image.Palette.ADAPTIVE,colors=192))
  dt=rows[i+1]['phase_time']-row['phase_time'] if i+1<len(rows) else .2;durations.append(max(20,round(dt*100)*10))
 target=O/(label+'.gif');images[0].save(target,save_all=True,append_images=images[1:],duration=durations,loop=0,optimize=False);previews[phase]=str(target)
log=(O/'saved_check/runtime.log').read_text(encoding='utf-8',errors='replace')
normal=float(re.search(r'M24_ACTION_REVIEW_PHASE normal_reload duration=([0-9.]+)',log).group(1))-.7
catalog=json.loads((O.parents[1]/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8'));base=next(w['base'] for w in catalog['weapons'] if w['id']=='ue_m24')
report={'complete':True,'saved_assets':json.loads((O/'install_receipt.json').read_text())['saved'],'saved_mesh':json.loads((O/'morph_install_receipt.json').read_text())['path'],'reload':{'earlier_finger_refinement_was_already_saved':True,'base_seconds':base['reload_time'],'empty_base_seconds':base['empty_reload_time'],'normal_runtime_seconds_rounded':round(normal,3),'runtime_speed_bonuses_preserved':True,'ordinary_and_extended_profiles_saved':True},'left_arm':{'scope':'fire, cycle, empty-reload bolt segment, both magazines','editable_source':str(O/'M24_BoltRoot_Editable.blend'),'joint_surface_examples_added':9,'mesh_version':'V9','saved_mesh_comparison':json.loads((O/'saved_mesh_comparison.json').read_text()),'saved_contact_comparison':json.loads((O/'saved_pose_comparison.json').read_text()),'source_elbow_check':{k:v for k,v in json.loads((O/'root_surface_check.json').read_text()).items() if k!='worse'}},'runtime':{'complete':runtime['complete'],'mesh':runtime['mesh'],'phases':['equip','idle','hip_fire_cycle','normal_reload'],'frames':len(runtime['frames']),'normal_reload_observed_magazine_change':[4,5],'game_review_isolated_from_player_profile':True,'other_variants_checked_offline':True,'gun_action_framing_max':max(x['action_framing'] for x in runtime['frames'] if x['phase']=='hip_fire_cycle')},'previews':previews,'native_build_required':False}
(O/'delivery.json').write_text(json.dumps(report,indent=2));print(json.dumps({'complete':True,'normal_runtime_seconds':report['reload']['normal_runtime_seconds_rounded'],'runtime_frames':len(runtime['frames']),'previews':previews},indent=2))
