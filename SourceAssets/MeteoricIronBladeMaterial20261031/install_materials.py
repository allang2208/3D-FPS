"""Add the etched meteorite finish as mode 5 to the current blade materials."""
from pathlib import Path
import json, shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
REVISION = 'MeteoricIron20261031V1'
MASTERS = [
    '/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
    '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold',
]

# An artistic Widmanstatten finish in local centimetres. Three straight plate
# families intersect at 60 degrees with varying widths and triangular regions.
# Filter both band coverage and microscopic polish for minified pixels.
PATTERN = '''
float2 q=float2(P.x*.72,P.z*.72+P.y*.11);
float3 axes=float3(q.x,dot(q,float2(.5,.8660254))+.37,
    dot(q,float2(-.5,.8660254))+.71);
float3 pixelWidth=max(fwidth(axes),.001);
float3 cells=floor(axes);
float3 seed=frac(sin(cells*float3(127.1,311.7,74.7)+float3(17.2,38.1,61.7))*43758.5453);
seed=lerp(.5,seed,exp2(-3*pixelWidth*pixelWidth));
float3 halfWidth=.06+.14*seed;
float3 center=.29+.42*frac(seed*7.13);
float3 distance=abs(frac(axes)-center);
float3 coverage=1-smoothstep(halfWidth-pixelWidth,halfWidth+pixelWidth,distance);
float3 plates=lerp(halfWidth*2,coverage,exp2(-3*pixelWidth*pixelWidth));
float grain=frac(sin(dot(cells,float3(17.17,59.31,113.73)))*15731.743);
grain=lerp(.5,grain,exp2(-3*dot(pixelWidth,pixelWidth)));
float polishAxis=lerp(axes.x,axes.y,plates.y);
polishAxis=lerp(polishAxis,axes.z,plates.z);
float polishPhase=polishAxis*210.0;
float polishWidth=fwidth(polishPhase);
float polish=sin(polishPhase)*exp2(-.35*polishWidth*polishWidth);
float protect=1-saturate(Mask*3.0);
'''
COLOR = PATTERN + '''
float tone=.13+.075*grain;
tone=lerp(tone,.34+.06*seed.x,plates.x);
tone=lerp(tone,.46+.10*seed.y,plates.y);
tone=lerp(tone,.28+.08*seed.z,plates.z);
float shade=clamp(dot(Base,float3(.2126,.7152,.0722))/.32,.86,1.06);
return lerp(Base,float3(.98,1.0,1.025)*tone*shade*(1+polish*.006),protect);
'''
ROUGH = PATTERN + '''
float roughness=.30+.035*grain;
roughness=lerp(roughness,.255,plates.x);
roughness=lerp(roughness,.210,plates.y);
roughness=lerp(roughness,.275,plates.z);
return lerp(Base,clamp(roughness+(Base-.35)*.06+polish*.003,.19,.38),protect);
'''
NORMAL = PATTERN + '''
float2 plateSlope=float2(plates.x-.5*plates.y-.5*plates.z,
    .8660254*(plates.y-plates.z))*.012;
float2 polishSlope=float2(polish*.002,polish*.001);
return normalize(lerp(Base,normalize(float3(Base.xy+plateSlope+polishSlope,Base.z)),protect));
'''
PROGRAMS = {'MP_BASE_COLOR': COLOR, 'MP_ROUGHNESS': ROUGH, 'MP_NORMAL': NORMAL}

saved = []
for path in MASTERS:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing blade master: ' + path)
    if E.get_metadata_tag(material, 'MeteoricIronFinishRevision') == REVISION:
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
    # Retain all earlier modes verbatim, as well as the shared Substrate,
    # wetness, native rune mask and emission connections.
    for property_name, code in PROGRAMS.items():
        expression = next((n for n in nodes if property_name + ':' in str(n.get_editor_property('desc'))), None)
        if expression is None:
            raise RuntimeError('Base blade finish missing: ' + path + ' ' + property_name)
        original = expression.get_editor_property('code')
        expression.set_editor_property('code', '// ' + REVISION + '\nif(Mode>4.5 && Mode<5.5) {\n' + code + '\n}\n' + original)
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Meteoric iron shader compilation failed: ' + str(errors))
    E.set_metadata_tag(material, 'MeteoricIronFinishRevision', REVISION)
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Material save failed: ' + path)
    saved.append({'asset': material.get_path_name(), 'saved': True, 'mode': 5,
                  'retained_modes': [0, 1, 2, 3, 4]})

(P / 'material-receipt.json').write_text(json.dumps({
    'revision': REVISION, 'materials': saved, 'gameplay_tested': False
}, indent=2) + '\n', encoding='utf8')
print('METEORIC_IRON_MATERIALS_SAVED', json.dumps(saved))
