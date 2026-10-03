"""Save new isolated cone assets, then switch only yanling_breaker recipe."""
import unreal as u,json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong UE project for TangDao pommel')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
editor=None if commandlet else u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor and editor.is_in_play_in_editor():raise RuntimeError('Import outside PIE; preserved existing play session')
m=json.loads((P/'pommel_manifest.json').read_text(encoding='utf-8'));D=m['ue_root']
A,L,E=u.AssetToolsHelpers.get_asset_tools(),u.EditorAssetLibrary,u.MaterialEditingLibrary
receipt={'revision':m['revision'],'assets':[],'complete':False,'runtime_tested':False}
previous=P/'import_receipt.json'
old=json.loads(previous.read_text(encoding='utf-8')) if previous.exists() else {}
owned=set(old.get('assets',[]))
parent_receipt=P.parent/'import_receipt.json'
if parent_receipt.exists():owned.update(json.loads(parent_receipt.read_text(encoding='utf-8')).get('assets',[]))
def record():previous.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Could not save '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());owned.add(asset.get_path_name());record();return asset
def import_one(file,path,options=None):
    obj=u.load_asset(path);refresh_icon=path.endswith('/ue_tang_dao_pommel_yanling_breaker')
    if obj:
        if obj.get_path_name() not in owned:raise RuntimeError('Preserved unowned asset '+path)
        if not refresh_icon:return obj
    task=u.AssetImportTask();task.filename=str(file);task.destination_path,task.destination_name=path.rsplit('/',1)
    task.automated=True;task.replace_existing=refresh_icon;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);obj=u.load_asset(path)
    if not obj or not task.imported_object_paths:raise RuntimeError('Pommel import incomplete '+str(file))
    return obj
def backup(path,label=None):
    target=P/'Before'/(label or path.name)
    if path.exists() and not target.exists():shutil.copy2(path,target)
record();textures={};materials={};temporal_materials={}
for family in ['Steel','Gilt','Lacquer']:
    textures[family]={}
    for key in ['BaseColor','ORM','Normal']:
        name=f'T_TangDao_YanlingConeV3_{family}_{key}'
        t=import_one(P/'Textures'/f'TangDao_YanlingConeV3_{family}_{key}.png',D+'/Textures/'+name)
        t.set_editor_property('srgb',key=='BaseColor')
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS if key=='ORM' else u.TextureCompressionSettings.TC_BC7)
        t.set_editor_property('never_stream',False)
        if key=='Normal':t.set_editor_property('flip_green_channel',True)
        textures[family][key]=save(t)
    name='M_TangDaoYanlingConeV3_'+family;path=D+'/Materials/'+name;mat=u.load_asset(path)
    if not mat:
        source=u.load_asset('/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoSurface')
        mat=A.duplicate_asset(name,D+'/Materials',source)
        if not mat:raise RuntimeError('Substrate surface duplication failed')
        for expr in E.get_material_expressions(mat):
            if isinstance(expr,u.MaterialExpressionTextureSample):
                tex=expr.get_editor_property('texture')
                for key in textures[family]:
                    if tex and tex.get_name()=='T_TangDao_'+key:expr.set_editor_property('texture',textures[family][key])
    elif mat.get_path_name() not in owned:raise RuntimeError('Preserved unowned pommel material')
    mat.set_editor_property('used_with_skeletal_mesh',False)
    errors=list(E.recompile_material(mat) or [])
    if errors:raise RuntimeError('Metal material compilation failed '+str(errors))
    materials[name]=save(mat)
    tname=name+'_Whirlwind';temporal=u.load_asset(D+'/Materials/'+tname)
    if not temporal:
        temporal=A.duplicate_asset(tname,D+'/Materials',mat)
        response=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
        one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
        if not E.connect_material_expressions(one,'',response,''):raise RuntimeError('Temporal material connection failed')
        errors=list(E.recompile_material(temporal) or [])
        if errors:raise RuntimeError('Temporal material compilation failed '+str(errors))
    temporal_materials[mat.get_path_name()]=save(temporal).get_path_name()
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_mesh=True;options.import_as_skeletal=False
options.import_materials=False;options.import_textures=False;options.import_animations=False
options.lod_number=3;options.auto_compute_lod_distances=True
data=options.static_mesh_import_data;data.combine_meshes=False;data.import_mesh_lods=True
data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.build_nanite=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh=import_one(P/'Export'/(m['mesh_name']+'.fbx'),m['mesh'].split('.')[0],options)
for i,slot in enumerate(mesh.static_materials):
    name=str(slot.material_slot_name)
    if name not in materials:raise RuntimeError('Unexpected cone material slot '+name)
    mesh.set_material(i,materials[name])
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;nanite.explicit_tangents=True;nanite.fallback_relative_error=0.
mesh.set_editor_property('nanite_settings',nanite);save(mesh)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
counts=[mesh.get_num_triangles(i) for i in range(sm.get_lod_count(mesh))]
if len(counts)!=3 or min(counts)<=0:raise RuntimeError('Cone imported empty geometry; option not published')
name='ue_tang_dao_pommel_yanling_breaker'
icon_source=P/'Icons'/(name+'.png');icon_target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(name+'.png')
backup(icon_target);shutil.copy2(icon_source,icon_target)
icon=import_one(icon_target,'/Game/ColdSteelData/AttachmentIcons20260913/'+name)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('never_stream',True);icon.set_editor_property('srgb',True);save(icon)
path=ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json';backup(path)
mapping=json.loads(path.read_text(encoding='utf-8-sig'));mapping.update(temporal_materials)
temp=path.with_suffix('.json.yanlingpommel.tmp');temp.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
receipt.update(complete=True,mesh=mesh.get_path_name(),lod_triangles_saved=counts,materials=m['materials'],
 textures={f:{k:t.get_path_name() for k,t in ts.items()} for f,ts in textures.items()},icon=icon.get_path_name(),
 material_source='/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoSurface',native_blade_runes_unchanged=True)
record()
for file in ['pommel_manifest.json','import_receipt.json']:
    backup(P.parent/file,'parent_'+file);shutil.copy2(P/file,P.parent/file)
runpy.run_path(str(P.parent/'catalog_extension.py'),run_name='__main__')
print('YANLING_CONE_V3_ASSETS_SAVED '+str(len(receipt['assets'])),flush=True)
