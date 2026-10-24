"""Import waterfront batches and rebuild reflection coordinates on retained water."""
from pathlib import Path
import unreal as u,json,runpy,gc
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',meshes={},materials={},textures=[])
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing V15 source '+p)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('V15 asset save '+a.get_path_name())
def duplicate(name,source):
    p=BASE+'/Materials/'+name
    return load(p) if E.does_asset_exist(p) else A.duplicate_asset(name,BASE+'/Materials',source)
def main():
    roles={'Frame':'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Materials/M_AP7_Machined',
           'Stone':'/Game/Props/CyberpunkBayBuildings20261022/Materials/M_DetailedBay_Stone',
           'Neon0':'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV6/Materials/M_AP6_Neon0',
           'WarmLight':'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV6/Materials/M_AP6_WarmLight'}
    for row in json.loads((R/'assembly.json').read_text())['meshes']:
        task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=row['name'];task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data
        for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():data.set_editor_property(k,v)
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt;A.import_asset_tasks([task]);mesh=load(BASE+'/Meshes/'+row['name'])
        for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(roles[str(s.material_slot_name)]))
        settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
        settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True;settings.explicit_tangents=True;settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;settings.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',settings)
        if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build '+row['key'])
        save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),triangles=row['triangles']);record();gc.collect()
    task=u.AssetImportTask();task.filename=str(R/'T_AP15_CityReflection.dds');task.destination_path=BASE+'/Textures';task.destination_name='T_AP15_CityReflection';task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task]);cube=load(BASE+'/Textures/T_AP15_CityReflection')
    for k,v in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,max_texture_size=2048,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,lod_group=u.TextureGroup.TEXTUREGROUP_SKYBOX).items():cube.set_editor_property(k,v)
    save(cube);report['textures'].append(cube.get_path_name());record()
    before=json.loads((R/'bay_before.json').read_text());old=load(before['BAY_Water']['meshes'][0]['materials'][0]);parent=old.get_editor_property('parent')
    mat=duplicate('M_AP15_BayWater',parent);emitter_count=0;cube_count=0
    for n in L.get_material_expressions(mat):
        if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection':n.set_editor_property('texture',cube);cube_count+=1
        if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='AP10 coherent billboard and sweeping beam water reflections':
            n.set_editor_property('code',(R/'WaterReflection.hlsl').read_text(encoding='utf8'));n.set_editor_property('desc','AP15 revised emitter coordinates');emitter_count+=1
    if emitter_count!=1 or cube_count!=1:raise RuntimeError('Retained water reflection inputs changed; preserve source material')
    # Retain pixel-footprint filtering, wave spectrum, mip bias and native sky.
    errors=list(L.recompile_material(mat))
    if errors:raise RuntimeError('V15 shader compilation '+str(errors))
    stats=L.get_statistics(mat)
    if stats.get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('V15 shader production returned no program')
    save(mat);report['materials']['WaterMaster']=mat.get_path_name()
    mi=duplicate('MI_AP15_BayWater',old);L.set_material_instance_parent(mi,mat);L.set_material_instance_texture_parameter_value(mi,'BayReflection',cube)
    L.update_material_instance(mi);save(mi);report['materials']['Water']=mi.get_path_name()
    report.update(stage='assets_saved',shader_compiled=True,new_dynamic_lights=0,new_capture_actors=0,new_tick_actors=0,additional_triangles=sum(x['triangles'] for x in report['meshes'].values()));record();print('AP15_ASSETS_SAVED')
if __name__=='__main__':main()
