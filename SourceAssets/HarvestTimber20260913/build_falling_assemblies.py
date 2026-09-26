"""Replace only the cut trunk geometry, retaining the original Nanite leaf assembly."""
import unreal as u,json,os
from pathlib import Path
root=Path(__file__).parent/'FellingCut';dest='/Game/Items/HarvestTimber'
E=u.EditorAssetLibrary;report={}
materials=[u.load_asset(dest+'/MI_CutUpper_Bark'),u.load_asset(dest+'/MI_CutUpper_Foliage'),u.load_asset(dest+'/M_FallingCutEnd')]
materials[2].set_editor_property('used_with_skeletal_mesh',True)
# 上半段以 Nanite 组合叶片渲染，断面材质必须同时带 Nanite 标志，否则游戏里退化成默认材质。
materials[2].set_editor_property('used_with_nanite',True)
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
    # 硬校验（2026-09-26）：过去这里只写报告，A 变体的统计还因为读到受保护属性而中断，
    # 结果倒树是否真的带上 Nanite 组合叶片从未被验证。现在逐项核对，失败也要留下证据。
    assembly=tree.get_editor_property('nanite_settings').get_editor_property('nanite_assembly_data')
    source_assembly=source.get_editor_property('nanite_settings').get_editor_property('nanite_assembly_data')
    parts=len(assembly.get_editor_property('parts'));source_parts=len(source_assembly.get_editor_property('parts'))
    nanite_data=bool(tree.has_valid_nanite_data())
    lods=u.SkeletalMeshEditorSubsystem.get_lod_count(tree)
    slots=[str(s.material_slot_name) for s in tree.materials]
    problems=[]
    if parts!=source_parts:problems.append('assembly_parts %d != source %d'%(parts,source_parts))
    if not nanite_data:problems.append('no valid Nanite data')
    if tree.get_editor_property('skeleton')!=source.get_editor_property('skeleton'):problems.append('skeleton differs')
    if lods<1:problems.append('no LOD')
    for slot in tree.materials:
        material=slot.material_interface
        base=material.get_base_material() if material else None
        if base is None or not base.get_editor_property('used_with_nanite'):
            problems.append('slot %s lacks Nanite usage'%str(slot.material_slot_name))
        elif not base.get_editor_property('used_with_skeletal_mesh'):
            problems.append('slot %s lacks skeletal usage'%str(slot.material_slot_name))
    # 合并写入：以前每轮报告都覆盖整个文件，A 变体的记录因此丢失。
    report=(json.loads((root/'assemblies.json').read_text()) if (root/'assemblies.json').exists() else {})
    report[kind]={'path':tree.get_path_name(),'materials':[s.material_interface.get_path_name() for s in tree.materials],
        'assembly_parts':parts,'source_assembly_parts':source_parts,'nanite_data':nanite_data,
        'lod_count':lods,'slots':slots,'problems':problems}
    (root/'assemblies.json').write_text(json.dumps(report,indent=2,sort_keys=True))
    u.log('CUT_TREE_ASSEMBLY_SAVED '+kind+' parts=%d/%d nanite=%d lods=%d problems=%d'%(parts,source_parts,1 if nanite_data else 0,lods,len(problems)))
    for problem in problems:u.log('CUT_TREE_ASSEMBLY_PROBLEM '+kind+' '+problem)
    if problems:raise RuntimeError('Cut assembly '+kind+' failed verification: '+'; '.join(problems))
u.log('CUT_TREE_ASSEMBLIES_AUTHORED count='+str(len(report)))
