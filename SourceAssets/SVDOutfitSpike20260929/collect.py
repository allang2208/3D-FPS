from pathlib import Path
p=Path('D:/FPS3D/FPSGAME');s=(p/'SourceAssets/ChainmailReloadFit20260929/collect.py').read_text();exec(s.split('manifest={}')[0])
R=p/'SourceAssets/SVDOutfitSpike20260929'
native,profile=next((k,v) for k,v in c['profiles'].items() if v['rig_profile']=='SVD')
paths={'native':native,'bare':profile['native_bare_skin']}
for key,v in c['items'].items():
 for family in ['rig_meshes','skin_meshes']:
  if v.get(family,{}).get('SVD'):paths[key+'_'+family]=v[family]['SVD']
for key,path in paths.items():
 d=extract(path);(R/(key+'.json')).write_text(json.dumps(d,separators=(',',':')));print('SVD_EXTRACT',key,flush=True)
(R/'paths.json').write_text(json.dumps(paths,indent=2))
poses=json.loads((p/'SourceAssets/ChainmailReloadFit20260929/SVD_poses.json').read_text())
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=u.load_asset(native);opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
names=list(d['rest'])
for folder in ['Complete20260923/Animations','Accessories20260923/Animations']:
 for f in (p/'Content/Weapons/SVDDragunov20260922'/folder).rglob('*.uasset'):
  if not f.stem.endswith(('_aim','_idle','_aim_fire')):continue
  path='/Game/'+f.relative_to(p/'Content').with_suffix('').as_posix();clip=u.load_asset(path)
  if not isinstance(clip,u.AnimSequence):continue
  for i in range(11):
   time=clip.get_play_length()*i/10;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
   poses.append(dict(clip=path,time=time,bones={n:tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}))
(R/'poses.json').write_text(json.dumps(poses,separators=(',',':')))
