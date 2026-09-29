"""Apply the accepted fingerless leather bake to the tactical glove family.

Use the existing MCP Python batch when the editor is running. Saves only this
item's materials/meshes and merges its catalog fields after all assets are saved.
"""
import sys
import shutil
import hashlib
import runpy
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P, ITEM, ICON, read, write
import import_tailored_fingerless_candidate as native

R = P/'SourceAssets/ModularOutfit20260927/OriginalLeatherV2'
DEST = '/Game/Characters/ModularOutfit20260924/OriginalLeatherV2'
E = u.EditorAssetLibrary; A = u.AssetToolsHelpers.get_asset_tools(); L = u.MaterialEditingLibrary
CFG = P/'Content/ColdSteelData/modular_outfits.json'; CATALOG = P/'Content/ColdSteelData/items.json'


def material(group):
    folder = DEST+'/Materials/'+group; E.make_directory(folder)
    textures = {}
    for channel in ('BaseColor','Roughness','Normal'):
        name = 'T_OriginalLeather_'+channel
        task = u.AssetImportTask(); task.filename = str(R/'Textures'/group/(name+'.png'))
        task.destination_path = folder; task.destination_name = name; task.automated = True; task.replace_existing = True; task.save = False
        A.import_asset_tasks([task]); tex = native.load(folder+'/'+name)
        tex.set_editor_property('srgb', channel == 'BaseColor')
        kind = u.TextureCompressionSettings.TC_NORMALMAP if channel == 'Normal' else u.TextureCompressionSettings.TC_DEFAULT if channel == 'BaseColor' else u.TextureCompressionSettings.TC_MASKS
        tex.set_editor_property('compression_settings',kind)
        if channel == 'Normal': tex.set_editor_property('flip_green_channel',True)
        native.save(tex); textures[channel] = tex
    name = 'M_OriginalTailoredLeather'
    mat = u.load_asset(folder+'/'+name) if E.does_asset_exist(folder+'/'+name) else A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    # The baked parent uses the same direct normal sampling as the accepted
    # fingerless parent. No custom BC5 unpacking or unrelated triplanar shader.
    for expression in list(L.get_material_expressions(mat)): L.delete_material_expression(mat,expression)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH); L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    for channel,prop,sampler in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR,u.MaterialSamplerType.SAMPLERTYPE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS,u.MaterialSamplerType.SAMPLERTYPE_MASKS),('Normal',u.MaterialProperty.MP_NORMAL,u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]:
        node = L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
        node.set_editor_property('parameter_name',channel); node.set_editor_property('texture',textures[channel]); node.set_editor_property('sampler_type',sampler)
        if not L.connect_material_property(node,'R' if channel == 'Roughness' else 'RGB',prop): raise RuntimeError('Material connection failed: '+channel)
    for value,prop in ((.42,u.MaterialProperty.MP_SPECULAR),(0.,u.MaterialProperty.MP_METALLIC)):
        node = L.create_material_expression(mat,u.MaterialExpressionConstant); node.set_editor_property('r',value)
        if not L.connect_material_property(node,'',prop): raise RuntimeError('Material constant connection failed')
    L.layout_material_expressions(mat)
    errors = L.recompile_material(mat)
    if errors: raise RuntimeError('Tactical glove material build failed: '+str(errors))
    native.save(mat)
    return mat


def pickup(mat):
    folder = DEST+'/Pickups'; name = 'SM_OriginalLeatherGlovesV2_Pickup'; E.make_directory(folder)
    task = u.AssetImportTask(); task.filename = str(R/(name+'.fbx')); task.destination_path = folder; task.destination_name = name
    task.automated = True; task.replace_existing = True; task.save = False
    opts = u.FbxImportUI(); opts.import_as_skeletal = False; opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opts.automated_import_should_detect_type = False; opts.import_materials = False; opts.import_textures = False
    opts.static_mesh_import_data.combine_meshes = True; opts.static_mesh_import_data.auto_generate_collision = True
    task.options = opts; A.import_asset_tasks([task]); mesh = native.load(folder+'/'+name)
    for i in range(len(mesh.get_editor_property('static_materials'))): mesh.set_material(i,mat)
    editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    settings = []
    for percentage,screen in ((1.,1.),(.5,.18),(.25,.075)):
        value = u.StaticMeshReductionSettings(); value.percent_triangles = percentage; value.screen_size = screen; settings.append(value)
    options = u.StaticMeshReductionOptions(); options.auto_compute_lod_screen_size = False; options.reduction_settings = settings
    editor.set_lods(mesh,options); native.save(mesh)
    return mesh


def main():
    if not (R/'artwork.json').exists(): raise RuntimeError('Complete the tactical glove bake first')
    initial = read(CFG); initial_item = read(CATALOG)[ITEM]; recipe = initial['items'][ITEM]
    if recipe.get('appearance_family') not in ('OriginalLeatherV1','OriginalLeatherV2'): raise RuntimeError('Unexpected tactical glove family')
    if not (R/'before-publication.json').exists(): write(R/'before-publication.json',dict(recipe=recipe,item=initial_item))
    materials = {group: material(group) for group in ('M4','Body')}
    profiles = dict(recipe['rig_meshes']); saved = {}
    for name,path in profiles.items():
        if name == 'Body':
            data = read(R/'Baked/Body.json')
            sha = hashlib.sha256((R/'Baked/Body.json').read_bytes()).hexdigest()
            record = read(R/'Saved/BodyGeometry.json') if (R/'Saved/BodyGeometry.json').exists() else {}
            if record.get('authored_sha256') == sha:
                mesh = native.load(record['mesh'])
            else:
                try:
                    mesh = native.build_mesh(data,'SK_Body_OriginalLeatherV2',[materials['Body']],['OriginalLeather'],DEST)
                except RuntimeError as error:
                    if str(error) != 'Candidate LOD build failed': raise
                    # The native-skin donor carries its old LOD0 simplified
                    # flag. This package now contains freshly authored LOD0.
                    runpy.run_path(str(P/'Tools/ModularOutfit/finish_original_body_leather_lods.py'),run_name='__main__')
                    mesh = native.load(DEST+'/Body/SK_Body_OriginalLeatherV2')
                write(R/'Saved/BodyGeometry.json',dict(mesh=mesh.get_path_name(),authored_sha256=sha,lods=3))
            profiles[name] = mesh.get_path_name()
        else:
            mesh = native.load(path); slots = mesh.get_editor_property('materials')
            for slot in slots: slot.set_editor_property('material_interface',materials['M4'])
            mesh.set_editor_property('materials',slots); native.save(mesh)
        saved[name] = dict(mesh=mesh.get_path_name(),material=materials['Body' if name=='Body' else 'M4'].get_path_name())
        write(R/'Saved'/f'{name}.json',saved[name])
        print('ORIGINAL_TAILORED_MATERIAL_SAVED',name,flush=True)
    prop = pickup(materials['M4'])
    # Empty recipe material preserves the explicit per-mesh slots. Body uses
    # its own noncollapsed UVs; the first-person meshes keep their original UV0.
    updated = dict(recipe,material='',rig_meshes=profiles,appearance_family='OriginalLeatherV2')
    appearance = {key:initial_item[key] for key in ('desc','ue_icon','world_mesh','world_material')}
    appearance.update(ue_icon=ICON,world_mesh=prop.get_path_name(),world_material=materials['M4'].get_path_name())
    receipt = dict(item=ITEM,recipe=updated,appearance=appearance,profiles=saved,
                   materials={k:v.get_path_name() for k,v in materials.items()},source_family='TailoredFingerlessV1',
                   unchanged_first_person_geometry=True,new_animations=0,runtime_tested=False)
    write(R/'saved-assets.json',receipt)
    cfg = read(CFG); items = read(CATALOG)
    if cfg['items'][ITEM] != recipe or items[ITEM] != initial_item: raise RuntimeError('Tactical glove configuration changed during import; assets retained')
    shutil.copy2(R/'ue_original_gloves.png',P/'Content/ColdSteelData'/ICON)
    cfg['items'][ITEM] = updated; items[ITEM].update(appearance)
    write(CFG,cfg); write(CATALOG,items); write(R/'published.json',receipt)
    print('ORIGINAL_TAILORED_LEATHER_PUBLISHED',len(saved),flush=True)


if __name__ == '__main__': main()
