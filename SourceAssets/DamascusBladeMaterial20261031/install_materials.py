"""Add mode 4 in place, retaining the saved factory and three common finishes."""
from pathlib import Path
import json, shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
REVISION = 'Damascus20261031V1'
MASTERS = [
    '/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
    '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold',
]

# Local centimetres stay attached to the blade while it moves. Warped contours
# represent contrasting etched alloys, with derivative filtering at distance.
PATTERN = '''
float2 dq=float2(P.x*1.4, P.z*.48+P.y*.13);
float twist=dq.x*2.9+dq.y*.70+.6*sin(dq.y*.90);
float field=dq.x+.58*sin(dq.y*.55+dq.x*.60)
    +.24*sin(dq.y*1.90-dq.x*.91)
    +.11*sin(dq.y*4.60+dq.x*2.40)+.47*sin(twist);
float phase=field*9.0;
float width=fwidth(phase);
float visibility=exp2(-.35*width*width);
float layers=lerp(.5,smoothstep(.20,.80,.5+.5*sin(phase)),visibility);
float polishPhase=P.x*260.0+sin(P.z*1.7)*.35;
float polishWidth=fwidth(polishPhase);
float polish=sin(polishPhase)*exp2(-.35*polishWidth*polishWidth);
float protect=1-saturate(Mask*3.0);
'''
COLOR = PATTERN + '''
float shade=clamp(dot(Base,float3(.2126,.7152,.0722))/.32,.84,1.06);
float3 steel=lerp(float3(.070,.075,.081),float3(.46,.48,.50),layers);
return lerp(Base,steel*shade*(1+polish*.008),protect);
'''
ROUGH = PATTERN + '''
float etchedRoughness=lerp(.365,.235,layers)+polish*.004;
return lerp(Base,clamp(etchedRoughness+(Base-.35)*.08,.20,.42),protect);
'''
NORMAL = PATTERN + '''
float shallowRelief=cos(phase)*visibility*.035;
float2 slope=float2(shallowRelief,shallowRelief*.30*sin(twist)+polish*.003);
return normalize(lerp(Base,normalize(float3(Base.xy+slope,Base.z)),protect));
'''
PROGRAMS = {'MP_BASE_COLOR': COLOR, 'MP_ROUGHNESS': ROUGH, 'MP_NORMAL': NORMAL}

saved = []
for path in MASTERS:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing blade master: ' + path)
    if E.get_metadata_tag(material, 'DamascusFinishRevision') == REVISION:
        saved.append({'asset': material.get_path_name(), 'already_current': True})
        continue
    asset = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    backup = P / 'BeforeAssets' / asset.relative_to(ROOT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(asset, backup)
    nodes = [n for n in L.get_material_expressions(material)
             if isinstance(n, u.MaterialExpressionCustom)
             and str(n.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    # Replace only the authored mode nodes; retain wetness, native rune masks,
    # emission, Substrate wiring and all existing mode 0-3 code verbatim.
    for property_name, code in PROGRAMS.items():
        expression = next((n for n in nodes if property_name + ':' in str(n.get_editor_property('desc'))), None)
        if expression is None:
            raise RuntimeError('Base blade finish missing: ' + path + ' ' + property_name)
        original = expression.get_editor_property('code')
        expression.set_editor_property('code', '// ' + REVISION + '\nif(Mode>3.5 && Mode<4.5) {\n' + code + '\n}\n' + original)
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Damascus material compilation failed: ' + str(errors))
    E.set_metadata_tag(material, 'DamascusFinishRevision', REVISION)
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Material save failed: ' + path)
    saved.append({'asset': material.get_path_name(), 'saved': True, 'mode': 4,
                  'retained_modes': [0, 1, 2, 3]})

(P / 'material-receipt.json').write_text(json.dumps({
    'revision': REVISION, 'materials': saved, 'gameplay_tested': False
}, indent=2) + '\n', encoding='utf8')
print('DAMASCUS_MATERIALS_SAVED', json.dumps(saved))
