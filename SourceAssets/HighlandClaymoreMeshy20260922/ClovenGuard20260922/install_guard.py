"""Import the exclusive guard and merge only its catalog entries."""
import json,os,shutil
from pathlib import Path
from datetime import datetime
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
spec=json.loads((P/'production.json').read_text(encoding='utf-8'));D=spec['ue_folder']
E,L,A=u.MaterialEditingLibrary,u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:raise RuntimeError('End active play before importing the guard.')
stamp=datetime.now().strftime('%Y%m%d-%H%M%S');before=P/'Before'/stamp;before.mkdir(parents=True,exist_ok=True)
receipt={'time':stamp,'editor_pid':os.getpid(),'assets':[],'complete':False,'tested':False}
def record():(P/'install_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(obj):
    if not L.save_loaded_asset(obj,False):raise RuntimeError('Asset save failed: '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name());record()
def node(mat,cls,**props):
    n=E.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,pin,b,target):
    if not E.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material connection failed: '+target)
def output(n,target,pin=''):
    if not E.connect_material_property(n,pin,target):raise RuntimeError('Material output failed: '+str(target))
def constant(mat,val,prop):output(node(mat,u.MaterialExpressionConstant,r=val),prop)
def color(mat,rgb,prop):output(node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rgb,1)),prop)
materials={'M_HighlandClaymoreSurface':u.load_asset('/Game/Weapons/HighlandClaymore20260922/Materials/M_HighlandClaymoreSurface')}
if not materials['M_HighlandClaymoreSurface']:raise RuntimeError('Highland native PBR is missing.')
for name,base,metal,rough in [('M_Cloven_Recess',[.018,.022,.025],.88,.42),('M_Cloven_Inlay',[.18,.006,.003],.48,.29)]:
    mat=u.load_asset(D+'/'+name)
    if mat is None:
        mat=A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
        color(mat,base,u.MaterialProperty.MP_BASE_COLOR);constant(mat,metal,u.MaterialProperty.MP_METALLIC);constant(mat,rough,u.MaterialProperty.MP_ROUGHNESS)
        if name=='M_Cloven_Inlay':
            mat.set_editor_property('two_sided',True)
            charge=node(mat,u.MaterialExpressionScalarParameter,parameter_name='GuardCharge',default_value=0.)
            wave=node(mat,u.MaterialExpressionScalarParameter,parameter_name='GuardWave',default_value=0.)
            vertex=node(mat,u.MaterialExpressionVertexColor);uv=node(mat,u.MaterialExpressionTextureCoordinate)
            pins=[]
            for key in ['Charge','Wave','Travel','UV']:
                pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
            custom=node(mat,u.MaterialExpressionCustom,inputs=pins,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                description='Cloven parry inlays: center-out pulse and soft transverse glow',
                code='float edge=smoothstep(0.02,0.20,UV.y)*(1-smoothstep(0.80,0.98,UV.y)); float front=smoothstep(Travel-0.08,Travel+0.08,Wave); return float3(1.0,0.018,0.006)*edge*(0.07+4.5*Charge*front);')
            for n,pin,key in [(charge,'','Charge'),(wave,'','Wave'),(vertex,'R','Travel'),(uv,'','UV')]:wire(n,pin,custom,key)
            output(custom,u.MaterialProperty.MP_EMISSIVE_COLOR)
        errors=list(E.recompile_material(mat))
        if errors:raise RuntimeError('Guard material compilation failed: '+str(errors))
        E.get_statistics(mat)
    save(mat);materials[name]=mat

def imported(file,name,folder,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset or not task.imported_object_paths:raise RuntimeError('Import failed: '+str(file))
    return asset
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False
options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
cfg=options.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
cfg.vertex_color_import_option=u.VertexColorImportOption.REPLACE
mesh=u.load_asset(D+'/'+spec['mesh']) or imported(P/'Export'/(spec['mesh']+'.fbx'),spec['mesh'],D,options)
slots=list(mesh.static_materials)
for slot in slots:
    name=str(slot.material_slot_name)
    if name not in materials:raise RuntimeError('Unmapped authored material slot: '+name)
    slot.material_slot_name=name;slot.material_interface=materials[name]
mesh.static_materials=slots
static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);settings=static.get_lod_build_settings(mesh,0)
settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_full_precision_u_vs=True
static.set_lod_build_settings(mesh,0,settings);save(mesh)

png=DATA/'AttachmentIcons20260913'/spec['icon']
if png.exists():shutil.copy2(png,before/png.name)
shutil.copy2(P/'Icons'/spec['icon'],png)
icon=imported(png,png.stem,'/Game/ColdSteelData/AttachmentIcons20260913')
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);icon.set_editor_property('srgb',True)
save(icon)

def update_catalog(file,mutate):
    path=DATA/file;old=path.read_bytes();catalog=json.loads(old.decode('utf-8-sig'))
    mutate(catalog)
    if path.read_bytes()!=old:raise RuntimeError('Concurrent catalog edit preserved: '+str(path))
    (before/file).write_bytes(old);tmp=path.with_suffix('.cloven.tmp')
    tmp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)

def module(catalog):
    catalog['slots']['guard'][spec['option']]={**spec['mount'],'mesh':mesh.get_path_name(),'appearance':'高地专属 · 厚根裂角与赤红承锋嵌纹'}
update_catalog('highland-claymore-modules.json',module)
def gameplay(catalog):
    column=next(c for c in catalog['columns'] if c['key']=='guard')
    s=spec['stats'];seconds=s['cloven_seconds'];physical=round((s['cloven_physical_mult']-1)*100);tough=round((s['cloven_toughness_mult']-1)*100)
    option={'id':spec['option'],'name':'裂角护手','weapons':[spec['weapon']],
        'description':'高地双手剑专属双角护手。承接来刃，弹反后以无需蓄力的重斩还击。',
        'effects':[{'text':f"格挡体力消耗 -{round((1-s['block_stamina_mult'])*100)}%",'benefit':1},
                   {'text':f'成功弹反后{seconds:g}秒内，下一次普通攻击替换为无需蓄力的重击','benefit':1},
                   {'text':f'该次重击物理伤害 +{physical}% · 韧性伤害 +{tough}%','benefit':1},
                   {'text':'按重击消耗体力，发起即消耗；最多保留一次，弹反刷新时间','benefit':0}],
        'stats':s}
    existing=next((o for o in column['options'] if o['id']==spec['option']),None)
    if existing is None:column['options'].append(option)
    else:existing.update(option)
update_catalog('melee-gunsmith.json',gameplay)
receipt['complete']=True;receipt['mesh']=mesh.get_path_name();receipt['option']=spec['option'];receipt['native_build_required']=True;record()
print('HIGHLAND_CLOVEN_GUARD_INSTALLED '+mesh.get_path_name())
