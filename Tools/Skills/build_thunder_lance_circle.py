"""Author/save only the lance's procedural circle. No play, render or tests."""
import json
from pathlib import Path
import unreal as u

DEST = '/Game/Skills/ElectricMagic/ThunderLanceV2'
PATH = DEST + '/M_ThunderLanceCircle'
ROOT = Path(u.Paths.project_dir())
LIB = u.MaterialEditingLibrary


def build_circle():
    if any(str(p.get_path_name()) == PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved ThunderLanceV2 packages')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('End PIE before saving lance circle material')
    u.EditorAssetLibrary.make_directory(DEST)
    material = u.load_asset(PATH) if u.EditorAssetLibrary.does_asset_exist(PATH) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_ThunderLanceCircle', DEST, u.Material, u.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Cannot author ' + PATH)
    LIB.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('disable_depth_test', False)
    material.set_editor_property('enable_responsive_aa', True)
    material.set_editor_property('output_translucent_velocity', True)
    def node(kind):
        return LIB.create_material_expression(material, kind)
    uv = node(u.MaterialExpressionTextureCoordinate)
    time = node(u.MaterialExpressionTime)
    charge = node(u.MaterialExpressionScalarParameter)
    charge.set_editor_property('parameter_name', 'Charge')
    charge.set_editor_property('default_value', 0.)
    shape = node(u.MaterialExpressionCustom)
    shape.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    shape.set_editor_property('code', '''
float2 p=(UV-.5)*2;
float r=length(p),a=atan2(p.y,p.x),c=saturate(Charge);
float aa=max(fwidth(r)*1.2,.002);
float outer=1-smoothstep(.015,.015+aa,abs(r-.91));
float inner=1-smoothstep(.012,.012+aa,abs(r-.69));
float turn=a-Time*.28,back=a+Time*.19;
float notches=pow(saturate(.5+.5*cos(turn*24)),18);
float ticks=notches*(1-smoothstep(.024,.024+aa,abs(r-.855)));
// Twelve repeated diamond/stave glyphs, with open space at the aim centre.
float q=abs(frac((back+3.14159265)*12/6.2831853)-.5);
float stave=(1-smoothstep(.022,.037,q))*(1-smoothstep(.048,.048+aa,abs(r-.775)));
float diamond=1-smoothstep(.014,.014+aa,abs(abs(r-.775)+q*.30-.047));
diamond*=1-smoothstep(.14,.17,q);
float core=1-smoothstep(.008,.008+aa,abs(r-(.43-.07*c)));
core*=.30+.40*pow(saturate(.5+.5*cos(turn*6)),10);
float pulse=.92+.08*sin(Time*3.0);
float pattern=saturate(outer*.65+inner*.75+ticks*.65+stave*.75+diamond*.8+core);
return pattern*lerp(.80,1.,c)*pulse*saturate((1-r)*18);
''')
    pins = []
    for name, expr in [('UV', uv), ('Time', time), ('Charge', charge)]:
        pin = u.CustomInput();pin.set_editor_property('input_name', name);pins.append(pin)
    shape.set_editor_property('inputs', pins)
    for name, expr in [('UV', uv), ('Time', time), ('Charge', charge)]:
        if not LIB.connect_material_expressions(expr, '', shape, name):
            raise RuntimeError('Circle input ' + name)
    tint = node(u.MaterialExpressionConstant3Vector)
    tint.set_editor_property('constant', u.LinearColor(.60, .80, 1., 1.))
    glow = node(u.MaterialExpressionMultiply)
    glow.set_editor_property('const_b', 14.)
    LIB.connect_material_expressions(tint, '', glow, 'A')
    # Additive blend multiplies emissive by opacity; apply the pattern once.
    LIB.connect_material_property(glow, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(shape, '', u.MaterialProperty.MP_OPACITY)
    LIB.recompile_material(material)
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Circle save failed')
    receipt = {'saved_asset': material.get_path_name(), 'mesh': '/Engine/BasicShapes/Plane',
               'size_cm': 64, 'staff_front_cm': 24, 'emissive_gain': 14, 'texture_dependencies': [],
               'design': 'counterrotating double ring, twelve stave/diamond glyphs, white-blue charge response',
               'gameplay_tested': False, 'rendered': False}
    folder = ROOT / 'Saved/ThunderLanceCharge20261001';folder.mkdir(parents=True, exist_ok=True)
    (folder / 'circle-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('THUNDER_LANCE_CIRCLE_SAVED ' + json.dumps(receipt))
    return material


if __name__ == '__main__':
    build_circle()
