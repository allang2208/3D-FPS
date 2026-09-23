"""Import original service-bank finishes, with vertex-localized corrosion."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/AtmosphereV2/Services'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Different project')
if any(p.get_path_name().startswith(BASE+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved service assets')
man=json.loads((ROOT/'Authored/material-manifest.json').read_text());textures={}
for key,filename in man['channels'].items():
    task=u.AssetImportTask();task.filename=filename;task.destination_path=BASE+'/Textures';task.destination_name='T_Service_'+key
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(BASE+'/Textures/T_Service_'+key)
    tex.set_editor_property('srgb',key in ('BaseColor','RustColor'))
    if key=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif key not in ('BaseColor','RustColor'):tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    if not E.save_loaded_asset(tex,False):raise RuntimeError('Cannot save '+key)
    textures[key]=tex
def make(name):
    path=BASE+'/Materials/'+name;mat=u.load_asset(path)
    if not mat:mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.modify();L.delete_all_material_expressions(mat);return mat
def node(klass):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+klass))
def connect(a,ao,b,bi):
    if not L.connect_material_expressions(a,ao,b,bi):raise RuntimeError('Material input '+bi)
def output(a,ao,prop):
    if not L.connect_material_property(a,ao,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
def constant(value):
    n=node('Constant');n.set_editor_property('r',value);return n
def color(value):
    n=node('Constant3Vector');n.set_editor_property('constant',u.LinearColor(*value,1));return n
def finish():
    L.layout_material_expressions(mat);L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save')
mat=make('M_Service_Paint');samples={}
for key,tex in textures.items():
    n=node('TextureSample');n.set_editor_property('texture',tex)
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key in ('BaseColor','RustColor') else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    samples[key]=n
vc=node('VertexColor');mask=node('Multiply');connect(vc,'R',mask,'A');connect(samples['AgeMask'],'R',mask,'B')
mix=node('LinearInterpolate');connect(samples['BaseColor'],'RGB',mix,'A');connect(samples['RustColor'],'RGB',mix,'B');connect(mask,'',mix,'Alpha');output(mix,'','BASE_COLOR')
rough=node('LinearInterpolate');connect(samples['Roughness'],'R',rough,'A');connect(constant(.89),'',rough,'B');connect(mask,'',rough,'Alpha');output(rough,'','ROUGHNESS')
metal=node('LinearInterpolate');connect(samples['Metallic'],'R',metal,'A');connect(constant(0),'',metal,'B');connect(mask,'',metal,'Alpha');output(metal,'','METALLIC')
output(samples['Normal'],'RGB','NORMAL');output(constant(.36),'','SPECULAR');finish()
mat=make('M_Service_Hardware');output(color((.085,.10,.095)),'','BASE_COLOR');output(constant(.78),'','METALLIC');output(constant(.48),'','ROUGHNESS')
n=node('TextureSample');n.set_editor_property('texture',textures['Normal']);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);output(n,'RGB','NORMAL');finish()
mat=make('M_Service_Gasket');output(color((.008,.011,.009)),'','BASE_COLOR');output(constant(.92),'','ROUGHNESS');output(constant(.18),'','SPECULAR');finish()
(ROOT/'Receipts').mkdir(exist_ok=True)
(ROOT/'Receipts/materials.json').write_text(json.dumps(dict(stage='materials_saved',materials=['M_Service_Paint','M_Service_Hardware','M_Service_Gasket']),indent=2))
print('DUNGEON_SERVICE_MATERIALS_SAVED')
