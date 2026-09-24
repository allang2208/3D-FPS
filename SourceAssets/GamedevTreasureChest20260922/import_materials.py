import json
from pathlib import Path
import unreal as u
HERE=Path(__file__).parent;ROOT='/Game/Props/GamedevTreasureChest20260922/Materials'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    raise RuntimeError('Requested end of play for the required asset import. Resume after the editor returns.')
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
recipes={'Treasure_BlackIron':((.055,.052,.048),.76,.43,.13),
         'Treasure_AntiqueGold':((.48,.30,.10),.88,.32,.10),
         'Treasure_Interior':((.009,.011,.013),.08,.86,.05)}
saved=[]
for name,(color,metal,rough,variation) in recipes.items():
    path=ROOT+'/M_'+name;m=u.load_asset(path)
    if m is None:
        m=AT.create_asset('M_'+name,ROOT,u.Material,u.MaterialFactoryNew())
    if E.get_metadata_tag(m,'TreasureMaterialVersion')!='1':
        L.delete_all_material_expressions(m)
        uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate,-650,0)
        grain=L.create_material_expression(m,u.MaterialExpressionCustom,-430,0)
        inp=u.CustomInput();inp.set_editor_property('input_name','UV')
        grain.set_editor_property('inputs',[inp]);grain.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
        grain.set_editor_property('code','float2 p=UV*280; float2 i=floor(p); float2 f=frac(p); f=f*f*(3-2*f); float a=frac(sin(dot(i,float2(127.1,311.7)))*43758.5453); float b=frac(sin(dot(i+float2(1,0),float2(127.1,311.7)))*43758.5453); float c=frac(sin(dot(i+float2(0,1),float2(127.1,311.7)))*43758.5453); float d=frac(sin(dot(i+1,float2(127.1,311.7)))*43758.5453); return lerp(lerp(a,b,f.x),lerp(c,d,f.x),f.y);')
        L.connect_material_expressions(uv,'',grain,'UV')
        base=L.create_material_expression(m,u.MaterialExpressionVectorParameter,-400,-240);base.set_editor_property('parameter_name','BaseColor');base.set_editor_property('default_value',u.LinearColor(*color,1))
        gain=L.create_material_expression(m,u.MaterialExpressionMultiply,-170,0);gain.set_editor_property('const_b',.22);L.connect_material_expressions(grain,'',gain,'A')
        bias=L.create_material_expression(m,u.MaterialExpressionAdd,0,0);bias.set_editor_property('const_b',.85);L.connect_material_expressions(gain,'',bias,'A')
        tint=L.create_material_expression(m,u.MaterialExpressionMultiply,180,-170);L.connect_material_expressions(base,'',tint,'A');L.connect_material_expressions(bias,'',tint,'B');L.connect_material_property(tint,'',u.MaterialProperty.MP_BASE_COLOR)
        metallic=L.create_material_expression(m,u.MaterialExpressionScalarParameter,160,80);metallic.set_editor_property('parameter_name','Metallic');metallic.set_editor_property('default_value',metal);L.connect_material_property(metallic,'',u.MaterialProperty.MP_METALLIC)
        rough_gain=L.create_material_expression(m,u.MaterialExpressionMultiply,-160,220);rough_gain.set_editor_property('const_b',variation);L.connect_material_expressions(grain,'',rough_gain,'A')
        rough_add=L.create_material_expression(m,u.MaterialExpressionAdd,160,220);rough_add.set_editor_property('const_b',rough);L.connect_material_expressions(rough_gain,'',rough_add,'A');L.connect_material_property(rough_add,'',u.MaterialProperty.MP_ROUGHNESS)
        L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.recompile_material(m)
        E.set_metadata_tag(m,'TreasureMaterialVersion','1')
    E.set_metadata_tag(m,'Source','Gamedev dungeon chest; independent of warehouse materials')
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(path)],False):raise RuntimeError('Material save failed '+path)
    saved.append(m.get_path_name())
(HERE/'materials_receipt.json').write_text(json.dumps({'saved':saved,'tested':False},indent=2),encoding='utf-8')
print('TREASURE_MATERIALS_SAVED '+json.dumps(saved))
