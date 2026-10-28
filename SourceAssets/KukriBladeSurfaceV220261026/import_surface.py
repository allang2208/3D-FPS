"""Replace nine blade PBR textures and three meshes with refined corner normals."""
import json,shutil,sys
from datetime import datetime
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriBladeSurfaceV220261026')
sys.path.insert(0,str(P.parent/'KukriAssetRepair20261026'))
from kukri_mesh_import import import_mesh,require_authoring_context
require_authoring_context()
PROJECT=P.parents[1]
data=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
dest='/Game/Weapons/Kukri20261020/BladeVariants20261026/Textures'
tools=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
targets={entry['mesh'].split('.')[0] for entry in data['variants']}
targets.update(dest+'/'+Path(filename).stem for entry in data['variants'] for filename in entry['textures'].values())
conflicts=targets.intersection(package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if conflicts:raise RuntimeError('Unsaved target packages: '+', '.join(sorted(conflicts)))
receipt={'complete':False,'started':datetime.now().astimezone().isoformat(),
         'saved_assets':[],'vertex_positions_changed':False,'corner_normals_refined':True,'uv0_changed':False,'numeric_changes':False,'runtime_tested':False}
for entry in data['variants']:
    for suffix,filename in entry['textures'].items():
        name=Path(filename).stem
        package=PROJECT/'Content/Weapons/Kukri20261020/BladeVariants20261026/Textures'/(name+'.uasset')
        backup=P/'Before'/package.name
        if package.exists() and not backup.exists():shutil.copy2(package,backup)
        task=u.AssetImportTask();task.filename=filename;task.destination_path=dest;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False
        tools.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
        if not asset:raise RuntimeError('Texture import failed: '+name)
        asset.set_editor_property('srgb',suffix=='BaseColor')
        asset.set_editor_property('compression_settings',{
            'BaseColor':u.TextureCompressionSettings.TC_BC7,'ORM':u.TextureCompressionSettings.TC_MASKS,
            'Normal':u.TextureCompressionSettings.TC_NORMALMAP}[suffix])
        asset.set_editor_property('lod_group',{
            'BaseColor':u.TextureGroup.TEXTUREGROUP_WEAPON,'ORM':u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,
            'Normal':u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP}[suffix])
        asset.set_editor_property('never_stream',False);asset.set_editor_property('max_texture_size',2048)
        if suffix=='Normal':asset.set_editor_property('flip_green_channel',True)
        if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+name)
        receipt['saved_assets'].append(asset.get_path_name())
        (P/'Receipts/import-surface.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    package=PROJECT/'Content/Weapons/Kukri20261020/BladeVariants20261026'/(entry['object']+'.uasset')
    backup=P/'Before'/package.name
    if package.exists() and not backup.exists():shutil.copy2(package,backup)
    mesh=import_mesh(entry['fbx'],entry['mesh'],u.load_asset(entry['material']))
    u.EditorAssetLibrary.set_metadata_tag(mesh,'Kukri.Source',str(P/'Kukri_Blade_SurfaceV2_Editable.blend'))
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Mesh save failed')
    receipt['saved_assets'].append(mesh.get_path_name())
receipt['complete']=True
receipt['rune_update']='The three base materials and nine selected-rune instances resolve the same replaced texture assets. Factory blade uses separate original textures.'
(P/'Receipts/import-surface.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('KUKRI_SURFACE_V2_SAVED '+str(len(receipt['saved_assets'])))
