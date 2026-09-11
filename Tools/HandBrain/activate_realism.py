import unreal,json
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/realism_v05');lib=unreal.EditorAssetLibrary
mesh=unreal.load_asset('/Game/Monsters/HandBrain/RealismV05/SK_HandBrain_Realism');clip=unreal.load_asset('/Game/Monsters/HandBrain/RealismV05/A_HandBrain_Howl_Realism');assert mesh and clip
assert all('/RealismV05/' in s.material_interface.get_path_name() for s in mesh.get_editor_property('materials'))
bp=unreal.load_asset('/Game/Monsters/HandBrain/BP_HandBrain');cdo=unreal.get_default_object(bp.generated_class())
report={'previous_mesh':cdo.get_editor_property('visual_mesh').get_path_name(),'previous_howl':cdo.get_editor_property('howl_clip').get_path_name()}
cdo.set_editor_property('visual_mesh',mesh);cdo.mesh.set_skeletal_mesh_asset(mesh);cdo.set_editor_property('howl_clip',clip)
assert lib.save_loaded_asset(bp,False)
report.update({'mesh':mesh.get_path_name(),'howl':clip.get_path_name(),'remaining_clips':{n:cdo.get_editor_property(n).get_path_name() for n in ['idle_clip','move_clip','slam_clip','death_clip']}})
(r/'activation.json').write_text(json.dumps(report,indent=2))
unreal.log('HANDBRAIN_REALISM_ACTIVATED')
