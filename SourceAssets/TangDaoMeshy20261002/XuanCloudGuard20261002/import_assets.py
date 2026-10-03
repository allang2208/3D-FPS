"""Import and save authored guard, PBR, temporal material and actual menu icon."""
import unreal as u,json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong UE project for TangDao guard')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
editor=None if commandlet else u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor and editor.is_in_play_in_editor():raise RuntimeError('Import solid geometry outside PIE. Existing play session was preserved.')
m=json.loads((P/'guard_manifest.json').read_text(encoding='utf-8'));D=m['ue_root']
A,L,E=u.AssetToolsHelpers.get_asset_tools(),u.EditorAssetLibrary,u.MaterialEditingLibrary
receipt={'revision':'TangDaoXuanCloudGuard20261002','assets':[],'complete':False,'runtime_tested':False}
previous=P/'import_receipt.json'
old=json.loads(previous.read_text(encoding='utf-8')) if previous.exists() else {}
owned=set(old.get('assets',[]))
def record():previous.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Could not save guard asset '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());owned.add(asset.get_path_name());record();return asset
def import_one(file,path,options=None):
    obj=u.load_asset(path)
    if obj:
        if obj.get_path_name() not in owned:raise RuntimeError('Preserved unowned asset '+path)
        return obj
    task=u.AssetImportTask();task.filename=str(file);task.destination_path,task.destination_name=path.rsplit('/',1)
    task.automated=True;task.replace_existing=False;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);obj=u.load_asset(path)
    if not obj or not task.imported_object_paths:raise RuntimeError('Guard import incomplete '+str(file))
    return obj
record()
textures={}
for key in ['BaseColor','ORM','Normal']:
    name='T_TangDao_XuanCloudGuard_'+key
    t=import_one(P/'Textures'/('TangDao_XuanCloudGuard_'+key+'.png'),D+'/Textures/'+name)
    t.set_editor_property('srgb',key=='BaseColor')
    t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS if key=='ORM' else u.TextureCompressionSettings.TC_BC7)
    t.set_editor_property('never_stream',False)
    if key=='Normal':t.set_editor_property('flip_green_channel',True)
    textures[key]=save(t)
mat_path=D+'/Materials/M_TangDaoXuanCloudGuard'
mat=u.load_asset(mat_path)
if not mat:
    source=u.load_asset('/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoSurface')
    mat=A.duplicate_asset('M_TangDaoXuanCloudGuard',D+'/Materials',source)
    if not mat:raise RuntimeError('Guard Substrate material duplication failed')
    for expr in E.get_material_expressions(mat):
        if isinstance(expr,u.MaterialExpressionTextureSample):
            tex=expr.get_editor_property('texture')
            for key in textures:
                if tex and tex.get_name()=='T_TangDao_'+key:expr.set_editor_property('texture',textures[key])
elif mat.get_path_name() not in owned:raise RuntimeError('Preserved unowned guard material')
mat.set_editor_property('used_with_skeletal_mesh',False)
errors=list(E.recompile_material(mat) or [])
if errors:raise RuntimeError('Guard material compilation failed '+str(errors))
save(mat)
name='M_TangDaoXuanCloudGuard_Whirlwind';temporal=u.load_asset(D+'/Materials/'+name)
if not temporal:
    temporal=A.duplicate_asset(name,D+'/Materials',mat)
    response=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
    one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
    if not E.connect_material_expressions(one,'',response,''):raise RuntimeError('Guard temporal material connection failed')
    errors=list(E.recompile_material(temporal) or [])
    if errors:raise RuntimeError('Guard temporal material build failed '+str(errors))
save(temporal)
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_mesh=True;options.import_as_skeletal=False
options.import_materials=False;options.import_textures=False;options.import_animations=False
options.lod_number=3;options.auto_compute_lod_distances=True
data=options.static_mesh_import_data;data.combine_meshes=False;data.import_mesh_lods=True
data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.build_nanite=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh=import_one(P/'Export'/(m['mesh_name']+'.fbx'),m['mesh'].split('.')[0],options)
for i,slot in enumerate(mesh.static_materials):
    if str(slot.material_slot_name)!='M_TangDaoXuanCloudGuard':raise RuntimeError('Unexpected guard material slot')
    mesh.set_material(i,mat)
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;nanite.explicit_tangents=True;nanite.fallback_relative_error=0.
mesh.set_editor_property('nanite_settings',nanite);save(mesh)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
counts=[mesh.get_num_triangles(i) for i in range(sm.get_lod_count(mesh))]
# Finish the same solid-geometry import contract repaired for the blade.
if len(counts)!=3 or min(counts)<=0:raise RuntimeError('Guard imported empty geometry; option not published')
name='ue_tang_dao_guard_xuan_cloud_dragon'
icon_source=P/'Icons'/(name+'.png');icon_target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(name+'.png')
shutil.copy2(icon_source,icon_target)
icon=import_one(icon_target,'/Game/ColdSteelData/AttachmentIcons20260913/'+name)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('never_stream',True);icon.set_editor_property('srgb',True);save(icon)
path=ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json';mapping=json.loads(path.read_text(encoding='utf-8-sig'))
backup=P/'Before'/path.name
if not backup.exists():shutil.copy2(path,backup)
mapping[mat.get_path_name()]=temporal.get_path_name()
temp=path.with_suffix('.json.xuancloudguard.tmp');temp.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
receipt.update(complete=True,mesh=mesh.get_path_name(),lod_triangles_saved=counts,materials=m['materials'],textures={k:t.get_path_name() for k,t in textures.items()},
    icon=icon.get_path_name(),stats={},material_source='/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoSurface',native_blade_runes_unchanged=True)
record();runpy.run_path(str(P/'catalog_extension.py'),run_name='__main__')
print('XUAN_CLOUD_GUARD_ASSETS_SAVED '+str(len(receipt['assets'])),flush=True)
