"""Shared authoring hook for the three existing wall-damp material identities."""
from pathlib import Path
import hashlib
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'SourceAssets/DungeonWallStains20260924'
BASE = '/Game/Dungeons/WallStains20260924'
PATHS = (
    '/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak',
    '/Game/Dungeons/AtmosphereV2/TilePolish/Materials/M_TileLeak',
    '/Game/Dungeons/AtmosphereV2/NaturalPass/Materials/M_NaturalLeakVertical',
)
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
TAG = 'WallStreakRevision'
REVISION = 'sparse-gravity-20260924-v1'

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Wall streak save failed: '+asset.get_path_name())

def install_material(path):
    if path not in PATHS:
        return False
    # Historical imports also use this hook. Never replace other decals or walls.
    source = ROOT/'Authored/WallStreakMasks.png'
    if not source.exists():
        raise RuntimeError('Author WallStreakMasks.png before importing wall stains')
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing existing wall stain material: '+path)
    texture_path=BASE+'/Textures/T_WallStreakMasks'
    texture=u.load_asset(texture_path)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if not texture or E.get_metadata_tag(texture,'WallStreakSourceSHA256')!=source_hash:
        task=u.AssetImportTask()
        task.filename=str(source);task.destination_path=BASE+'/Textures'
        task.destination_name='T_WallStreakMasks';task.automated=True;task.save=False;task.replace_existing=True
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture=u.load_asset(texture_path)
        if not texture:raise RuntimeError('Wall stain mask import failed')
        texture.set_editor_property('srgb',False)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property('compression_no_alpha',False)
        texture.set_editor_property('never_stream',False)
        texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
        texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
        E.set_metadata_tag(texture,'WallStreakSourceSHA256',source_hash)
        save(texture)
    if E.get_metadata_tag(material,TAG)==REVISION:
        return True
    backup=BASE+'/Baseline/'+material.get_name()+'_BeforeSparseStreaks'
    if not E.does_asset_exist(backup):
        copied=E.duplicate_asset(path,backup)
        if not copied:raise RuntimeError('Cannot preserve previous wall stain material')
        save(copied)
    material.modify();L.delete_all_material_expressions(material)
    material.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    def node(kind,**properties):
        n=L.create_material_expression(material,getattr(u,'MaterialExpression'+kind))
        for key,value in properties.items():n.set_editor_property(key,value)
        return n
    inputs={'UV':node('TextureCoordinate'),
            'MaskTex':node('TextureObjectParameter',parameter_name='StreakMasks',texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)}
    for key,value in [('StainOpacity',.28),('StainVariant',0.),('StainWidth',.8),('StainLength',.8),('StainOffset',0.),('StainMirror',0.)]:
        inputs[key]=node('ScalarParameter',parameter_name=key,default_value=value)
    custom=node('Custom',output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,desc='Sparse downward seepage; neutral colour and soft variable trail lengths',code='''
// Deferred decal UV is local Z/Y: convert to horizontal/top-to-bottom.
float2 p=float2(UV.y,1-UV.x);
p.x=lerp(p.x,1-p.x,step(.5,StainMirror));
p.x=(p.x-.5-StainOffset)/max(StainWidth,.35)+.5;
// Keep the upper leak source fixed while the lower trail varies.
p.y=(p.y-.06)/max(StainLength,.3)+.06;
float edge=smoothstep(0,.045,p.x)*(1-smoothstep(.955,1,p.x))
          *smoothstep(0,.035,p.y)*(1-smoothstep(.965,1,p.y));
float4 masks=Texture2DSample(MaskTex,MaskTexSampler,saturate(p));
float mask=StainVariant<.5?masks.r:StainVariant<1.5?masks.g:StainVariant<2.5?masks.b:masks.a;
return saturate(mask*edge*clamp(StainOpacity,0,.42));
''')
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for key,src in inputs.items():
        if not L.connect_material_expressions(src,'',custom,key):raise RuntimeError('Wall stain input '+key)
    outputs=[(custom,'OPACITY'),
        (node('VectorParameter',parameter_name='StainTint',default_value=u.LinearColor(.115,.108,.086,1)),'BASE_COLOR'),
        (node('ScalarParameter',parameter_name='StainRoughness',default_value=.72),'ROUGHNESS')]
    for src,prop in outputs:
        if not L.connect_material_property(src,'',getattr(u.MaterialProperty,'MP_'+prop)):
            raise RuntimeError('Wall stain output '+prop)
    # No normal output: the accepted wall relief is retained under the stain.
    errors=L.recompile_material(material)
    if errors:raise RuntimeError(str(errors))
    L.get_statistics(material)  # Complete necessary shader production before saving.
    L.layout_material_expressions(material)
    E.set_metadata_tag(material,TAG,REVISION);save(material)
    print('WALL_STREAK_MATERIAL_SAVED',path,flush=True)
    return True
