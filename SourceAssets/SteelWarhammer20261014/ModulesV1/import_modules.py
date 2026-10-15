"""Import six factory modules and their UI icons; preserve the live arms/materials."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/SteelWarhammer20261014/ModulesV1'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
material=u.load_asset('/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface')
if not material:raise RuntimeError('Current warhammer material is missing')
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name().startswith(D+'/'):raise RuntimeError('Unsaved destination package: '+pkg.get_name())
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
receipt={'assets':[],'complete':False,'tested':False}
catalog={'version':1,'weapon':'ue_steel_warhammer','interface':'warhammer_factory_v1',
    'arms_mesh':'/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1.SK_Warhammer_BareArmsSprintV1',
    'root_slot':'head_mount','module_slots':[row['slot'] for row in rows],'drive_bone':'WPN_root','slots':{}}

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

for row in rows:
    name=row['mesh'];asset=u.load_asset(D+'/'+name)
    if not asset:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        t=u.AssetImportTask();t.filename=str(P/'Export'/(name+'.fbx'));t.destination_path=D;t.destination_name=name;t.automated=True;t.save=False;t.options=opt
        A.import_asset_tasks([t]);asset=u.load_asset(D+'/'+name)
        if not asset:raise RuntimeError('Import failed: '+name)
    asset.set_material(0,material);save(asset)
    appearance='固定金属长柄' if row['slot']=='shaft' else '原装'+row['name']+' · 独立组件'
    catalog['slots'][row['slot']]={'factory':{'mesh':asset.get_path_name(),'location_cm':row['location_cm'],'appearance':appearance}}
# Keep any later alternatives if the factory exporter is intentionally rerun.
target=ROOT/'Content/ColdSteelData/warhammer-modules.json'
if target.exists():
    previous=json.loads(target.read_text(encoding='utf-8-sig'))
    if 'bone_mount' in previous:catalog['bone_mount']=previous['bone_mount']
    for slot,choices in previous.get('slots',{}).items():
        for key,value in choices.items():
            if key!='factory':catalog['slots'].setdefault(slot,{})[key]=value
(P/'catalog_base.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
# Final runtime catalog is written by the mount-authoring commandlet after the build.
icon_root=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
for row in rows:
    for key in ('ue_steel_warhammer_category_'+row['slot'],'ue_steel_warhammer_'+row['slot']+'_false'):
        file=icon_root/(key+'.png')
        if not file.exists():continue
        folder='/Game/ColdSteelData/AttachmentIcons20260913';tex=u.load_asset(folder+'/'+key)
        if not tex:
            t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=key;t.automated=True;t.save=False
            A.import_asset_tasks([t]);tex=u.load_asset(folder+'/'+key)
        if not tex:raise RuntimeError('Icon import failed: '+key)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
receipt['complete']=True;(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))
