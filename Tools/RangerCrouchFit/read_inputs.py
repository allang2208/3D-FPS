"""Read the equipped waist layers and authored crouch poses, without changing play."""
import hashlib,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021';R.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])
cfg=read(P/'Content/ColdSteelData/modular_outfits.json');body=read(P/'Content/ColdSteelData/player_body.json')
recipe={k:cfg['items'][k] for k in ('ue_field_sweater','ue_leather_pants')}
files={p:P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021/Authored/ue_field_sweater'/(p+'.json') for p in ('Jason','Owner_Jason','Body')}
sources={p:dict(file=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for p,f in files.items()}
shirt=read(files['Jason']);names=sorted(set().union(*shirt['weights']))
assets={}
paths=[recipe['ue_field_sweater']['rig_meshes'][p] for p in ('Jason','Body')]+list(recipe['ue_field_sweater']['owner_body_meshes'].values())+list(recipe['ue_leather_pants']['rig_meshes'].values())
for row in recipe['ue_leather_pants'].get('shoe_fit_meshes',{}).values():paths+=list(row.values())
for path in dict.fromkeys(paths):
    asset=u.load_asset(path)
    assets[path]=dict(skeleton=asset.skeleton.get_path_name(),materials=[m.material_interface.get_path_name() if m.material_interface else None for m in asset.materials],slots=[str(m.material_slot_name) for m in asset.materials],garment_sha=u.EditorAssetLibrary.get_metadata_tag(asset,'GarmentSleeveSHA'),trouser_sha=u.EditorAssetLibrary.get_metadata_tag(asset,'ST6SourceSHA'))
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();runtime=[]
if world:
    for pawn in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        components=[]
        for c in pawn.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.get_skeletal_mesh_asset()
            if not mesh:continue
            path=mesh.get_path_name()
            if not any(v in path for v in ('FieldRangerTop','LeatherPants','Jason_Base','JasonPlayer')):continue
            leader=c.get_editor_property('leader_pose_component')
            components.append(dict(component=c.get_name(),asset=path,leader=leader.get_name() if leader else None,visible=c.is_visible(),owner_no_see=c.get_editor_property('owner_no_see'),world_transform=pack(c.get_world_transform()),bones={n:pack(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in names if c.get_bone_index(n)>=0}))
        runtime.append(dict(pawn=pawn.get_path_name(),crouched=pawn.get_editor_property('is_crouched'),components=components))
mesh=u.load_asset(body['body_mesh']);options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
clips={}
for key,path in body['clips'].items():
    if not key.startswith('Crouch.'):continue
    clip=u.load_asset(path);samples=[]
    for fraction in (0.,.25,.5,.75):
        time=clip.get_play_length()*fraction;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,options)
        samples.append(dict(time=time,bones={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}))
    clips[key]=dict(asset=path,samples=samples)
report=dict(read_only=True,pie=bool(world),recipe=recipe,sources=sources,assets=assets,runtime=runtime,clips=clips,body_mesh=body['body_mesh'])
(R/'inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('RANGER_CROUCH_INPUTS',json.dumps(dict(pie=bool(world),clips=len(clips),bones=len(names),runtime=[dict(crouched=r['crouched'],components=[{k:c[k] for k in ('component','asset','leader')} for c in r['components']]) for r in runtime],assets=assets),ensure_ascii=False),flush=True)
