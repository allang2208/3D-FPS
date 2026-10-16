"""Save the A762 neutral-normal repair through the existing editor bridge.

Only misused DefaultNormal inputs change. No geometry, finish scalar, structural
normal, optical material, parent graph, weather behaviour or gameplay changes.
"""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
if Path(u.Paths.project_dir()).resolve()!=P:raise RuntimeError('Wrong project')
R=json.loads((O/'recipe.json').read_text());C=json.loads((O/'capture.json').read_text())
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level and level.is_in_play_in_editor():raise RuntimeError('Stop the existing PIE before saving; do not launch a second editor')
receipt={'version':R['version'],'texture':None,'materials':{},'meshes':{},'live_refresh':[],
         'complete':False,'gameplay_tested':False,'geometry_changed':False,'finish_parameters_changed':False}
if (O/'install_receipt.json').exists():raise RuntimeError('Preserve existing receipt; do not rerun production blindly')
def record():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(path):
 f=O/'Before'/disk(path).relative_to(P/'Content');f.parent.mkdir(parents=True,exist_ok=True)
 if not f.exists():shutil.copy2(disk(path),f)
 return str(f)

# The editor is already open. Respect unsaved work and the captured inputs.
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for t in R['targets']:
 if t['source'].split('.')[0] in dirty or t['destination'] in dirty:raise RuntimeError('Unsaved target '+t['source'])
 if sha(disk(t['source']))!=t['sha256']:raise RuntimeError('Changed material '+t['source'])
 if L.get_material_instance_texture_parameter_value(load(t['source']),'SurfaceNormal').get_path_name()!=t['old_normal']:raise RuntimeError('Changed normal '+t['source'])
 if t['clone'] and E.does_asset_exist(t['destination']):raise RuntimeError('Private copy already exists '+t['destination'])
for path,bindings in R['bindings'].items():
 if path in dirty or sha(disk(path))!=C['assets'][path]['sha256']:raise RuntimeError('Changed mesh '+path)
 slots=load(path).static_materials
 for b in bindings:
  s=slots[b['index']]
  if str(s.material_slot_name)!=b['slot'] or s.material_interface.get_path_name()!=b['before']:raise RuntimeError('Changed binding '+path)
spec=R['texture']
if sha(Path(spec['source']))!=spec['sha256'] or disk(spec['path']).exists():raise RuntimeError('Texture input or saved destination changed')

tex=u.load_asset(spec['path']) if E.does_asset_exist(spec['path']) else None
if tex:
 if Path(tex.get_editor_property('asset_import_data').get_first_filename()).resolve()!=Path(spec['source']).resolve():raise RuntimeError('Unexpected pending texture')
else:
 task=u.AssetImportTask();task.filename=spec['source'];task.destination_path,task.destination_name=spec['path'].rsplit('/',1)
 task.automated=True;task.replace_existing=False;task.save=False
 A.import_asset_tasks([task]);tex=load(spec['path'])
tex.set_editor_property('srgb',False)
tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
tex.set_editor_property('flip_green_channel',False)
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP)
E.set_metadata_tag(tex,'A762SurfaceRepair','Neutral RGB 128,128,255; replaces stone-wall DefaultNormal only')
save(tex);receipt['texture']={'path':tex.get_path_name(),'saved':True,'sha256':sha(disk(tex.get_path_name()))};record()

for t in R['targets']:
 source=load(t['source']);before=None
 if t['clone']:
  mi=E.duplicate_asset(t['source'].split('.')[0],t['destination'])
  if not mi:raise RuntimeError('Private material copy failed '+t['destination'])
 else:
  before=backup(t['source']);mi=source
 L.set_material_instance_texture_parameter_value(mi,'SurfaceNormal',tex)
 L.update_material_instance(mi)
 if L.get_material_instance_texture_parameter_value(mi,'SurfaceNormal')!=tex:raise RuntimeError('Normal setter did not apply '+t['destination'])
 E.set_metadata_tag(mi,'A762SurfaceRepair',R['version']);save(mi)
 receipt['materials'][t['destination']]={'saved':True,'source':t['source'],'private_copy':t['clone'],
     'normal':tex.get_path_name(),'backup':before,'sha256':sha(disk(t['destination']))};record()

for path,bindings in R['bindings'].items():
 before=backup(path);mesh=load(path);slots=mesh.static_materials
 for b in bindings:
  slot=slots[b['index']];slot.material_interface=load(b['after']);slots[b['index']]=slot
 mesh.set_editor_property('static_materials',slots);save(mesh)
 receipt['meshes'][path]={'saved':True,'bindings':bindings,'backup':before,'sha256':sha(disk(path))};record()

# Existing weather MIDs copy texture parameters at construction, so refresh only
# the A762-owned parents already in memory. Do not start or stop PIE or alter wetness.
owned={t['source'] for t in R['targets'] if not t['clone']}
for mid in u.ObjectIterator(u.MaterialInstanceDynamic):
 if mid.parent and mid.parent.get_path_name() in owned:
  mid.set_texture_parameter_value('SurfaceNormal',tex)
  receipt['live_refresh'].append({'mid':mid.get_path_name(),'normal':tex.get_path_name()})
# Shared grip originals stay unchanged for other guns. Rebind only components
# using the three A762 meshes whose slots now reference private material copies.
for comp in u.ObjectIterator(u.StaticMeshComponent):
 mesh=comp.static_mesh
 if not mesh:continue
 bindings=R['bindings'].get(mesh.get_path_name().split('.')[0])
 if not bindings or 'UEDPIE_' not in comp.get_path_name():continue
 for b in bindings:
  m=comp.get_material(b['index'])
  original=m.parent if isinstance(m,u.MaterialInstanceDynamic) else m
  if original and original.get_path_name()==b['before']:
   comp.set_material(b['index'],load(b['after']))
   receipt['live_refresh'].append({'component':comp.get_path_name(),'slot':b['index'],'material':b['after']})
receipt['complete']=True;record()
print('A762_ADS_SURFACE_SAVED',len(receipt['materials']),'materials',len(receipt['meshes']),'bindings',len(receipt['live_refresh']),'existing runtime refreshes; gameplay_tested=False',flush=True)
