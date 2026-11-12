"""Author beech-only harvest assets from matched source sections, without a map.

Standing trees, their Fab originals and the existing poplar family are not saved.
Run after export_sources.py and the background Blender cut_tree_sections.py.
"""
import json, shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).parent
PROJECT=ROOT.parent.parent
DEST='/Game/Items/HarvestTimber/Beech'
FOREST='/Game/WorldGeneration/TemperateHills/ForestSpecies20261110'
TIMBER='/Game/Items/HarvestTimber'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
REPORT={'saved':[],'trees':{},'map_modified':False,'game_run':False,'visual_tested':False}

def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Missing asset: '+path)
    return obj

def backup(path):
    rel=path.split('.')[0].removeprefix('/Game/')
    for ext in ('.uasset','.uexp','.ubulk'):
        src=PROJECT/'Content'/(rel+ext);dst=ROOT/'Backups/Content'/(rel+ext)
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())
    (ROOT/'Receipts/beech-saved.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    return obj

def duplicate(source,name):
    path=DEST+'/'+name;backup(path)
    obj=u.load_asset(path) or E.duplicate_asset(source,path)
    if not obj:raise RuntimeError('Cannot duplicate '+name)
    return obj

def node(mat,cls,**props):
    obj=L.create_material_expression(mat,cls)
    obj.set_editor_property('desc','BeechHarvest20261110')
    for key,value in props.items():obj.set_editor_property(key,value)
    return obj

def wire(source,target,pin='',output=''):
    if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Cannot connect '+pin)

def master_material():
    mat=duplicate(FOREST+'/Materials/M_ForestPCG','M_FallingBeech')
    prop=u.MaterialProperty.MP_MATERIAL_ATTRIBUTES
    original=L.get_material_property_input_node(mat,prop)
    output=L.get_material_property_input_node_output_name(mat,prop)
    # Reruns update this task's wrapper, preserving the imported PVE shader.
    if original.get_editor_property('desc')=='BeechHarvest20261110':
        wrapper=original;original=L.get_inputs_for_material_expression(mat,wrapper)[0]
        result=L.get_input_node_output_name_for_material_expression(wrapper,original)
        output=result if isinstance(result,str) else result[-1] if result else ''
    for n in list(L.get_material_expressions(mat)):
        if n.get_editor_property('desc')=='BeechHarvest20261110':L.delete_material_expression(mat,n)
    get=node(mat,u.MaterialExpressionGetMaterialAttributes)
    mask_index=u.TemperateForestAuthoringLibrary.add_visibility_mask_pin(get)
    wire(original,get,L.get_material_expression_input_names(get)[0],output)
    mask_output=L.get_material_expression_output_names(get)[mask_index]
    world=node(mat,u.MaterialExpressionWorldPosition,
        world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    local=node(mat,u.MaterialExpressionTransformPosition,
        transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
        transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(world,local)
    z=node(mat,u.MaterialExpressionComponentMask,r=False,g=False,b=True,a=False);wire(local,z)
    height=node(mat,u.MaterialExpressionScalarParameter,parameter_name='HarvestCutHeight',default_value=42)
    zero=node(mat,u.MaterialExpressionConstant,r=0);one=node(mat,u.MaterialExpressionConstant,r=1)
    cut=node(mat,u.MaterialExpressionIf)
    cut_pins=L.get_material_expression_input_names(cut)
    wire(z,cut,cut_pins[0]);wire(height,cut,cut_pins[1])
    wire(one,cut,cut_pins[2]);wire(one,cut,cut_pins[3]);wire(zero,cut,cut_pins[4])
    geometric=node(mat,u.MaterialExpressionScalarParameter,parameter_name='HarvestGeometricCut',default_value=1)
    select=node(mat,u.MaterialExpressionLinearInterpolate)
    wire(cut,select,'A');wire(one,select,'B');wire(geometric,select,'Alpha')
    fade=node(mat,u.MaterialExpressionScalarParameter,parameter_name='HarvestFade',default_value=1)
    dither=node(mat,u.MaterialExpressionMaterialFunctionCall,
        material_function=load('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
    wire(fade,dither,L.get_material_expression_input_names(dither)[0])
    fadecut=node(mat,u.MaterialExpressionMultiply);wire(select,fadecut,'A');wire(dither,fadecut,'B')
    mask=node(mat,u.MaterialExpressionMultiply);wire(get,mask,'A',mask_output);wire(fadecut,mask,'B')
    put=node(mat,u.MaterialExpressionSetMaterialAttributes)
    put_index=u.TemperateForestAuthoringLibrary.add_visibility_mask_pin(put)
    pins=L.get_material_expression_input_names(put)
    wire(original,put,pins[0],output);wire(mask,put,pins[put_index])
    if not L.connect_material_property(put,'',prop):raise RuntimeError('Cannot connect beech attributes')
    mat.set_editor_property('used_with_nanite',True)
    mat.set_editor_property('used_with_skeletal_mesh',True)
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    L.recompile_material(mat);save(mat)
    return mat

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Do not author during PIE')
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
    if dirty:raise RuntimeError('Preserve unsaved beech harvest packages: '+repr(dirty))
    master=master_material()
    # Instance duplication retains all leaf masks, packed textures, switches and colour controls.
    falling=[];stump=[]
    stump_master=duplicate(FOREST+'/Materials/M_ForestPCG','M_StumpBeech')
    stump_master.set_editor_property('used_with_instanced_static_meshes',True)
    L.recompile_material(stump_master);save(stump_master)
    for part in ('Bark','Foliage'):
        src=FOREST+'/Materials/MI_European_Beech_'+part+'_01'
        mi=duplicate(src,'MI_FallingBeech_'+part);L.set_material_instance_parent(mi,master)
        L.update_material_instance(mi);falling.append(save(mi))
        mi=duplicate(src,'MI_StumpBeech_'+part);L.set_material_instance_parent(mi,stump_master)
        L.update_material_instance(mi);stump.append(save(mi))
    # Existing end-grain look, with dedicated beech assets and complete usage flags.
    end=duplicate(TIMBER+'/M_TreeCutSurface','M_BeechCutSurface')
    end.set_editor_property('used_with_instanced_static_meshes',True);L.recompile_material(end);save(end)
    fallend=duplicate(TIMBER+'/M_FallingCutEnd','M_BeechFallingCutEnd')
    fallend.set_editor_property('used_with_skeletal_mesh',True)
    fallend.set_editor_property('used_with_nanite',True)
    L.recompile_material(fallend);save(fallend)
    authored=json.loads((ROOT/'FellingCut/Delivery/authoring.json').read_text())
    read=u.GeometryScriptMeshReadLOD();read.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    for kind in 'ABCD':
        source=load(FOREST+'/Meshes/SK_Beech_'+kind)
        for upper in (False,True):
            name=('SM_CutUpper_' if upper else 'SM_CutStump_')+kind
            backup(DEST+'/'+name)
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
            opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
            opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.generate_lightmap_u_vs=False
            task=u.AssetImportTask();task.filename=str(ROOT/'FellingCut/Delivery'/(name+'.fbx'))
            task.destination_path=DEST;task.destination_name=name;task.options=opt
            task.automated=True;task.replace_existing=True;task.save=False
            A.import_asset_tasks([task]);mesh=load(DEST+'/'+name)
            slots=list(mesh.static_materials)
            for i,slot in enumerate(slots):
                label=str(slot.material_slot_name)
                slot.material_interface=(fallend if upper else end) if 'CutEndGrain' in label else (falling if upper else stump)[1 if 'Foliage' in label else 0]
                slots[i]=slot
            mesh.set_editor_property('static_materials',slots);save(mesh)
            dynamic,result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read)
            if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+name)
            if not upper:
                _,positions,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dynamic,True)
                vectors=u.GeometryScript_List.convert_vector_list_to_array(positions)
                unique={(round(p.x,4),round(p.y,4)) for p in vectors if abs(p.z-42)<.01}
                if len(unique)<3:raise RuntimeError('Missing cut rim '+name)
                cls=u.load_class(None,'/Script/FPSGAME.ProductionTreeCutProfile')
                factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',cls)
                profile_name='DA_TreeCut_'+kind;backup(DEST+'/'+profile_name)
                profile=u.load_asset(DEST+'/'+profile_name) or A.create_asset(profile_name,DEST,u.DataAsset,factory)
                profile.set_editor_property('rim',[u.Vector2D(x,y) for x,y in sorted(unique)]);save(profile)
                continue
            # Retain the original bone hierarchy, Nanite assembly nodes and material maps.
            for i in range(len(slots)):u.GeometryScript_Materials.remap_material_i_ds(dynamic,i,100+i)
            for i,slot in enumerate(slots):
                label=str(slot.material_slot_name)
                u.GeometryScript_Materials.remap_material_i_ds(dynamic,100+i,2 if 'CutEndGrain' in label else 1 if 'Foliage' in label else 0)
            tree=duplicate(source.get_path_name(),'SK_CutUpper_'+kind)
            options=u.GeometryScriptCopyMeshToAssetOptions();options.replace_materials=True
            options.new_materials=falling+[fallend]
            options.new_material_slot_names=[s.material_slot_name for s in source.materials]+[u.Name('CutEndGrain')]
            options.bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON
            options.apply_nanite_settings=True;options.new_nanite_settings=source.get_editor_property('nanite_settings')
            _,result=u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dynamic,tree,options,u.GeometryScriptMeshWriteLOD())
            if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author cut assembly '+kind)
            save(tree)
            # The source-mesh fallback shares exactly this cut surface, at the same local origin.
            for index in (0,1):u.GeometryScript_Materials.delete_triangles_by_material_id(dynamic,index,True)
            u.GeometryScript_Materials.remap_material_i_ds(dynamic,2,0)
            cap_name='SM_CutCap_'+kind;cap_path=DEST+'/'+cap_name;backup(cap_path)
            cap=u.load_asset(cap_path)
            if cap is None:
                create=u.GeometryScriptCreateNewStaticMeshAssetOptions();create.enable_collision=False
                cap,result=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,cap_path,create)
                if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create cut cap '+kind)
            write=u.GeometryScriptCopyMeshToAssetOptions();write.replace_materials=True
            write.new_materials=[fallend];write.new_material_slot_names=[u.Name('CutEndGrain')]
            _,result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,cap,write,u.GeometryScriptMeshWriteLOD())
            if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write cut cap '+kind)
            save(cap)
            REPORT['trees'][kind]={'source':source.get_path_name(),'falling':tree.get_path_name(),
                'stump':DEST+'/SM_CutStump_'+kind,'cut_height_cm':42,'geometry':authored['SM_CutStump_'+kind]}
    REPORT['finished_at']=datetime.now().astimezone().isoformat()
    (ROOT/'Receipts/beech-saved.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    u.log('BEECH_HARVEST_ASSETS_SAVED count='+str(len(REPORT['saved'])))

if __name__=='__main__':main()
