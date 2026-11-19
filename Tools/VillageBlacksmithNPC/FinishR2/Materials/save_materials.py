"""Import the R2 textures and update five owned character materials inside an isolated host."""
import json
from pathlib import Path
import unreal as u

PROJECT=Path(__file__).resolve().parents[4]
OUT=PROJECT/'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit'
FOLDER='/Game/Characters/VillageBlacksmithNPC20261118/BodyOutfit'
VERSION=FOLDER+'/SurfaceR2'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools()
SETTINGS=json.loads((OUT/'material_settings.json').read_text())
packages=[]
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    packages.append(obj.get_path_name().split('.')[0])
def texture(name,kind):
    path=OUT/'Textures'/(name+'.png')
    task=u.AssetImportTask()
    task.filename=str(path)
    task.destination_path=VERSION
    task.destination_name=name
    task.replace_existing=True
    task.replace_existing_settings=True
    task.automated=True
    task.save=False
    A.import_asset_tasks([task])
    obj=u.load_asset(VERSION+'/'+name)
    if not obj:raise RuntimeError('Import failed '+name)
    obj.set_editor_property('srgb',kind=='BC')
    compression,group={
        'BC':(u.TextureCompressionSettings.TC_DEFAULT,u.TextureGroup.TEXTUREGROUP_CHARACTER),
        'N':(u.TextureCompressionSettings.TC_NORMALMAP,u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP),
        'ORM':(u.TextureCompressionSettings.TC_MASKS,u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
    }[kind]
    obj.set_editor_property('compression_settings',compression)
    obj.set_editor_property('lod_group',group)
    if name.endswith('Contact'):
        obj.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
        obj.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    save(obj)
    return obj
samplers={'BC':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'N':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS}
prop=u.MaterialProperty
for slot in SETTINGS['upgraded']:
    m=u.load_asset(FOLDER+'/Materials/M_Smith_'+slot)
    if not m:raise RuntimeError('Original material unavailable: '+slot)
    L.delete_all_material_expressions(m)
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    def node(cls,**props):
        e=L.create_material_expression(m,cls)
        for k,v in props.items():e.set_editor_property(k,v)
        return e
    cloth=slot in ('Linen','Twill')
    m.set_editor_property('use_material_attributes',cloth)
    attributes=node(u.MaterialExpressionMakeMaterialAttributes) if cloth else None
    cloth_pins={prop.MP_BASE_COLOR:'BaseColor',prop.MP_AMBIENT_OCCLUSION:'AmbientOcclusion',prop.MP_ROUGHNESS:'Roughness',prop.MP_METALLIC:'Metallic',prop.MP_SPECULAR:'Specular',prop.MP_NORMAL:'Normal',prop.MP_SUBSURFACE_COLOR:'SubsurfaceColor'}
    def output(src,material_pin):
        if cloth:
            connect(src,attributes,cloth_pins[material_pin])
            return
        if not L.connect_material_property(src[0],src[1],material_pin):raise RuntimeError('Material output failed '+str(material_pin))
    def connect(src,e,pin):
        if not L.connect_material_expressions(src[0],src[1],e,pin):raise RuntimeError('Node input failed '+pin)
    def constant(x):return node(u.MaterialExpressionConstant,r=x),''
    def constant3(x):return node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*x,1.)),''
    def pair(cls,x,y):
        e=node(cls)
        connect(x,e,'A');connect(y,e,'B')
        return e,''
    def mul(x,y):return pair(u.MaterialExpressionMultiply,x,y)
    def add(x,y):return pair(u.MaterialExpressionAdd,x,y)
    def sub(x,y):return pair(u.MaterialExpressionSubtract,x,y)
    def sample(name,k):
        return node(u.MaterialExpressionTextureSample,texture=texture(name,k),sampler_type=samplers[k])
    basename='T_Smith_'+slot+'_'
    bc=(sample(basename+'BC','BC'),'RGB')
    normal=(sample(basename+'N','N'),'RGB')
    orm=sample(basename+'ORM','ORM')
    rough=(orm,'G')
    if slot=='Apron':
        pre=node(u.MaterialExpressionPreSkinnedPosition)
        rest=node(u.MaterialExpressionVertexInterpolator)
        connect((pre,''),rest,'')
        def axis(key):
            mask=node(u.MaterialExpressionComponentMask,**{axis:axis==key for axis in 'rgba'})
            connect((rest,''),mask,'')
            return mask,''
        uv=pair(u.MaterialExpressionAppendVector,add(mul(axis('r'),constant(1/37)),constant(.5)),mul(sub(constant(136.2),axis('b')),constant(1/81)))
        c=sample('T_Smith_Apron_Contact','ORM');connect(uv,c,'UVs')
        wear,oil,soot=(c,'R'),(c,'G'),(c,'B')
        bc=mul(add(bc,mul(constant3((.086,.045,.017)),wear)),sub(sub(constant(1.),mul(oil,constant(.39))),mul(soot,constant(.35))))
        rough=add(sub(add(rough,mul(wear,constant(.09))),mul(oil,constant(.24))),mul(soot,constant(.14)))
    if cloth:
        m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH)
        output(mul(bc,constant(.45)),prop.MP_SUBSURFACE_COLOR)
        connect(constant(.22),attributes,'ClearCoat')
        if not L.connect_material_property(attributes,'',prop.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Cannot bind cloth attributes')
    output(bc,prop.MP_BASE_COLOR)
    output(normal,prop.MP_NORMAL)
    output((orm,'R'),prop.MP_AMBIENT_OCCLUSION)
    output(rough,prop.MP_ROUGHNESS)
    output((orm,'B'),prop.MP_METALLIC)
    output(constant(SETTINGS['specular'][slot]),prop.MP_SPECULAR)
    L.layout_material_expressions(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Unable to compile '+slot+' '+str(errors))
    save(m)
    print('SAVED_SMITH_R2_SURFACE',slot,flush=True)
(OUT/'materials_saved.json').write_text(json.dumps({'packages':packages},indent=2))
