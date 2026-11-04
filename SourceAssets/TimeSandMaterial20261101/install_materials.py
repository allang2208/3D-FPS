"""Extend current PBR masters with mode 7 and save the replicated echo visual."""
from pathlib import Path
import json,shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
REVISION='TimeSandMaterial20261101V1'
DEST='/Game/Weapons/AzureRunesword20260913/TimeSand20261101'
MASTERS=['/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
 '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold']
if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('PIE is running; preserve the current session.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    path=package.get_path_name()
    if path in MASTERS or path.startswith(DEST):raise RuntimeError('Unsaved target package '+path)

def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n

def wire(src,dst,pin,channel=''):
    names=[str(n) for n in L.get_material_expression_input_names(dst)]
    norm=lambda s:s.replace(' ','').replace('_','').lower()
    actual=next((n for n in names if norm(n)==norm(pin)),None)
    if actual is None and pin=='Input' and len(names)==1:actual=names[0]
    if actual is None or not L.connect_material_expressions(src,channel,dst,actual):raise RuntimeError('Material pin '+pin+' '+str(names))

def out(n,name,channel=''):
    if not L.connect_material_property(n,channel,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Material output '+name)

def save(m):
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation failed: '+str(errors))
    E.set_metadata_tag(m,'TimeSandRevision',REVISION)
    if not E.save_loaded_asset(m,False):raise RuntimeError('Material save failed '+m.get_path_name())

GRAIN='''float w=1-saturate(Mask*3.0);
float phase=P.x*2.1+sin(P.z*.09-TimeSandTime*.22)*1.8;
float stream=.5+.5*sin(phase);
float2 q=float2(P.x*10+sin(P.z*.08)*2,P.z*8-TimeSandTime*3);
float2 cell=floor(q), f=frac(q)-.5;
float seed=frac(sin(dot(cell,float2(127.1,311.7)))*43758.5453);
float footprint=max(length(ddx(q)),length(ddy(q)));
float filter=exp2(-.8*footprint*footprint);
float sand=exp(-dot(f,f)*65)*step(.74,seed)*(.35+.65*stream)*filter;
'''
RECIPES={
 'MP_BASE_COLOR':GRAIN+'''float shade=clamp(dot(Base,float3(.2126,.7152,.0722))/.32,.72,1.12);
float3 gold=float3(.29,.135,.032)*(.86+.14*stream)+float3(.62,.38,.10)*sand;
return lerp(Base,gold*shade,w);''',
 'MP_ROUGHNESS':GRAIN+'''return lerp(Base,clamp(.29-.09*sand+(Base-.35)*.10,.17,.44),w);''',
 'MP_NORMAL':GRAIN+'''float detail=sin(phase)*.008+sand*.014;
return normalize(lerp(Base,normalize(float3(Base.xy+float2(detail,detail*.3),Base.z)),w));''',
 'MP_METALLIC':'return lerp(Base,.93,1-saturate(Mask*3.0));'}

saved=[]
for path in MASTERS:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing current master '+path)
    if E.get_metadata_tag(mat,'TimeSandRevision')==REVISION:
        saved.append({'asset':path,'already_current':True});continue
    source=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/source.relative_to(ROOT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    finishes=[n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom)
              and str(n.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    if len(finishes)!=4:raise RuntimeError('Current blade finish graph missing '+path)
    time=node(mat,u.MaterialExpressionTime,desc=REVISION+' flowing sand')
    for field,recipe in RECIPES.items():
        finish=next(n for n in finishes if field+':' in str(n.get_editor_property('desc')))
        if field!='MP_METALLIC':
            inputs=list(finish.get_editor_property('inputs'))
            pin=u.CustomInput();pin.set_editor_property('input_name','TimeSandTime');inputs.append(pin)
            finish.set_editor_property('inputs',inputs);wire(time,finish,'TimeSandTime')
        code='// '+REVISION+'\nif(Mode>6.5 && Mode<7.5){\n'+recipe+'\n}\n'
        finish.set_editor_property('code',code+finish.get_editor_property('code'))
    save(mat);saved.append({'asset':path,'saved':True,'mode':7})

path=DEST+'/M_TimeSandEcho'
mat=u.load_asset(path) if E.does_asset_exist(path) else None
if mat and E.get_metadata_tag(mat,'TimeSandRevision')!=REVISION:raise RuntimeError('Unowned echo material '+path)
if not mat:
    mat=A.create_asset('M_TimeSandEcho',DEST,u.Material,u.MaterialFactoryNew())
    for key,value in [('blend_mode',u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE),
                      ('shading_model',u.MaterialShadingModel.MSM_UNLIT),('two_sided',True),
                      ('used_with_instanced_static_meshes',True),('automatically_set_usage_in_editor',False)]:
        mat.set_editor_property(key,value)
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    data=node(mat,u.MaterialExpressionPerInstanceCustomData,data_index=0,const_default_value=0.)
    age=node(mat,u.MaterialExpressionVertexInterpolator);wire(data,age,'Input')
    shader=node(mat,u.MaterialExpressionCustom,desc=REVISION+' delayed cut and dissolving sand',
        code=(P/'echo.hlsl').read_text(),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins=[]
    for name in ['UV','Age']:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    shader.set_editor_property('inputs',pins);wire(uv,shader,'UV');wire(age,shader,'Age')
    depth=node(mat,u.MaterialExpressionDepthFade)
    distance=node(mat,u.MaterialExpressionConstant,r=1.);wire(distance,depth,'FadeDistance')
    color=node(mat,u.MaterialExpressionMultiply);wire(shader,color,'A');wire(depth,color,'B')
    transmission=node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(1,1,1,1))
    surface=node(mat,u.MaterialExpressionSubstrateUnlitBSDF)
    wire(color,surface,'EmissiveColor');wire(transmission,surface,'TransmittanceColor')
    out(surface,'FRONT_MATERIAL');out(color,'EMISSIVE_COLOR')
    save(mat)
saved.append({'asset':path,'saved':True})

icons=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
name='ue_rune_sword_blade_material_time_sand_gold'
destination=icons/(name+'.png');shutil.copy2(P/'time_sand_gold.png',destination)
task=u.AssetImportTask()
task.filename=str(destination);task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913'
task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
A.import_asset_tasks([task]);icon=u.load_asset(task.destination_path+'/'+name)
if not icon:raise RuntimeError('Time sand icon import failed')
for key,value in [('lod_group',u.TextureGroup.TEXTUREGROUP_UI),('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON),
                  ('srgb',True),('never_stream',True),('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)]:
    icon.set_editor_property(key,value)
if not E.save_loaded_asset(icon,False):raise RuntimeError('Time sand icon save failed')
(P/'material-receipt.json').write_text(json.dumps({'revision':REVISION,'materials':saved,'icon':icon.get_path_name(),
    'gameplay_tested':False,'preview_rendered':False},indent=2)+'\n',encoding='utf8')
print('TIME_SAND_MATERIALS_SAVED',json.dumps(saved))
