"""Save quiet 2011-only surface assets and bind current attachment meshes."""
import importlib.util,json,shutil
from pathlib import Path
import unreal as u

O=Path(__file__).parent;P=O.parents[1]
spec=importlib.util.spec_from_file_location('pv_surface_contract',O/'surface_contract.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
D=C.D;E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong production project')
inputs=json.loads((O/'Input/current.json').read_text(encoding='utf8'))
recipe=json.loads((O/'texture_recipe.json').read_text(encoding='utf8'))['textures']
WET='/Game/Weapons/PistolGripSurface20260927/DA_PistolGripSurfaceWetMaterials'
ws={p:entry for p,entry in inputs['materials'].items() if p.startswith('/Game/Weapons/PitViper2011/') and entry['base'].split('.')[0]==C.WS_BASE}
textures_flat=[recipe['Grain'],*recipe['TacticalMetal'].values(),*[file for files in recipe['Grips'].values() for file in files.values()],*recipe['Vip'].values()]
targets={p.split('.')[0] for p in ws}|{WET}|set(C.MATERIAL_REMAP.values())
targets.update(D+'/Textures/'+Path(file).stem for file in textures_flat)
targets.update(p.split('.')[0] for p,slots in inputs['meshes'].items() if any((s['material'] or '').split('.')[0] in C.MATERIAL_REMAP for s in slots))
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets&dirty:raise RuntimeError('Preserve unsaved 2011 surface packages '+str(sorted(targets&dirty)))
for path in targets:
    file=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'Before/Content'/(path.removeprefix('/Game/')+'.uasset')
    if file.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
catalog=P/'Content/ColdSteelData/gunsmith.json';backup=O/'Before/gunsmith.json'
if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(catalog,backup)
receipt={'saved':[],'materials':{},'meshes':{},'game_tested':False,'acceptance_rendered':False,'native_build_required':False}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing surface dependency '+path)
    return a
def save(a):
    if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Cannot save '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record();return a
def texture(file,kind):
    task=u.AssetImportTask();task.filename=file;task.destination_path=D+'/Textures';task.destination_name=Path(file).stem
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);tex=load(task.destination_path+'/'+task.destination_name)
    tex.srgb=kind=='BaseColor'
    tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_GRAYSCALE if kind=='Roughness' else u.TextureCompressionSettings.TC_BC7
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
    tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE;tex.filter=u.TextureFilter.TF_TRILINEAR
    tex.never_stream=False
    if kind=='Normal':tex.flip_green_channel=True
    E.set_metadata_tag(tex,'SurfaceAuthoring','2011 only: preserved structural relief; reduced random high-frequency microfinish')
    return save(tex)
grain=texture(recipe['Grain'],'Grain')
metal={kind:texture(file,kind) for kind,file in recipe['TacticalMetal'].items()}
grips={part:{kind:texture(file,kind) for kind,file in files.items()} for part,files in recipe['Grips'].items()}
vip={kind:texture(file,kind) for kind,file in recipe['Vip'].items()}
for path,entry in ws.items():
    material=load(path);C.apply_ws(u,material);save(material)
    receipt['materials'][path]={'parameters':C.ws_parameters(path),'grain':grain.get_path_name(),'parent_preserved':True};record()
created={}
for old,new in C.MATERIAL_REMAP.items():
    mat=u.load_asset(new) or A.duplicate_asset(Path(new).name,str(Path(new).parent).replace('\\','/'),load(old))
    if not isinstance(mat,u.Material):raise RuntimeError('Expected private material graph '+new)
    if old==C.VIP_OLD:replacement=vip
    elif '/PistolGripSurface20260927/' in old:replacement=grips[old.rsplit('/M_',1)[1]]
    else:replacement=metal
    for node in L.get_material_expressions(mat):
        if not isinstance(node,u.MaterialExpressionTextureSample):continue
        source=node.texture.get_path_name() if node.texture else ''
        if old.endswith('_Body') and '/T_M4_Receiver_' not in source and '/T_PV2011_TacticalMetal_' not in source:continue
        for kind,tex in replacement.items():
            if source.split('.')[0].endswith('_'+kind):
                node.texture=tex
                node.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE if kind=='Roughness' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
                break
    L.recompile_material(mat);E.set_metadata_tag(mat,'WeaponSurfaceHost','2011 quiet finish; original optical/structural/wetness branches retained')
    save(mat);created[old]=mat;receipt['materials'][new]={'source':old,'textures':{k:v.get_path_name() for k,v in replacement.items()}};record()
for path in inputs['meshes']:
    mesh=load(path)
    if not isinstance(mesh,u.StaticMesh):continue
    slots=list(mesh.static_materials);changed=False
    for i,slot in enumerate(slots):
        old=slot.material_interface.get_path_name().split('.')[0] if slot.material_interface else ''
        if old in created:slot.material_interface=created[old];slots[i]=slot;changed=True
    if changed:
        mesh.set_editor_property('static_materials',slots);save(mesh)
        receipt['meshes'][path]={'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}};record()
library=load(WET);mapping=dict(library.get_editor_property('wet_materials'))
for mat in created.values():
    if 'WeaponWetness' in [str(name) for name in L.get_scalar_parameter_names(mat)]:mapping[mat.get_path_name()]=mat
library.set_editor_property('wet_materials',mapping);save(library)
C.publish_bindings()
receipt.update(status='imported_and_saved',catalog_published=True,scope='2011 and its modifications only',shared_master_changed=False)
record();print('PIT_VIPER_QUIET_SURFACES_IMPORTED_AND_SAVED',len(receipt['saved']),flush=True)
