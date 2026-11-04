"""Add Highland-only opaque metal finishes to the existing surface graphs."""
from pathlib import Path
import json
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
REV = 'HighlandExclusive20261103V1'
SURFACES = [
    '/Game/Weapons/HighlandClaymore20260922/Materials/M_HighlandClaymoreSurface',
]
WHIRLWIND = SURFACES[0] + '_Whirlwind_HighlandExclusive20261103'
ICONS = {
    'ue_highland_claymore_blade_material_blackthorn_steel': 'blade_material_dark_iron',
    'ue_highland_claymore_blade_material_whitehart_mithril': 'blade_material_mithril',
}
ICON_ROOT = '/Game/ColdSteelData/AttachmentIcons20260913/'

# Two scales of smooth, non-directional hammer texture. Position is the shared
# face-planar local coordinate in centimetres, so blade modules keep one scale.
NOISE = '''
float2 hq=P.xz*.85;
float2 hi=floor(hq),hf=frac(hq);hf=hf*hf*(3-2*hf);
float4 hk=float4(dot(hi,float2(127.1,311.7)),dot(hi+float2(1,0),float2(127.1,311.7)),dot(hi+float2(0,1),float2(127.1,311.7)),dot(hi+float2(1,1),float2(127.1,311.7)));
float4 hv=frac(sin(hk)*43758.5453);
float hammer=lerp(lerp(hv.x,hv.y,hf.x),lerp(hv.z,hv.w,hf.x),hf.y);
float2 mq=P.xz*7.3;
float2 mi=floor(mq),mf=frac(mq);mf=mf*mf*(3-2*mf);
float4 mk=float4(dot(mi,float2(269.5,183.3)),dot(mi+float2(1,0),float2(269.5,183.3)),dot(mi+float2(0,1),float2(269.5,183.3)),dot(mi+float2(1,1),float2(269.5,183.3)));
float4 mv=frac(sin(mk)*43758.5453);
float micro=lerp(lerp(mv.x,mv.y,mf.x),lerp(mv.z,mv.w,mf.x),mf.y);
'''
BRANCHES = {
    'BASE_COLOR': NOISE + '''
float edge=saturate(Edge*.9);
if(Mode<10.5){
 float3 steel=float3(.055,.069,.086)*(.91+.18*hammer);
 return lerp(steel,float3(.36,.40,.45),edge*.82);
}
float3 silver=float3(.72,.79,.85)*(.985+.03*micro);
return lerp(silver,float3(.88,.91,.95),edge*.76);
''',
    'ROUGHNESS': NOISE + '''
if(Mode<10.5)return lerp(.30+.07*hammer+.014*(micro-.5),.17,saturate(Edge*.9));
return lerp(.185+.015*(micro-.5),.105,saturate(Edge*.9));
''',
    'NORMAL': NOISE + '''
float amplitude=Mode<10.5?.013:.002;
float2 polish=float2(hammer-.5,micro-.5)*amplitude;
return normalize(float3(Base.xy*(Mode<10.5?.48:.24)+polish,max(Base.z,.55)));
''',
    'METALLIC': 'return .98;\n',
    'ANISOTROPY': 'return Mode<10.5?.08:.30;\n',
}

def backup(package):
    disk = ROOT / 'Content' / (package.removeprefix('/Game/') + '.uasset')
    if disk.exists():
        dest = P / 'BeforeAssets' / disk.relative_to(ROOT / 'Content')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(disk, dest)

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.EditorLevelLibrary.get_pie_worlds(False):
        raise RuntimeError('PIE running; preserve the current session')
owned = set(SURFACES) | {WHIRLWIND} | {ICON_ROOT + name for name in ICONS}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in owned:
        raise RuntimeError('Unsaved target: ' + package.get_path_name())

receipt = {'revision': REV, 'materials': [], 'icons': [], 'gameplay_tested': False}
for path in SURFACES:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Required existing material missing: ' + path)
    backup(path)
    fields = {}
    for expression in L.get_material_expressions(material):
        if not isinstance(expression, u.MaterialExpressionCustom):
            continue
        desc = str(expression.get_editor_property('desc'))
        for field in BRANCHES:
            if desc == 'SharedTwoHandFinish20261101V1 ' + field:
                fields[field] = expression
    if set(fields) != set(BRANCHES):
        raise RuntimeError('Required finish inputs missing: ' + path)
    previous = {}
    for field, expression in fields.items():
        code = str(expression.get_editor_property('code'))
        previous[field] = code
        begin, end = '// ' + REV + ' BEGIN', '// ' + REV + ' END'
        if begin in code:
            start = code.index(begin)
            stop = code.index(end, start) + len(end)
            code = code[:start] + code[stop:].lstrip('\n')
        branch = begin + '\nif(Mode>9.5&&Mode<11.5){\n' + BRANCHES[field] + '}\n' + end + '\n'
        expression.set_editor_property('code', branch + code)
    before_path = P / ('before-' + path.rsplit('/', 1)[-1] + '.json')
    if not before_path.exists():
        before_path.write_text(json.dumps(previous, indent=2) + '\n', encoding='utf8')
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Material compilation: ' + path + ' ' + str(errors))
    L.get_statistics(material)
    E.set_metadata_tag(material, 'HighlandExclusiveFinishRevision', REV)
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Save failed: ' + path)
    receipt['materials'].append({'asset': path, 'saved': True, 'compile_errors': list(errors)})
    print('HIGHLAND_FINISH_SAVED', path)

# The legacy Whirlwind copy predates the shared finish system. Derive a new
# skill-only copy from the current graph; retain the old package untouched.
if E.does_asset_exist(WHIRLWIND):
    whirlwind = u.load_asset(WHIRLWIND)
    if E.get_metadata_tag(whirlwind, 'HighlandExclusiveWhirlwindRevision') != REV:
        raise RuntimeError('Preserve existing unowned material: ' + WHIRLWIND)
else:
    whirlwind = E.duplicate_asset(SURFACES[0], WHIRLWIND)
    if not whirlwind:
        raise RuntimeError('Whirlwind material duplication failed')
    temporal = L.create_material_expression(whirlwind, u.MaterialExpressionTemporalResponsivenessOutput, -700, -700)
    value = L.create_material_expression(whirlwind, u.MaterialExpressionConstant, -950, -700)
    value.set_editor_property('r', 1.0)
    if not L.connect_material_expressions(value, '', temporal, ''):
        raise RuntimeError('Whirlwind temporal output connection failed')
    E.set_metadata_tag(whirlwind, 'HighlandExclusiveWhirlwindRevision', REV)
    E.set_metadata_tag(whirlwind, 'Whirlwind.TemporalSource', u.load_asset(SURFACES[0]).get_path_name())
errors = L.recompile_material(whirlwind)
if errors:
    raise RuntimeError('Whirlwind material compilation: ' + str(errors))
L.get_statistics(whirlwind)
if not E.save_loaded_asset(whirlwind, False):
    raise RuntimeError('Whirlwind material save failed')
receipt['materials'].append({'asset': WHIRLWIND, 'saved': True, 'compile_errors': list(errors)})
mapping_path = ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping_backup = P / 'BeforeData/Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping_backup.parent.mkdir(parents=True, exist_ok=True)
if not mapping_backup.exists():
    shutil.copy2(mapping_path, mapping_backup)
mapping = json.loads(mapping_path.read_text(encoding='utf-8-sig'))
mapping[u.load_asset(SURFACES[0]).get_path_name()] = whirlwind.get_path_name()
mapping_path.write_text(json.dumps(mapping, indent=2) + '\n', encoding='utf8')
print('HIGHLAND_WHIRLWIND_SAVED', WHIRLWIND)

for name, source in ICONS.items():
    path = ICON_ROOT + name
    backup(path)
    texture = u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(ICON_ROOT + source, path)
    if not texture:
        raise RuntimeError('Icon duplication failed: ' + path)
    if not E.save_loaded_asset(texture, False):
        raise RuntimeError('Icon save failed: ' + path)
    receipt['icons'].append({'asset': path, 'source': ICON_ROOT + source, 'saved': True})

(P / 'material-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
print('HIGHLAND_EXCLUSIVE_MATERIALS_COMPLETE')
