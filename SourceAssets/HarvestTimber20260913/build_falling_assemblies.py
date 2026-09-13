"""Replace only the cut trunk geometry, retaining the original Nanite leaf assembly."""
import unreal as u,json,os
from pathlib import Path
root=Path(__file__).parent/'FellingCut';dest='/Game/Items/HarvestTimber'
E=u.EditorAssetLibrary;report={}
materials=[u.load_asset(dest+'/MI_CutUpper_Bark'),u.load_asset(dest+'/MI_CutUpper_Foliage'),u.load_asset(dest+'/M_FallingCutEnd')]
materials[2].set_editor_property('used_with_skeletal_mesh',True)
u.MaterialEditingLibrary.recompile_material(materials[2])
if not E.save_loaded_asset(materials[2],False):raise RuntimeError('Cannot save cut-surface material')
for kind in os.environ.get('TREE_CUT_AUTHOR_VARIANTS','ABCD'):
    source=u.load_asset('/Game/WorldGeneration/TemperateHills/SK_BlackPoplarPCG_'+kind)
    target=dest+'/SK_CutUpper_'+kind
    tree=u.load_asset(target) or E.duplicate_asset(source.get_path_name(),target)
    trunk=u.load_asset(dest+'/SM_CutUpper_'+kind)
    read=u.GeometryScriptMeshReadLOD();read.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    dynamic,result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(trunk,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read)
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read cut trunk '+kind)
    slots=trunk.static_materials
    for i in range(len(slots)):u.GeometryScript_Materials.remap_material_i_ds(dynamic,i,100+i)
    for i,slot in enumerate(slots):
        label=str(slot.material_slot_name)
        index=2 if 'CutEndGrain' in label else 1 if 'Foliage' in label else 0
        u.GeometryScript_Materials.remap_material_i_ds(dynamic,100+i,index)
    options=u.GeometryScriptCopyMeshToAssetOptions();options.replace_materials=True
    options.new_materials=materials
    options.new_material_slot_names=[s.material_slot_name for s in source.materials]+[u.Name('CutEndGrain')]
    options.bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON
    # Preserve the source assembly nodes, bone references and material remaps.
    options.apply_nanite_settings=True;options.new_nanite_settings=source.get_editor_property('nanite_settings')
    _,result=u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dynamic,tree,options,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author cut assembly '+kind)
    if not E.save_loaded_asset(tree,False):raise RuntimeError('Cannot save cut assembly '+kind)
    assembly=tree.get_editor_property('nanite_settings').get_editor_property('nanite_assembly_data')
    report[kind]={'path':tree.get_path_name(),'materials':[s.material_interface.get_path_name() for s in tree.materials],
        'assembly_parts':len(assembly.get_editor_property('parts'))}
    (root/'assemblies.json').write_text(json.dumps(report,indent=2))
    u.log('CUT_TREE_ASSEMBLY_SAVED '+kind)
u.log('CUT_TREE_ASSEMBLIES_AUTHORED count='+str(len(report)))
