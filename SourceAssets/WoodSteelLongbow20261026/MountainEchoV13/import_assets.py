"""Create and save the owned legendary string, PBR finishes, echo shader and UI icon."""
from pathlib import Path
import unreal as u
import json,hashlib,shutil
P=Path(__file__).parent;ROOT=Path('D:/FPS3D/FPSGAME')
DEST='/Game/Weapons/WoodSteelLongbow20261026/MountainEchoV13'
ICON='/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
ICON_NAME='bow_woodsteel_string_highland_mountain_echo'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
author=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active: preserving the running session')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(DEST+'/') or package.get_name()==ICON+'/'+ICON_NAME:
        raise RuntimeError('Preserving unsaved package '+package.get_name())

def save(asset,source=None):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Package save failed '+str(asset))
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print('MOUNTAIN_ECHO_SAVED '+asset.get_path_name(),flush=True)
def existing(name,folder=DEST):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    if E.does_asset_exist(folder+'/'+name):raise RuntimeError('Preserving unowned asset '+folder+'/'+name)
    return None
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,pin,b,slot):
    if not L.connect_material_expressions(a,pin,b,slot):raise RuntimeError('Material connection failed '+slot)
def output(n,pin,prop):
    if not L.connect_material_property(n,pin,prop):raise RuntimeError('Material output failed '+str(prop))
def scalar(m,value):return node(m,u.MaterialExpressionConstant,r=value)
def color(m,value):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))

metal='/Game/Weapons/DarkBow20260925/SingleLensOptics20260927/Textures/T_BowOptic_Metal'
fibre='/Game/Weapons/DarkBow20260925/GripSeriesV20/Textures/T_Bow_Grip_WovenLinen_'
materials={}
for name,finish in author['finishes'].items():
    m=existing(name)
    if not m:
        m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
        output(color(m,finish['color']),'',u.MaterialProperty.MP_BASE_COLOR)
        output(scalar(m,finish['metallic']),'',u.MaterialProperty.MP_METALLIC)
        textile=name.endswith(('Fibre','Graphite','Serving'))
        orm=u.load_asset((fibre if textile else metal)+'ORM')
        normal=u.load_asset((fibre if textile else metal)+'Normal')
        if not orm or not normal:raise RuntimeError('Shared PBR textures unavailable '+name)
        tex=node(m,u.MaterialExpressionTextureSample,texture=orm,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        rough=node(m,u.MaterialExpressionMultiply,const_b=finish['roughness']/(.65 if textile else .34));wire(tex,'G',rough,'A')
        output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
        normals=node(m,u.MaterialExpressionTextureSample,texture=normal,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        output(normals,'RGB',u.MaterialProperty.MP_NORMAL)
        if name.endswith(('Resonance','Gold')):
            charge=node(m,u.MaterialExpressionScalarParameter,parameter_name='StringCharges',default_value=0.,use_custom_primitive_data=True,primitive_data_index=0)
            if name.endswith('Resonance'):
                vertex=node(m,u.MaterialExpressionVertexColor)
                threshold=node(m,u.MaterialExpressionMultiply,const_b=3.);wire(vertex,'R',threshold,'A')
            else:threshold=scalar(m,3.)
            lit=node(m,u.MaterialExpressionIf,equals_threshold=.02)
            wire(charge,'',lit,'A');wire(threshold,'',lit,'B')
            on=color(m,[2.5,1.0,.16] if name.endswith('Resonance') else [.45,.18,.028]);off=color(m,[0,0,0])
            pins=L.get_material_expression_input_names(lit)
            for pin in [pins[2],pins[3]]:wire(on,'',lit,pin)
            wire(off,'',lit,pins[4]);output(lit,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.recompile_material(m);save(m)
    materials[name]=m

name='M_MountainEcho_Arrow';m=existing(name)
if not m:
    m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',False)
    fresnel=node(m,u.MaterialExpressionFresnel,exponent=2.4,base_reflect_fraction=.18)
    emission=node(m,u.MaterialExpressionMultiply);wire(fresnel,'',emission,'A');wire(color(m,[3.4,1.35,.22]),'',emission,'B')
    output(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR);output(scalar(m,.58),'',u.MaterialProperty.MP_OPACITY)
    L.recompile_material(m);save(m)

name=author['mesh'];mesh=existing(name)
if not mesh:
    source=P/'Export'/(name+'.fbx')
    flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    try:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opt.import_mesh=True;opt.import_as_skeletal=True;opt.import_animations=False
        opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
        d=opt.skeletal_mesh_import_data
        d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('update_skeleton_reference_pose',False)
        d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
        task.automated=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
        mesh=u.load_asset(DEST+'/'+name)
        if not mesh:raise RuntimeError('String skeletal import failed')
        slots=list(mesh.get_editor_property('materials'))
        for i,slot in enumerate(slots):
            slot.set_editor_property('material_interface',materials[str(slot.material_slot_name)]);slots[i]=slot
        mesh.set_editor_property('materials',slots)
        # Distance LODs retain the three attachment bones and their weights.
        sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        if not sub.regenerate_lod(mesh,3,False,False):raise RuntimeError('String LOD generation failed')
        save(mesh.skeleton);save(mesh,source)
        r['materials']=[s.material_interface.get_path_name() for s in slots]
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))

texture=existing(ICON_NAME,ICON)
if not texture:
    png=P/(ICON_NAME+'.png');target=ROOT/'Content'/ICON.removeprefix('/Game/')/(ICON_NAME+'.png')
    if target.exists() and target.read_bytes()!=png.read_bytes():raise RuntimeError('Preserving different icon source '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(png,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=ICON;task.destination_name=ICON_NAME
    task.automated=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task])
    texture=u.load_asset(ICON+'/'+ICON_NAME)
    if not texture:raise RuntimeError('String icon import failed')
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;texture.srgb=True;texture.max_texture_size=1024
    texture.adjust_saturation=0.;texture.set_editor_property('never_stream',True);save(texture,png)
r['complete']=True;receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
print('MOUNTAIN_ECHO_IMPORT_COMPLETE',flush=True)
