"""Author and install the selected white-marble, varied-constellation roof.

Preserves original pavilion geometry, materials and collision in source backups.
No level load, gameplay launch, screenshot or runtime test.
"""
import json
import math
from pathlib import Path
import unreal as u

HERE=Path(__file__).parent
BASE='/Game/Props/RomanColumn20260915'
ROOT='/Game/Props/RomanPavilionRoof20260919/WhiteCelestial'
E=u.EditorAssetLibrary
M=u.MaterialEditingLibrary
SV=u.ModelingService
TOOLS=u.AssetToolsHelpers.get_asset_tools()
REPORT={'assets':[],'runtime_tested':False,'preview_renderer':'Blender 5.1 Cycles'}
REVISION='C2'


def save(asset):
    package=u.load_package(asset.get_path_name().split('.')[0])
    if not u.EditorLoadingAndSavingUtils.save_packages([package],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    REPORT['assets'].append(asset.get_path_name())
    u.log('PAVILION_'+REVISION+'_SAVED '+asset.get_path_name())


def operation(result):
    if not result.success:raise RuntimeError(str(result.message))
    return result


def load_mesh(asset,handles):
    # The EditorAssetLibrary path loader rejects PIE. Copy the already loaded
    # asset into our own session mesh, using the same GeometryScript options.
    handle=operation(SV.create_mesh()).handle;handles.append(handle)
    _,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        asset,SV.get_dynamic_mesh(handle),u.GeometryScriptCopyMeshFromAssetOptions(),
        u.GeometryScriptMeshReadLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not read '+asset.get_path_name())
    return handle


def gold_material():
    path=ROOT+'/M_PavilionAgedGold'
    existing=u.load_asset(path)
    if existing:return existing
    mat=TOOLS.create_asset('M_PavilionAgedGold',ROOT,u.Material,u.MaterialFactoryNew())
    col=M.create_material_expression(mat,u.MaterialExpressionVectorParameter)
    col.set_editor_property('parameter_name','GoldColor')
    col.set_editor_property('default_value',u.LinearColor(.58,.36,.14,1))
    M.connect_material_property(col,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    for name,value,prop in [('Metallic',.78,u.MaterialProperty.MP_METALLIC),('Roughness',.33,u.MaterialProperty.MP_ROUGHNESS)]:
        n=M.create_material_expression(mat,u.MaterialExpressionScalarParameter)
        n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value)
        M.connect_material_property(n,'',prop)
    errors=M.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat)
    return mat


def import_part(kind):
    name='SM_'+REVISION+'_'+kind
    path=ROOT+'/'+name
    existing=u.load_asset(path)
    if existing:return existing
    options=u.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh=True;options.import_as_skeletal=False
    options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.auto_generate_collision=False
    data.generate_lightmap_u_vs=False
    data.transform_vertex_to_absolute=True
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask()
    task.filename=str(HERE/f'{REVISION}_{kind}.fbx')
    task.destination_path=ROOT;task.destination_name=name
    task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
    TOOLS.import_asset_tasks([task])
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed: '+kind)
    save(asset)
    return asset


def source_backup(name):
    original=BASE+'/'+name
    backup=ROOT+'/SourceBackup/'+name+'_BeforeC2'
    if not u.load_asset(backup):
        old=TOOLS.duplicate_asset(name+'_BeforeC2',ROOT+'/SourceBackup',u.load_asset(original))
        if not old:raise RuntimeError('Could not preserve '+original)
        save(old)
    return backup


def assemble(name,offset,gold,parts):
    backup_path=source_backup(name)
    source=u.load_asset(backup_path)
    mats=[source.get_material(i) for i in range(len(source.get_editor_property('static_materials')))]
    gold_id=len(mats);mats.append(gold)
    handles=[]
    try:
        h=load_mesh(source,handles)
        for kind,part in parts.items():
            addition=load_mesh(part,handles)
            dm=SV.get_dynamic_mesh(addition)
            clear=getattr(u.GeometryScript_Materials,next(n for n in dir(u.GeometryScript_Materials) if n.startswith('clear_material')))
            clear(dm,gold_id if kind=='GoldDecor' else 0)
            # UVs only on new detail; existing marble UVs and custom normals stay intact.
            operation(SV.auto_uv(addition,'XAtlas',0))
            expected=json.loads((HERE/f'{REVISION}_{kind}_bounds.json').read_text())['bounds_m']
            bounds=part.get_bounds()
            scale=(expected[0][1]-expected[0][0])*100/(2*bounds.box_extent.x)
            center=[(a+b)*50 for a,b in expected]
            t=u.Transform()
            t.scale3d=u.Vector(scale,scale,scale)
            t.translation=u.Vector(center[0]-bounds.origin.x*scale,center[1]-bounds.origin.y*scale,
                                   center[2]-bounds.origin.z*scale+offset)
            operation(SV.append_mesh(h,addition,t))
        # Save a separate revision before switching the existing, referenced mesh.
        revision=ROOT+'/'+name+'_'+REVISION
        candidate=u.load_asset(revision)
        if not candidate:candidate=TOOLS.duplicate_asset(name+'_'+REVISION,ROOT,source)
        options=u.GeometryScriptCopyMeshToAssetOptions()
        options.enable_recompute_normals=False;options.enable_recompute_tangents=True
        options.replace_materials=True;options.new_materials=mats;options.use_build_scale=False
        dm=SV.get_dynamic_mesh(h)
        _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,candidate,options,u.GeometryScriptMeshWriteLOD())
        if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Assembly failed: '+name)
        # ComputeTransform centres the mesh bounds in its 20 cm footprint. Pad only
        # the upper culling bound to the next cell; no visible geometry is shifted.
        candidate.set_editor_property('positive_bounds_extension',u.Vector(0,0,0))
        b=candidate.get_bounds()
        height=math.ceil((2*b.box_extent.z)/20)*20
        padding=height-2*b.box_extent.z
        candidate.set_editor_property('positive_bounds_extension',u.Vector(0,0,padding))
        E.set_metadata_tag(candidate,'PavilionRoofRevision',REVISION+'_WhiteCelestial')
        save(candidate)
        active=u.load_asset(BASE+'/'+name)
        _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,active,options,u.GeometryScriptMeshWriteLOD())
        if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not install '+name)
        active.set_editor_property('positive_bounds_extension',u.Vector(0,0,padding))
        E.set_metadata_tag(active,'PavilionRoofRevision',REVISION+'_WhiteCelestial')
        save(active)
        REPORT[name]={'backup':backup_path,'revision':revision,'height_cm':height,'upper_bounds_padding_cm':padding,
                      'stone':mats[0].get_path_name(),'material_slots':len(mats)}
        return round(height/20)
    finally:
        for h in reversed(handles):SV.release_mesh(h)


def integrate(revision='C2'):
    global REVISION,REPORT
    REVISION=revision
    REPORT={'revision':REVISION,'assets':[],'runtime_tested':False,'preview_renderer':'Blender 5.1 Cycles'}
    gold=gold_material()
    parts={kind:import_part(kind) for kind in ('GoldDecor','WhiteGlobe')}
    full_height=assemble('SM_RomanPavilionFull_20',0.,gold,parts)
    assemble('SM_RomanPavilionDome_20',-360.,gold,parts)
    palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    entries=list(palette.get_editor_property('components'))
    for entry in entries:
        if str(entry.get_editor_property('id'))=='pavilion_full':
            footprint=entry.get_editor_property('footprint')
            entry.set_editor_property('footprint',u.IntVector(footprint.x,footprint.y,full_height))
            break
    else:raise RuntimeError('Active pavilion_full entry not found')
    palette.set_editor_property('components',entries);save(palette)
    (HERE/f'{REVISION}_integration.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    u.log('PAVILION_'+REVISION+'_INTEGRATION_COMPLETE')


if __name__=='__main__':
    integrate()
