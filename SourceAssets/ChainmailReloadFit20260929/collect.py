"""Read current garments and firearm reload families without opening the editor UI."""
import json, math, unreal as u
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailReloadFit20260929'
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
roots={
 'M4':['M4TacticalTossFinal','M4SlapImpactFinal','M4DrumDrop/Contact','M4DrumGripRebuilt/Support','ExtMagContact20260919','M4ForegripWristNatural','M4VerticalGripVRENatural/Vertical','M4VREGripExtensions'],
 'AKM':['AKMIntegration/SovietFab/ReloadPolish/base','AKMDrumFreeDrop20260920','AKMIntegration/SovietFab/GripVRENatural','AKMIntegration/SovietFab/GripVREExtensions','AKMIntegration/SovietFab/GripErgonomic','AKMIntegration/SovietFab/Attachments/prism'],
 'QBZ191':['QBZ191/Attachments20260913/Animations'],
 'ASH12':['ASH12/ReloadReference20260919','ASH12/UniversalAttachments20260919/Animations'],
 'M16':['M16A2/Gameplay20260919/Animations','M16A2/UniversalAttachments20260920/Animations'],
 'M1911':['M1911/ReloadReady20260913/Animations'],
 'DW715':['DanWesson715/PalmClearance20260915/Animations','DanWesson715/LeftRecovery20260914/Animations'],
 'A762':['A762/Integrated20260920/Animations','A762/Accessories05/Animations'],
 'SVD':['SVDDragunov20260922/Complete20260923/Animations','SVDDragunov20260922/Accessories20260923/Animations'],
 'PKM':['PKMLowpoly20260922/Animations','PKMLowpoly20260922/Accessories14/Animations'],
 'LMG201':['LMG201/Magazine24/Animations','LMG201/ClothFeed33/Animations']}
for weapon in ['M1911','DW715']:
 for side in ['l','r']:roots[weapon+'_'+side]=['PistolDualWield20260914/'+weapon+'/'+side+('/RevolverReloadFlickV6/Animations' if weapon=='DW715' else '/NaturalAimV3/Animations')]
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
def tr(t):return dict(p=list(t.translation.to_tuple()),q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],s=list(t.scale3d.to_tuple()))
def extract(path):
 mesh=u.load_asset(path)
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
 _,bones=B.get_all_bones_info(dm);bn={b.index:str(b.name) for b in bones}
 _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps)
 _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
 d=dict(source=path,rest={str(b.name):tr(b.world_transform) for b in bones},positions=[[p.x,p.y,p.z] for p in ps],triangles=[[t.x,t.y,t.z] for t in ts],weights=[],materials=[])
 for i in range(len(ps)):
  _,ws,valid=B.get_vertex_bone_weights(dm,i);d['weights'].append({bn[w.bone_index]:w.weight for w in ws if w.weight>0})
 for i in range(len(ts)):d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
 return d
manifest={}
for rig,folders in roots.items():
 native,profile=next((k,v) for k,v in c['profiles'].items() if v['rig_profile']==rig)
 shirt=extract(c['items']['ue_chainmail_shirt']['rig_meshes'][rig]);skin=extract(profile['native_bare_skin'])
 (R/(rig+'_shirt.json')).write_text(json.dumps(shirt,separators=(',',':')));(R/(rig+'_skin.json')).write_text(json.dumps(skin,separators=(',',':')))
 clips=[]
 for folder in folders:
  disk=P/'Content/Weapons'/folder
  for file in sorted(disk.rglob('*.uasset')):
   name=file.stem
   if not name.startswith('A_') or not any(x in name.lower() for x in ['reload','single_','speed_']):continue
   if rig=='DW715' and 'LeftRecovery' in folder and ('single_0_' in name or 'speed_' in name):continue
   path='/Game/'+file.relative_to(P/'Content').with_suffix('').as_posix()
   clip=u.load_asset(path)
   if not isinstance(clip,u.AnimSequence):continue
   clips.append((path,clip))
 if not clips:raise RuntimeError('No reloads '+rig)
 names=sorted(set(n for d in [shirt,skin] for w in d['weights'] for n in w))
 poses=[];opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=u.load_asset(native);opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
 for path,clip in clips:
  duration=clip.get_play_length();count=max(2,math.ceil(duration*10)+1)
  for i in range(count):
   time=duration*i/(count-1);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
   poses.append(dict(clip=path,time=time,bones={n:tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}))
 (R/(rig+'_poses.json')).write_text(json.dumps(poses,separators=(',',':')))
 manifest[rig]=dict(native=native,shirt=shirt['source'],skin=skin['source'],clips=[p for p,a in clips],samples=len(poses))
 (R/'sources.json').write_text(json.dumps(manifest,indent=2));print('CHAINMAIL_COLLECT',rig,len(clips),len(poses),flush=True)
