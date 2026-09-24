"""Install the entrance PBR materials and replace only the freight Lift mesh."""
import json
import re
import shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/FreightDoor20260923'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Unexpected Unreal project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('PIE is active; preserve the running game and defer entrance import')
manifest=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
item=manifest['objects'][0];path=item['asset']
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
if any(p==path or p.startswith(BASE+'/') for p in dirty):
    raise RuntimeError('Preserve unsaved changes to entrance assets')
old=u.load_asset(path)
if old is None:raise RuntimeError('Installed freight entrance missing')
body=old.get_editor_property('body_setup')
settings=dict(nanite=old.get_editor_property('nanite_settings').copy(),
    collision=body.get_editor_property('collision_trace_flag'),
    double_sided=body.get_editor_property('double_sided_geometry'),
    physical_material=body.get_editor_property('phys_material'))
backup=ROOT/'Sources/InstalledBeforeRepair'/('SM_RS_FreightTransfer_Lift.uasset')
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset'),backup)
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=dict(stage='materials',textures=[],materials=[],meshes=[],map_modified=False,
    runtime_tested=False,rendered=False)
receipt_file=ROOT/'Receipts/import.json'
def record():receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
record()
textures={}
for channel,filename in manifest['maps'].items():
    task=u.AssetImportTask();task.filename=filename
    task.destination_path=BASE+'/Textures';task.destination_name='T_FreightSurface_'+channel
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task])
    texture=u.load_asset(task.destination_path+'/'+task.destination_name)
    if not texture:raise RuntimeError('Texture import failed '+channel)
    texture.set_editor_property('srgb',False)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP
        if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS)
    if channel=='Normal':texture.set_editor_property('flip_green_channel',False)
    save(texture);textures[channel]=texture
    receipt['textures'].append(texture.get_path_name());record()

finishes={
    'FreightCoat':(.04,.62), 'FreightTrack':(.92,.32), 'FreightGate':(.46,.54),
    'FreightPanel':(.03,.49), 'FreightRubber':(0,.88), 'FreightAmber':(0,.28),
    'FreightLegend':(0,.67), 'FreightPlate':(.22,.48), 'FreightWarning':(0,.65),
}
materials={}
for key,color in manifest['colors'].items():
    mat_path=BASE+'/Materials/M_'+key
    mat=u.load_asset(mat_path)
    if mat:L.delete_all_material_expressions(mat)
    else:mat=A.create_asset('M_'+key,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    def node(cls):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+cls))
    def link(a,pin,b,input_name):
        if not L.connect_material_expressions(a,pin,b,input_name):
            raise RuntimeError('Material connection failed '+key+' '+input_name)
    def const(value):
        if isinstance(value,(list,tuple)):
            n=node('Constant3Vector');n.constant=u.LinearColor(*value,1)
        else:n=node('Constant');n.r=value
        return n
    def op(cls,a,b,a_pin='',b_pin=''):
        n=node(cls);link(a,a_pin,n,'A');link(b,b_pin,n,'B');return n
    def mix(a,b,alpha,a_pin='',b_pin='',alpha_pin=''):
        n=node('LinearInterpolate');link(a,a_pin,n,'A');link(b,b_pin,n,'B')
        link(alpha,alpha_pin,n,'Alpha');return n
    def out(n,prop,pin=''):
        if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+prop)):
            raise RuntimeError('Material output failed '+prop)
    metal,rough=finishes[key]
    base=const(color);metal_node=const(metal);rough_node=const(rough)
    if key not in ('FreightLegend','FreightAmber','FreightRubber'):
        detail=node('TextureSample');detail.texture=textures['Detail']
        detail.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
        normal=node('TextureSample');normal.texture=textures['Normal']
        normal.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL
        vc=node('VertexColor')
        grain=op('Add',const(.92),op('Multiply',detail,const(.16),'G'))
        base=op('Multiply',base,grain)
        dirt=op('Multiply',base,const([.61,.58,.52]))
        base=mix(base,dirt,vc,alpha_pin='R')
        scratch=op('Add',const(.20),op('Multiply',detail,const(.65),'B'))
        wear=op('Multiply',vc,scratch,'G')
        base=mix(base,const([.27,.285,.27]),wear)
        metal_node=mix(metal_node,const(.88),wear)
        rough_node=op('Add',rough_node,op('Multiply',op('Subtract',detail,const(.5),'G'),const(.18)))
        rough_node=mix(rough_node,const(.32),wear)
        if key in ('FreightCoat','FreightGate','FreightTrack','FreightWarning'):
            rust=op('Multiply',op('Multiply',vc,detail,'B','R'),const(.72))
            base=mix(base,const([.13,.051,.019]),rust)
            rough_node=mix(rough_node,const(.89),rust)
            metal_node=mix(metal_node,const(0),rust)
        scale=op('Multiply',normal,const([.45,.45,1]),'RGB')
        unit=node('Normalize');link(scale,'',unit,'VectorInput');out(unit,'NORMAL')
    out(base,'BASE_COLOR');out(metal_node,'METALLIC');out(rough_node,'ROUGHNESS')
    out(const(.34 if key!='FreightRubber' else .20),'SPECULAR')
    if key=='FreightAmber':out(const([c*2.2 for c in color]),'EMISSIVE_COLOR')
    L.layout_material_expressions(mat);L.recompile_material(mat);save(mat)
    materials['RS_'+key]=mat;receipt['materials'].append(mat_path);record()

receipt['stage']='mesh_import';record()
task=u.AssetImportTask();task.filename=item['fbx']
task.destination_path=path.rsplit('/',1)[0];task.destination_name=item['name']
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
options.import_as_skeletal=False;options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=options.static_mesh_import_data
data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task.options=options;task.factory=u.FbxFactory()
A.import_asset_tasks([task]);mesh=u.load_asset(path)
if not mesh or not task.get_objects():raise RuntimeError('Entrance mesh import failed')
for index,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
    mesh.set_material(index,materials[key])
body=mesh.get_editor_property('body_setup')
body.set_editor_property('collision_trace_flag',settings['collision'])
body.set_editor_property('double_sided_geometry',settings['double_sided'])
body.set_editor_property('phys_material',settings['physical_material'])
mesh.set_editor_property('nanite_settings',settings['nanite']);save(mesh)
receipt['meshes'].append(path);receipt['stage']='saved';record()
print('FREIGHT_ENTRANCE_IMPORTED',json.dumps(receipt),flush=True)
