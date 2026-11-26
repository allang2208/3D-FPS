"""Save the procedural soft black visor as a new UI material."""
import hashlib, json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/SteelArmet20261019/BlackFrame20261020'
R.mkdir(parents=True,exist_ok=True)
DEST='/Game/Characters/ModularOutfit20260924/SteelArmet20261019/BlackFrame20261020'
NAME='M_SteelArmet_SoftBlackFrame'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
shader=(P/'Tools/SteelArmet/black_frame.hlsl').read_text()
revision=hashlib.sha256(shader.encode()+Path(__file__).read_bytes()).hexdigest()
mat=u.load_asset(DEST+'/'+NAME)
if not mat or E.get_metadata_tag(mat,'HelmetBlackFrameSHA')!=revision:
    if mat and '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():
            raise RuntimeError('End play before replacing the saved black-frame material')
    mat=mat or A.create_asset(NAME,DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_UI)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    def node(cls,**props):
        value=L.create_material_expression(mat,cls)
        for key,data in props.items():value.set_editor_property(key,data)
        return value
    values={'UV':node(u.MaterialExpressionTextureCoordinate),
        'Motion':node(u.MaterialExpressionVectorParameter,parameter_name='HelmetMotion',default_value=u.LinearColor(0,0,0,0))}
    for key,name,value in [('Aspect','HelmetAspect',16/9),('HalfWidth','OpeningHalfWidth',.45),
        ('HalfHeight','OpeningHalfHeight',.2385),('CenterY','OpeningCenterY',.50675),
        ('CornerRadius','OpeningCornerRadius',.05),('Feather','EdgeFeather',.025)]:
        values[key]=node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    mask=node(u.MaterialExpressionCustom,code=shader,
        description='Soft black helmet frame; clear centre and screen-space feather',
        output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
    pins=[]
    for key in values:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    mask.set_editor_property('inputs',pins)
    for key,value in values.items():
        if not L.connect_material_expressions(value,'RGB' if key=='Motion' else '',mask,key):
            raise RuntimeError('Black frame input '+key)
    black=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,1))
    if not L.connect_material_property(black,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Black frame colour connection')
    if not L.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY):
        raise RuntimeError('Black frame opacity connection')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Black frame material compile '+str(errors))
    E.set_metadata_tag(mat,'HelmetBlackFrameSHA',revision)
    mat.modify()
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Black frame material save failed')
(R/'saved_assets.json').write_text(json.dumps(dict(completed=True,material=mat.get_path_name(),
    revision=revision,clear_height_fraction=.477,clear_width_fraction=.9,
    feather_height_fraction=.025,texture_samples=0,runtime_tested=False),indent=2),encoding='utf-8')
print('HELMET_BLACK_FRAME_SAVED',mat.get_path_name(),flush=True)
