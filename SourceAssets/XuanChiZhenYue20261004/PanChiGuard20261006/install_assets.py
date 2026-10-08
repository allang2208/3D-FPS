"""Headless author import: one guard, copper PBR, temporal variant and shared icon."""
from pathlib import Path
import json,runpy,shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
m=json.loads((P/'guard_manifest.json').read_text(encoding='utf-8'));D=m['ue_root']
A,E,L=u.AssetToolsHelpers.get_asset_tools(),u.MaterialEditingLibrary,u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Exit PIE before importing this guard')
receipt={'complete':False,'assets_saved':False,'assets':[],'temporal_materials':{},'runtime_tested':False}
out=P/'import_receipt.json'
def record():out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(obj):
    L.set_metadata_tag(obj,'PanChiGuardRevision','PanChiGuard20261006')
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Asset save failed '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name());record();return obj
def import_one(file,path,options=None):
    existing=u.load_asset(path)
    if existing and L.get_metadata_tag(existing,'PanChiGuardRevision')!='PanChiGuard20261006':raise RuntimeError('Preserved unowned asset '+path)
    t=u.AssetImportTask();t.filename=str(file);t.destination_path,t.destination_name=path.rsplit('/',1)
    t.automated=True;t.replace_existing=bool(existing);t.save=False
    if options:t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(path)
    if not obj or not t.imported_object_paths:raise RuntimeError('Import did not produce '+path)
    return obj

textures={}
for key in ['BaseColor','ORM','Normal']:
    tex=import_one(P/'Textures'/('PanChi_'+key+'.png'),D+'/Textures/T_PanChi_'+key)
    tex.srgb=key=='BaseColor';tex.never_stream=False
    tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_BC7 if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
    tex.address_x=u.TextureAddress.TA_CLAMP;tex.address_y=u.TextureAddress.TA_CLAMP
    if key=='Normal':tex.flip_green_channel=True
    textures[key]=save(tex)
hilt=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2/Materials/M_XuanChi_Hilt_V2')
steel=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/BladeV3/Materials/M_XuanChi_SteelRelief_V3')
name='M_XuanChi_PanChiWing_V1';mat=u.load_asset(D+'/Materials/'+name)
if not mat:mat=A.duplicate_asset(name,D+'/Materials',hilt)
elif L.get_metadata_tag(mat,'PanChiGuardRevision')!='PanChiGuard20261006':raise RuntimeError('Preserved unowned wing material')
for expr in E.get_material_expressions(mat):
    if isinstance(expr,u.MaterialExpressionTextureSample):
        old=expr.get_editor_property('texture')
        for key,tex in textures.items():
            if old and key in old.get_name():expr.set_editor_property('texture',tex)
mat.set_editor_property('used_with_skeletal_mesh',False)
errors=E.recompile_material(mat)
if errors:raise RuntimeError('Wing material compilation '+str(errors))
save(mat)
tn=name+'_Whirlwind';temporal=u.load_asset(D+'/Materials/'+tn)
if not temporal:
    temporal=A.duplicate_asset(tn,D+'/Materials',mat)
    response=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
    one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
    E.connect_material_expressions(one,'',response,'')
elif L.get_metadata_tag(temporal,'PanChiGuardRevision')!='PanChiGuard20261006':raise RuntimeError('Preserved unowned temporal material')
for expr in E.get_material_expressions(temporal):
    if isinstance(expr,u.MaterialExpressionTextureSample):
        old=expr.get_editor_property('texture')
        for key,tex in textures.items():
            if old and key in old.get_name():expr.set_editor_property('texture',tex)
errors=E.recompile_material(temporal)
if errors:raise RuntimeError('Temporal material compilation '+str(errors))
save(temporal);receipt['temporal_materials'][mat.get_path_name()]=temporal.get_path_name()

world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
cfg=u.FbxImportUI();cfg.automated_import_should_detect_type=False
cfg.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;cfg.import_as_skeletal=False;cfg.import_mesh=True
cfg.import_materials=False;cfg.import_textures=False;cfg.import_animations=False;cfg.lod_number=3;cfg.auto_compute_lod_distances=True
data=cfg.static_mesh_import_data;data.combine_meshes=False;data.import_mesh_lods=True
data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.build_nanite=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh=import_one(P/'Export'/(m['mesh_name']+'.fbx'),m['mesh'].split('.')[0],cfg)
for i,slot in enumerate(mesh.static_materials):
    key=str(slot.material_slot_name)
    mesh.set_material(i,mat if 'PanChiWing' in key else steel if 'SteelRelief' in key else hilt)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for lod in range(sm.get_lod_count(mesh)):
    build=sm.get_lod_build_settings(mesh,lod);build.recompute_normals=False;build.recompute_tangents=True
    build.use_mikk_t_space=True;build.use_full_precision_u_vs=True;sm.set_lod_build_settings(mesh,lod,build)
save(mesh)
icon_key='guard_panchi_zhanyue';dst=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon_key+'.png')
shutil.copy2(P/'Icons'/(icon_key+'.png'),dst)
icon=import_one(dst,'/Game/ColdSteelData/AttachmentIcons20260913/'+icon_key)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('never_stream',True);icon.set_editor_property('srgb',True);save(icon)
receipt['assets_saved']=True;receipt['mesh']=mesh.get_path_name();receipt['icon']=icon.get_path_name();record()
runpy.run_path(str(P/'catalog_extension.py'),run_name='__main__')
receipt['complete']=True;record();print('PANCHI_GUARD_ASSETS_SAVED '+str(len(receipt['assets'])),flush=True)
