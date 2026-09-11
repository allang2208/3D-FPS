import unreal,json
from pathlib import Path
lib=unreal.EditorAssetLibrary
mesh=unreal.load_asset('/Game/Monsters/HandBrain/SK_HandBrain')
before=[s.material_interface.get_path_name() for s in mesh.get_editor_property('materials')]
materials=[]
for i in range(6):
 m=unreal.load_asset('/Game/Monsters/HandBrain/RefinedV04/M_HandBrain_Refined_'+str(i));assert m
 m.set_editor_property('used_with_skeletal_mesh',True)
 unreal.MaterialEditingLibrary.recompile_material(m);assert lib.save_loaded_asset(m,False);materials.append(m)
slots=mesh.get_editor_property('materials')
for i,s in enumerate(slots):s.material_interface=materials[i];slots[i]=s
mesh.set_editor_property('materials',slots);assert lib.save_loaded_asset(mesh,False)
bp=unreal.load_asset('/Game/Monsters/HandBrain/BP_HandBrain');cdo=unreal.get_default_object(bp.generated_class())
report={'disk_materials_before':before,'materials_after':[s.material_interface.get_path_name() for s in mesh.get_editor_property('materials')],'blueprint_override_materials':[str(m) for m in cdo.mesh.get_editor_property('override_materials')],'forced_save':True,'skeletal_usage':True}
Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/material_v04/finalize_report.json').write_text(json.dumps(report,indent=2))
unreal.log('HANDBRAIN_FAB_FINALIZED')
