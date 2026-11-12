"""Publish the Peakwatch icon and extend the existing physical-lens material."""
from pathlib import Path
from datetime import datetime
import hashlib, json, os, shutil
import unreal as u

P=Path('D:/FPS3D/FPSGAME/SourceAssets/PeakwatchPhysicalOptics20261109')
ROOT=P.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT.resolve():
    raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('Preserving active PIE; finish play before asset publication')
L,E=u.MaterialEditingLibrary,u.EditorAssetLibrary
key='bow_woodsteel_sight_highland_peakwatch_3_6x'
icon_dir='/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
icon_pkg=icon_dir+'/'+key
lens_pkg='/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens'
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection({icon_pkg,lens_pkg}):
    raise RuntimeError('Preserving unsaved target assets')
receipt={'saved':[], 'runtime_tested':False,'complete':False}
before=P/'BeforeAssets'/datetime.now().strftime('%Y%m%d-%H%M%S')
before.mkdir(parents=True,exist_ok=False)
for pkg in (icon_pkg,lens_pkg):
    path=ROOT/'Content'/pkg.removeprefix('/Game/')
    for suffix in ('.uasset','.png'):
        file=path.with_suffix(suffix)
        if file.exists():shutil.copy2(file,before/file.name)

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    (P/'asset-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

# Follow the existing emissive graph to the one scene/reticle Custom node.
# Preserve all other material properties, graph nodes and gun reticle styles.
m=u.load_asset(lens_pkg)
if not isinstance(m,u.Material):raise RuntimeError('Missing shared lens material')
todo=[L.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)]
nodes={}
while todo:
    node=todo.pop()
    if not node or node.get_path_name() in nodes:continue
    nodes[node.get_path_name()]=node
    todo.extend(L.get_inputs_for_material_expression(m,node))
pictures=[n for n in nodes.values() if isinstance(n,u.MaterialExpressionCustom)
          and 'CaptureTanHalfFOV' in n.get_editor_property('code')
          and 'ReticleStyle' in n.get_editor_property('code')]
if len(pictures)!=1:raise RuntimeError('Shared lens picture node is ambiguous')
picture=pictures[0]
inputs=list(picture.get_editor_property('inputs'))
names={str(pin.get_editor_property('input_name')) for pin in inputs}
for name in ('BowDrawState','BowRelease'):
    if name not in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
picture.set_editor_property('inputs',inputs)
for name,cls,value,output in (
        ('BowDrawState',u.MaterialExpressionVectorParameter,u.LinearColor(0,0,0,0),'RGBA'),
        ('BowRelease',u.MaterialExpressionScalarParameter,0.0,'')):
    matches=[n for n in nodes.values() if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==name]
    node=matches[0] if matches else L.create_material_expression(m,cls)
    node.set_editor_property('parameter_name',name)
    node.set_editor_property('default_value',value)
    if not L.connect_material_expressions(node,output,picture,name):
        raise RuntimeError('Cannot connect '+name)
picture.set_editor_property('code',(ROOT/'SourceAssets/SharedPhysicalOptics20261030/lens.hlsl').read_text(encoding='utf-8'))
picture.set_editor_property('desc','Shared physical optics, including Peakwatch angular reticle and bow draw cues')
errors=L.recompile_material(m)
if errors:raise RuntimeError(str(errors))
stats=L.get_statistics(m)
if stats.num_pixel_shader_instructions<=0:raise RuntimeError('Lens shader did not compile')
receipt['lens_pixel_instructions']=stats.num_pixel_shader_instructions
save(m)

src=P/(key+'.png')
dest=ROOT/'Content'/icon_pkg.removeprefix('/Game/')
dest=dest.with_suffix('.png')
prior=dest.read_bytes() if dest.exists() else None
task=u.AssetImportTask();task.filename=str(src);task.destination_path=icon_dir;task.destination_name=key
task.factory=u.TextureFactory();task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(icon_pkg)
if not task.imported_object_paths or not isinstance(texture,u.Texture2D):
    raise RuntimeError('Peakwatch icon import failed')
texture.set_editor_properties(dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
    compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,srgb=True,never_stream=True,
    mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,max_texture_size=1024,
    address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP))
E.set_metadata_tag(texture,'PeakwatchIconRevision','FramedPhysical20261109')
save(texture)
if (dest.read_bytes() if dest.exists() else None)!=prior:
    raise RuntimeError('Concurrent PNG update retained')
temp=dest.with_suffix('.peakwatch.tmp');temp.write_bytes(src.read_bytes());os.replace(temp,dest)
receipt.update(complete=True,loose_png=str(dest),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
(P/'asset-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('PEAKWATCH_ASSETS_SAVED '+json.dumps(receipt),flush=True)
