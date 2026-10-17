"""Read the current user-run cast/body pose without starting or changing play."""
import json
from pathlib import Path
import unreal as u
out=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))/'SourceAssets/WarhammerCastArm20261017/DirectionV2'
out.mkdir(parents=True,exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report={'pie':bool(world),'characters':[]}
def transform(t):
    q=t.rotation;p=t.translation;s=t.scale3d
    return {'position':[p.x,p.y,p.z],'rotation':[q.x,q.y,q.z,q.w],'scale':[s.x,s.y,s.z]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        if 'FPSGAMECharacter' not in actor.get_class().get_name():continue
        row={'actor':actor.get_name(),'transform':transform(actor.get_actor_transform()),'meshes':[]}
        magic=actor.get_component_by_class(u.FPSFireballComponent)
        if magic:row['cast']={'active':magic.is_occupying_left_hand(),'phase':str(magic.get_hand_phase()),'phase_fraction':magic.hand_phase_fraction()}
        for mesh in actor.get_components_by_class(u.SkeletalMeshComponent):
            asset=mesh.get_skeletal_mesh_asset()
            if not asset:continue
            parent=mesh.get_attach_parent()
            data={'component':mesh.get_name(),'class':mesh.get_class().get_name(),'asset':asset.get_path_name(),'visible':mesh.is_visible(),'parent':parent.get_name() if parent else None,'world':transform(mesh.get_world_transform()),'bones':{}}
            for name in ('pelvis','spine_01','spine_03','spine_05','clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twistCor_02_l','lowerarm_correctiveRoot_l','lowerarm_twist_02_l','hand_r'):
                if mesh.get_bone_index(name)>=0:data['bones'][name]=transform(mesh.get_socket_transform(name,u.RelativeTransformSpace.RTS_COMPONENT))
            row['meshes'].append(data)
        report['characters'].append(row)
(out/'current-scene.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HAMMER_CAST_SCENE '+json.dumps({'pie':report['pie'],'characters':len(report['characters']),'casts':[r.get('cast') for r in report['characters']]}),flush=True)
