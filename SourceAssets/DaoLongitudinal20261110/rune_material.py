"""Blade-local arc coordinates and aspect-preserving rune panels."""
import json
import runpy
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
L = u.MaterialEditingLibrary
REV = 'DaoLongitudinal20261110V2'
START = '// DAO_LONGITUDINAL_V2'
END = '// END_DAO_LONGITUDINAL_V2'


def curve(name, x, y):
    # Continuous piecewise Hermite fit, with monotone slopes at bend stations.
    h = [b - a for a, b in zip(x, x[1:])]
    d = [(b - a) / step for a, b, step in zip(y, y[1:], h)]
    m = [d[0]] + [0.] * (len(x) - 2) + [d[-1]]
    for i in range(1, len(x) - 1):
        if d[i - 1] * d[i] > 0:
            a, b = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (a + b) / (a / d[i - 1] + b / d[i])
    lines = ['float ' + name + '=0;']
    for i, step in enumerate(h):
        a = 2 * y[i] - 2 * y[i + 1] + step * (m[i] + m[i + 1])
        b = -3 * y[i] + 3 * y[i + 1] - step * (2 * m[i] + m[i + 1])
        gate = ('if' if i == 0 else 'else if') + ('(true)' if i == len(h) - 1 else '(DaoZ<=%.9f)' % x[i + 1])
        lines.append(gate + '{float s=saturate((DaoZ-%.9f)/%.9f);%s=((%.9f*s+%.9f)*s+%.9f)*s+%.9f;}' % (x[i], step, name, a, b, step * m[i], y[i]))
    return '\n'.join(lines)


def remove_beiwei(code):
    marker = '// BEIWEI_RUNE_V1'
    if marker not in code:
        return code
    start = code.index(marker)
    opening = code.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (code[end] == '{') - (code[end] == '}')
        end += 1
    return code[:start] + code[end:]


def prefix(profile, zhan):
    code = START + '\nif(RuneMode<-.5)return float4(0,0,0,0);\nfloat DaoZ=P.z;\n'
    for name, field in [('DaoCenter', 'center_x_cm'), ('DaoWidth', 'width_cm'), ('DaoArc', 'arc_cm')]:
        code += curve(name, profile['z_cm'], profile[field]) + '\n'
    low, high, center = profile['display_arc_cm']
    height = 2 * min(center - low, high - center)
    code += '''float DaoSide=N.y>=0?1:-1;
float DaoAcross=P.x-DaoCenter;
float DaoFace=smoothstep(.35,.78,abs(normalize(N.xyz).y));
float DaoLane=1-smoothstep(DaoWidth*.48,DaoWidth*.54,abs(DaoAcross));
float DaoKeepout=1-saturate(DaoDecoration*3.);
RuneOpacity*=DaoFace*DaoLane*DaoKeepout;
HaloOpacity*=DaoFace*DaoLane*DaoKeepout;
uint DaoTexW,DaoTexH;
RuneTexture.GetDimensions(DaoTexW,DaoTexH);
float DaoCrop=(RuneMode>6.5&&RuneMode<7.5)?.56:.40;
float DaoAspect=float(DaoTexH)/max(float(DaoTexW)*DaoCrop,1.);
float DaoReferenceWidth=%.9f;
float DaoMaxHeight=%.9f;
float DaoPanelCenter=%.9f;
float DaoPanelHeight=min(DaoMaxHeight,DaoReferenceWidth*DaoAspect);
float DaoPanelWidth=DaoPanelHeight/max(DaoAspect,.001);
Dimensions=float3(DaoPanelWidth,DaoPanelCenter-DaoPanelHeight*.5,DaoPanelHeight);
P=float3(DaoAcross,0,DaoArc);
N=float3(0,DaoSide,0);BladeOrigin=float3(0,0,0);BladeAxis=float3(0,0,1);
''' % (profile['reference_width_cm'], height, center)
    code += END + '\n'
    if zhan:
        code += '''// END_ZHANMADAO_BLADE_CONTOUR_V1
// BEIWEI_RUNE_V1: the original horizontal calligraphy follows the blade arc.
if(RuneMode>9.5&&RuneMode<10.5)
{
    // The accepted 2172x724 calligraphy is 3:1. Its UE texture is stretched
    // to power-of-two dimensions, which must not change the physical aspect.
    float aspect=3.;
    float span=min(DaoReferenceWidth/.58,DaoMaxHeight/max(aspect,.001));
    float2 artUV=float2(.5+(DaoPanelCenter-DaoArc)/(span*aspect),.5-DaoSide*DaoAcross/span);
    float inside=smoothstep(0,.035,artUV.x)*(1-smoothstep(.965,1,artUV.x));
    inside*=smoothstep(0,.035,artUV.y)*(1-smoothstep(.965,1,artUV.y));
    float ink=Texture2DSample(RuneTexture,RuneTextureSampler,saturate(artUV)).r;
    float edge=Texture2DSample(RuneTexture,RuneTextureSampler,saturate(artUV+float2(.0008,-.0024))).r;
    float time=PreviewTime>=0?PreviewTime:T;
    float wave=.5+.5*sin(time*.85-artUV.x*7.0);
    float highlight=pow(wave,5.);
    float3 gold=lerp(float3(.40,.18,.035),float3(.96,.57,.12),.35+.65*wave);
    gold=lerp(gold,float3(1.,.87,.47),highlight*.55);
    gold+=saturate(ink-edge)*float3(.16,.10,.025);
    return float4(gold*(.72+.08*sin(time*.7)),ink*inside*RuneOpacity);
}
'''
    return code


def decoration_mask(material, profile_key):
    nodes = list(L.get_material_expressions(material))
    choice = profile_key.split('/')[1]
    samples = [n for n in nodes if isinstance(n, u.MaterialExpressionTextureSample) and n.get_editor_property('texture')]
    is_cyan = choice == 'zhufeng'
    token = 'T_Zhufeng_ORM_V1' if is_cyan else 'BaseColor'
    sample = next(n for n in samples if token in n.get_editor_property('texture').get_name())
    code = 'return smoothstep(.01,.05,.98-Native.b)/3.;' if is_cyan else 'return smoothstep(.002,.020,Native.r-max(Native.g,Native.b))/3.;'
    mask = next((n for n in nodes if str(n.get_editor_property('desc')) == REV + ' decoration keepout'), None)
    if mask is None:
        mask = L.create_material_expression(material, u.MaterialExpressionCustom)
        pin = u.CustomInput(); pin.set_editor_property('input_name', 'Native')
        mask.set_editor_property('inputs', [pin])
    mask.set_editor_properties(dict(desc=REV + ' decoration keepout', code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT1))
    if not L.connect_material_expressions(sample, 'RGB', mask, 'Native'):
        raise RuntimeError('Cannot connect decoration keepout')
    return mask


def apply_layout(material, profile_key):
    profiles = json.loads((P / 'layouts.json').read_text(encoding='utf-8'))
    profile = profiles[profile_key]
    zhan = profile_key.startswith('zhanmadao/')
    rune = next((n for n in L.get_material_expressions(material)
                 if isinstance(n, u.MaterialExpressionCustom) and 'RuneTexture' in str(n.get_editor_property('code'))), None)
    if rune is None:
        return False
    code = str(rune.get_editor_property('code'))
    old_end = '// END_ZHANMADAO_BLADE_CONTOUR_V1'
    if zhan and old_end in code:
        code = code.split(old_end, 1)[1]
    elif START in code:
        code = code.split(END, 1)[1]
    code = remove_beiwei(code)
    mask = decoration_mask(material, profile_key)
    pins = list(rune.get_editor_property('inputs'))
    if not any(str(p.get_editor_property('input_name')) == 'DaoDecoration' for p in pins):
        pin = u.CustomInput(); pin.set_editor_property('input_name', 'DaoDecoration'); pins.append(pin)
        rune.set_editor_property('inputs', pins)
    if not L.connect_material_expressions(mask, '', rune, 'DaoDecoration'):
        raise RuntimeError('Cannot connect rune keepout')
    rune.set_editor_property('code', prefix(profile, zhan) + code)
    u.EditorAssetLibrary.set_metadata_tag(material, 'DaoLongitudinalProfile', profile_key)
    u.EditorAssetLibrary.set_metadata_tag(material, 'DaoLongitudinalRevision', REV)
    return True


def apply_known_layout(material):
    name = material.get_name().removesuffix('_Whirlwind')
    prefix_name = 'M_TangDaoBladeRuneSurface_Zhanmadao_'
    if name.startswith(prefix_name):
        suffix = name.removeprefix(prefix_name)
        choices = json.loads((P / 'layouts.json').read_text())
        for key in choices:
            if key.startswith('zhanmadao/') and suffix.startswith(key.split('/')[1] + '_'):
                result = apply_layout(material, key)
                # Rebuilding a blade retains the later steel finish as well as its runes.
                recipe = P.parent / 'ZhanmadaoDamascus20261111/materials.py'
                if recipe.exists():
                    runpy.run_path(str(recipe))['apply_if_installed'](material)
                return result
    return False
