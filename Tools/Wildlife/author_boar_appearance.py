"""Build the boar-only skin and route both the wildlife animation set and character to it."""
from pathlib import Path
import runpy
import unreal as u

folder='/Game/Monsters/Wildlife/Pig'
looks=folder+'/Appearance'
pack='/Game/AnimalVarietyPack/Pig'
skin=looks+'/SK_WL_Boar'
bristles=looks+'/M_BoarBristles'
ivory=looks+'/M_BoarIvory'
actor=folder+'/BP_WL_Pig'
dataset=folder+'/DA_WL_Pig_AnimationSet'
library=u.EditorAssetLibrary
materials=u.MaterialEditingLibrary


def save(obj):
    if not library.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())


def import_texture(name, masked=False):
    task = u.AssetImportTask()
    task.filename = str(Path(__file__).resolve().parents[2] / 'SourceAssets/Wildlife/Boar' / (name+'.tga'))
    task.destination_path = looks
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Could not import '+task.filename)
    texture = u.load_asset(task.imported_object_paths[0])
    texture.set_editor_property('srgb', True)
    if masked:
        texture.set_editor_property('do_scale_mips_for_alpha_coverage', True)
        texture.set_editor_property('alpha_coverage_thresholds', u.Vector4(0,0,0,.33))
        texture.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
    save(texture)
    return texture


def coat_material(source_name, target_name, texture):
    target = looks+'/'+target_name
    mat = u.load_asset(target) if library.does_asset_exist(target) else library.duplicate_asset(
        pack+'/Materials/'+source_name,target)
    sample = materials.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
    if not isinstance(sample,u.MaterialExpressionTextureSample):
        raise RuntimeError('Missing coat texture input on '+target)
    mat.modify()
    sample.modify()
    sample.set_editor_property('texture',texture)
    errors = list(materials.recompile_material(mat))
    if errors:
        raise RuntimeError(str(errors))
    save(mat)
    return mat


def create_mane_material(texture):
    mat=u.load_asset(bristles) if library.does_asset_exist(bristles) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_BoarBristles',looks,u.Material,u.MaterialFactoryNew())
    mat.modify()
    materials.delete_all_material_expressions(mat)
    mat.set_editor_property('used_with_skeletal_mesh',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('opacity_mask_clip_value',.33)
    sample=materials.create_material_expression(mat,u.MaterialExpressionTextureSample)
    sample.set_editor_property('texture',texture)
    for channel,prop in [('RGB',u.MaterialProperty.MP_BASE_COLOR),('A',u.MaterialProperty.MP_OPACITY_MASK)]:
        if not materials.connect_material_property(sample,channel,prop):
            raise RuntimeError('Could not connect bristle '+channel)
    rough=materials.create_material_expression(mat,u.MaterialExpressionConstant)
    rough.set_editor_property('r',.84)
    materials.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    spec=materials.create_material_expression(mat,u.MaterialExpressionConstant)
    spec.set_editor_property('r',.22)
    materials.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
    errors=list(materials.recompile_material(mat))
    if errors:
        raise RuntimeError(str(errors))
    save(mat)
    return mat


def build_mesh():
    library.make_directory(looks)
    original=u.load_asset(pack+'/Meshes/SK_Pig')
    boar=u.load_asset(skin) if library.does_asset_exist(skin) else library.duplicate_asset(original.get_path_name(),skin)
    tooth=u.load_asset(ivory) if library.does_asset_exist(ivory) else library.duplicate_asset(
        '/Game/Monsters/Wildlife/Trophies/M_boar_tusk',ivory)
    if not boar or not tooth:
        raise RuntimeError('Could not duplicate the source mesh or tusk material')
    tooth.set_editor_property('used_with_skeletal_mesh',True)
    save(tooth)
    coat=import_texture('T_WL_BoarCoat')
    palette=[coat_material('M_PigDirty','M_BoarCoat',coat),
             coat_material('M_PigHairDirty','M_BoarHair',coat), tooth,
             create_mane_material(import_texture('T_WL_BoarMane',masked=True))]
    if not all(palette):
        raise RuntimeError('Missing boar surface')
    return build_geometry(original,boar,palette)


def build_geometry(original,boar,palette):
    shape=runpy.run_path(str(Path(__file__).with_name('boar_silhouette.py')))
    slot_names=[str(s.material_slot_name) for s in original.materials]+['Tusks','DorsalBristles']
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    asset_io=u.GeometryScript_AssetUtils
    count=editor.get_lod_count(original)
    for lod in range(count):
        dm,status=asset_io.copy_mesh_from_skeletal_mesh(original,u.DynamicMesh(),
            u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Could not read body LOD '+str(lod))
        shape['shape_eyes'](dm)
        bones={str(b.name):b.index for b in u.GeometryScript_BoneWeights.get_all_bones_info(dm)[1]}
        # Use each LOD's own skin surface and bone weights so that roots do not
        # float as the original pig mesh simplifies with distance.
        back=shape['BackSurface'](dm)
        shape['mane'](lod,back).append(dm,3)
        shape['tusks'](lod,bones['PIG_-Queue-de-cheval-1']).append(dm,2)
        opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=palette,
            new_material_slot_names=slot_names,enable_recompute_normals=False,enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=asset_io.copy_mesh_to_skeletal_mesh(dm,boar,opts,u.GeometryScriptMeshWriteLOD(lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Could not write boar LOD '+str(lod))
    save(boar)
    return boar,count


def author():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('BOAR_PIE_ACTIVE')
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    pending=dirty.intersection({actor,dataset})
    if pending:
        raise RuntimeError('Unsaved changes on '+str(pending))
    boar,count=build_mesh()
    anim=u.load_asset(dataset)
    anim.modify()
    anim.set_editor_property('reference_mesh',boar)
    save(anim)
    bp=u.load_asset(actor)
    component=u.get_default_object(bp.generated_class()).get_editor_property('mesh')
    bp.modify()
    component.modify()
    component.set_skeletal_mesh_asset(boar)
    runpy.run_path(str(Path(__file__).with_name('boar_materials.py')))['apply'](bp)
    save(bp)
    u.log(f'BOAR_APPEARANCE_SAVED {skin}, {actor}, {dataset}, LODs={count}')


if __name__=='__main__':
    author()
