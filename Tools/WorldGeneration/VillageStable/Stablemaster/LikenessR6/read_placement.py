"""Read the saved instance and its concrete meshes and materials."""
import unreal as u
import os,json
from pathlib import Path
out=Path(os.environ['STABLEMASTER_WORK'])
mapname='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
# The streamed village's async mesh builds otherwise race commandlet shutdown in UE 5.8.
u.SystemLibrary.execute_console_command(None,'Editor.AsyncStaticMeshCompilation 0')
world=u.EditorLoadingAndSavingUtils.load_map(mapname)
sub=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
target,=[a for a in sub.get_all_level_actors() if a.get_actor_label()=='Village_Stable_Stablemaster']
def path(obj):return obj.get_path_name() if obj else None
def item(c):
    mesh=c.skeletal_mesh_asset
    tr=c.get_world_transform()
    return dict(name=c.get_name(),mesh=path(mesh),parent=path(c.get_attach_parent()),materials=[path(c.get_material(i)) for i in range(c.get_num_materials())],relative=str(c.relative_location),scale=str(c.relative_scale3d),world=str(tr),skeleton=path(mesh.skeleton) if mesh else None,bones={n:list(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT).translation.to_tuple()) for n in ('LeftArm','RightArm','Head','Neck','LeftFoot','LeftToeBase')},lod=int(c.get_predicted_lod_level()) if hasattr(c,'get_predicted_lod_level') else None)
components=target.get_components_by_class(u.SkeletalMeshComponent)
report=dict(actor=target.get_path_name(),actor_class=path(target.get_class()),parts=[item(c) for c in components])
(out/('map-'+os.environ['STABLEMASTER_STAGE']+'.json')).write_text(json.dumps(report,indent=2))
