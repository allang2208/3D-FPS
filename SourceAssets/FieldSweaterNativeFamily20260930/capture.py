"""Freeze active sleeve bindings and native arm sources for the family rebuild."""
import sys,shutil
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import garment_ue as g
c=g.read(P/'Content/ColdSteelData/modular_outfits.json');item=c['items']['ue_field_sweater']
g.write(R/'before.json',dict(recipe=item))
for profile,path in item['rig_meshes'].items():
 if profile=='Body':continue
 rows=[(k,v) for k,v in c['profiles'].items() if v['rig_profile']==profile]
 native,row=rows[-1] if profile=='Bow' else rows[0]
 skinpath=row['native_bare_skin'];folder=R/'Before'/profile
 paths=dict(shirt=path,native=native,skin=skinpath,shirt_sha256=g.digest(g.asset_file(path)),skin_sha256=g.digest(g.asset_file(skinpath)),aliases=[k for k,_ in rows])
 cached=P/'SourceAssets/FieldSweaterCameraRepair20260930/Before'/profile
 old=g.read(cached/'paths.json')
 if old['skin']==skinpath and old['skin_sha256']==paths['skin_sha256']:
  folder.mkdir(parents=True,exist_ok=True);shutil.copyfile(cached/'skin.json',folder/'skin.json')
 else:g.write(folder/'skin.json',g.source_snapshot(u.load_asset(skinpath))[1])
 g.write(folder/'paths.json',paths)
 print('NATIVE_SOURCE',profile,skinpath,flush=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();live=dict(playing=bool(world),components=[])
if world:
 pawn=u.GameplayStatics.get_player_pawn(world,0)
 if pawn:
  for comp in pawn.get_components_by_class(u.SkeletalMeshComponent):
   asset=comp.get_skinned_asset()
   if not asset or not comp.is_visible():continue
   leader=comp.get_editor_property('leader_pose_component')
   live['components'].append(dict(name=comp.get_name(),asset=asset.get_path_name(),leader=leader.get_name() if leader else None,lod=comp.get_predicted_lod_level(),transform=g.transform(comp.get_world_transform()),bones={str(comp.get_bone_name(i)):g.transform(comp.get_socket_transform(comp.get_bone_name(i),u.RelativeTransformSpace.RTS_COMPONENT)) for i in range(comp.get_num_bones())}))
g.write(R/'live.json',live)
print('NATIVE_CAPTURE_COMPLETE',len(item['rig_meshes'])-1,'playing',live['playing'],flush=True)
