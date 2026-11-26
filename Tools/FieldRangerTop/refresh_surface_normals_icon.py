"""Refresh the texture fallback after a material-only update; keep display geometry."""
import hashlib,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021';OUT=R/'SurfaceNormals20261021'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End play before saving the refreshed shirt icon')
materials=read(R/'materials.json');saved=read(R/'saved_assets.json');display=read(R/'display_assets.json');editable=read(R/'editable.json')
if materials.get('surface_revision')!='SurfaceNormals20261021' or not all(d.get('completed') for d in (materials,saved,display,editable)):raise RuntimeError('Finish the surface material save before refreshing its icon')
package=display['texture'].split('.')[0];folder,name=package.rsplit('/',1)
task=u.AssetImportTask();task.filename=editable['icon'];task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=u.load_asset(package)
for key,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():texture.set_editor_property(key,value)
texture.modify()
if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Cannot save the refreshed shirt icon')
display.update(surface_revision=materials['surface_revision'],material_revision=materials['revision'],png_sha256=hashlib.sha256(Path(editable['icon']).read_bytes()).hexdigest(),geometry_changed=False)
(R/'display_assets.json').write_text(json.dumps(display,indent=2),encoding='utf-8')
(OUT/'saved.json').write_text(json.dumps(dict(completed=True,surface_revision=materials['surface_revision'],material_revision=materials['revision'],profiles=list(saved['saved']),materials=materials['materials'],textures=read(R/'surfaces.json')['files'],icon=texture.get_path_name(),geometry_authored=False,geometry_display_changed=False,runtime_tested=False,preview_rendered=False),indent=2),encoding='utf-8')
print('SURFACE_NORMALS_ICON_SAVED',flush=True)
