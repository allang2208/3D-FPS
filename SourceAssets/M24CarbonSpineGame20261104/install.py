"""Install the fitted R1 stock in FPSGAME through the existing UE batch gate."""
from pathlib import Path
import json,hashlib
import unreal as u

root=Path(__file__).resolve().parent
project=root.parents[1]
active_project=Path(u.Paths.project_dir()).resolve()
stage=project/'Saved/AssetStaging/M24CarbonSpine20261104/Project'
D='/Game/Weapons/M24/CarbonSpine20261104'
icons='/Game/ColdSteelData/AttachmentIcons20260913'
icon='ue_m24_stock_m24_carbon_spine_stock'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
geometry=json.loads((root/'geometry.json').read_text())
seats=json.loads((root/'Inputs/seats.json').read_text())
receipt_file=root/('stage_receipt.json' if active_project==stage else 'install_receipt.json')
receipt={'complete':False,'saved':[],'models':{},'weave_pitch':1.,'gameplay_tested':False}
if receipt_file.is_file():receipt=json.loads(receipt_file.read_text())
if receipt['complete']:raise RuntimeError('This edition has already been published')
def record():
    receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def package(path):return active_project/'Content'/(path.removeprefix('/Game/')+'.uasset')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    path=a.get_path_name()
    E.set_metadata_tag(a,'M24CarbonSpineEdition','R1-Fitted-20261104')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+path)
    if path not in receipt['saved']:receipt['saved'].append(path)
    record()
def generated_ui(path):
    if path not in (icons+'/'+icon,icons+'/FramedFirearms/'+icon):return False
    a=u.load_asset(path)
    if not a or not isinstance(a,u.Texture2D):return False
    imported=a.get_editor_property('asset_import_data').get_first_filename()
    expected=package(path).with_suffix('.png')
    return bool(imported) and Path(imported).resolve()==expected.resolve()
def own(path):
    if not E.does_asset_exist(path):return None
    a=load(path)
    if E.get_metadata_tag(a,'M24CarbonSpineEdition')!='R1-Fitted-20261104' and not generated_ui(path):raise RuntimeError('Occupied asset '+path)
    return a
if active_project not in (project,stage):raise RuntimeError('Wrong project')
lv=None if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else u.get_editor_subsystem(u.LevelEditorSubsystem)
if lv and lv.is_in_play_in_editor():raise RuntimeError('PIE active. Existing world preserved.')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path in dirty:
    if path.startswith(D+'/'):
        a=u.load_asset(path)
        if not generated_ui(path) and (not a or E.get_metadata_tag(a,'M24CarbonSpineEdition')!='R1-Fitted-20261104'):raise RuntimeError('Unsaved '+path)
for s in seats.values():
    if s['asset'] in dirty or hashlib.sha256(package(s['asset']).read_bytes()).hexdigest()!=s['sha256']:
        raise RuntimeError('Receiver geometry changed during authoring: '+s['asset'])

def imported(src,dest,name,options=None):
    path=dest+'/'+name
    if own(path):return load(path)
    task=u.AssetImportTask();task.filename=str(src);task.destination_path=dest;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    else:task.factory=u.TextureFactory()
    A.import_asset_tasks([task])
    a=load(path);E.set_metadata_tag(a,'M24CarbonSpineEdition','R1-Fitted-20261104');return a
def texture(src,dest,name,kind):
    t=imported(src,dest,name)
    t.compression_settings={'base':u.TextureCompressionSettings.TC_DEFAULT,'mask':u.TextureCompressionSettings.TC_MASKS,'normal':u.TextureCompressionSettings.TC_NORMALMAP,'ui':u.TextureCompressionSettings.TC_EDITOR_ICON}[kind]
    t.lod_group=u.TextureGroup.TEXTUREGROUP_UI if kind=='ui' else u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
    t.srgb=kind in ('ui','base');t.never_stream=kind=='ui';save(t);return t
art=root.parent/'M24CarbonSpineConcept/ArtSource'
tex={'base':texture(root/'Exports/T_CS_Weave_B.png',D+'/Textures','T_CS_Weave_B','base'),
     'mask':texture(root/'Exports/T_CS_Weave_H.png',D+'/Textures','T_CS_Weave_H','mask'),
     'normal':texture(root/'Exports/T_CS_Weave_N.png',D+'/Textures','T_CS_Weave_N','normal')}
def make_mat(name):
    path=D+'/Materials/'+name;m=own(path)
    if not m:m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    if not m:raise RuntimeError('Could not create '+path)
    E.set_metadata_tag(m,'M24CarbonSpineEdition','R1-Fitted-20261104');L.delete_all_material_expressions(m);return m
def node(m,cls,x,y,**props):
    n=L.create_material_expression(m,cls,x,y)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def prop(n,output,label):
    field=next((k for k in dir(u.MaterialProperty) if k.replace('_','')==('MP_'+label).replace('_','')),None)
    if not field or not L.connect_material_property(n,output,getattr(u.MaterialProperty,field)):raise RuntimeError('Material property '+label+' '+str(field))
def link(n,out,target,pin):
    if not L.connect_material_expressions(n,out,target,pin):raise RuntimeError('Connection refused '+pin)
def scalar(m,label,value,x,y):
    return node(m,u.MaterialExpressionScalarParameter,x,y,parameter_name=label,default_value=value)
def master():
    m=make_mat('M_CS_WovenResin')
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLEAR_COAT)
    m.set_editor_property('use_material_attributes',True)
    attrs=node(m,u.MaterialExpressionMakeMaterialAttributes,0,140)
    pins={str(k).replace(' ','').lower():str(k) for k in L.get_material_expression_input_names(attrs)}
    def channel(n,out,name):
        link(n,out,attrs,pins[name.lower()])
    def sample(kind,typ,y):
        return node(m,u.MaterialExpressionTextureSample,-800,y,texture=tex[kind],sampler_type=typ)
    color=sample('base',u.MaterialSamplerType.SAMPLERTYPE_COLOR,0)
    h=sample('mask',u.MaterialSamplerType.SAMPLERTYPE_MASKS,260)
    normal=sample('normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,570)
    brightness=scalar(m,'WeaveBrightness',.68,-700,150)
    mult=node(m,u.MaterialExpressionMultiply,-400,0)
    link(color,'RGB',mult,'A');link(brightness,'',mult,'B');channel(mult,'','BaseColor')
    rough=node(m,u.MaterialExpressionLinearInterpolate,-320,280,const_a=.30,const_b=.45)
    link(h,'R',rough,'Alpha');channel(rough,'','Roughness');channel(normal,'RGB','Normal')
    channel(node(m,u.MaterialExpressionConstant,-310,480,r=.20),'','Metallic')
    channel(scalar(m,'ResinCoat',.30,-330,620),'','ClearCoat')
    channel(node(m,u.MaterialExpressionConstant,-310,750,r=.25),'','ClearCoatRoughness')
    prop(attrs,'','MATERIAL_ATTRIBUTES')
    L.recompile_material(m);save(m);return m
carbon=master()
solid=make_mat('M_CS_Trim')
tint=node(solid,u.MaterialExpressionVectorParameter,-300,0,parameter_name='FinishColor',default_value=u.LinearColor(.026,.031,.030,1))
prop(tint,'','BASE_COLOR');prop(scalar(solid,'Metallic',.05,-300,150),'','METALLIC');prop(scalar(solid,'Roughness',.56,-300,340),'','ROUGHNESS')
L.recompile_material(solid);save(solid)
def instance(label,parent,params,color=None):
    name='MI_'+label;mi=own(D+'/Materials/'+name)
    if not mi:mi=A.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,parent)
    for k,v in params.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
    if color:L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*color,1))
    L.update_material_instance(mi);save(mi);return mi
materials={}
for label,level,coat in [('CS_WeaveBody',.68,.30),('CS_WeaveSpine',.39,.24),('CS_WeaveCrown',.60,.27)]:
    materials[label]=instance(label,carbon,dict(WeaveBrightness=level,ResinCoat=coat))
trim={'CS_Pad':((.024,.029,.029),0,.68),'CS_Cheek':((.042,.050,.049),.02,.55),'CS_Dark':((.014,.020,.021),.29,.44),'CS_Metal':((.080,.093,.090),.74,.31),'CS_Index':((.39,.43,.39),.52,.37)}
for label,(color,metal,rough) in trim.items():materials[label]=instance(label,solid,dict(Metallic=metal,Roughness=rough),color)
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for kind,model in geometry['models'].items():
        filename=root/'Exports'/model['fbx']
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
        imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        mesh=imported(filename,D+'/Meshes',filename.stem,opt)
        materials['CS_Receiver']=load(model['material'])
        for i,slot in enumerate(mesh.static_materials):
            label=str(slot.material_slot_name);mesh.set_material(i,materials[label])
        sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sub.set_lod_build_settings(mesh,0,bs)
        lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False
        lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))]
        sub.set_lods(mesh,lod)
        if not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):raise RuntimeError('Tangent authoring '+kind)
        E.set_metadata_tag(mesh,'Source',str(root/'M24_CarbonSpine_Fitted.blend'))
        save(mesh);receipt['models'][kind]={'mesh':mesh.get_path_name(),'receiver_finish':model['material'],'interface_points':model['interface_points'],'shoulder_y_m':model['shoulder_y_m']};record()
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
for where in [icons,icons+'/FramedFirearms']:
    file=project/'Content'/where.removeprefix('/Game/')/(icon+'.png')
    texture(file,where,icon,'ui')
receipt['complete']=True;record()
print('M24_CARBON_SPINE_SAVED',len(receipt['saved']),flush=True)
