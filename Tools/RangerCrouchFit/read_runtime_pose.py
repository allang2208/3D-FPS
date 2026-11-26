"""Read the user's current pose only; never move, equip, or start/stop play."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021'
data=json.loads((R/'inputs.json').read_text());shirt=json.loads(Path(data['sources']['Jason']['file']).read_text());names=list(shirt['bones'])
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();rows=[]
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        body=actor.mesh;parts=[]
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            asset=c.get_skeletal_mesh_asset()
            if asset and any(k in asset.get_path_name() for k in ('FieldRangerTop','LeatherPants')):parts.append(dict(component=c.get_name(),asset=asset.get_path_name()))
        rows.append(dict(actor=actor.get_path_name(),crouched=actor.get_editor_property('is_crouched'),bones={n:pack(body.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in names},parts=parts))
(R/'runtime_pose.json').write_text(json.dumps(dict(pie=bool(world),rows=rows),indent=2),encoding='utf-8')
print('CURRENT_CROUCH',json.dumps(dict(pie=bool(world),actors=[dict(actor=r['actor'],crouched=r['crouched']) for r in rows])),flush=True)
