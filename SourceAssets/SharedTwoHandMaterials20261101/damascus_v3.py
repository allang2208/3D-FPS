"""Apply the approved Zhanmadao V3 field to another steel carrier's existing finish branch."""
import json
import re
import runpy
from pathlib import Path

import unreal as u

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'ZhanmadaoDamascus20261111'
Z = runpy.run_path(str(SOURCE / 'materials.py'))
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
REV = 'SharedDamascusZhanmadaoV3_20261122'
REF = '/Game/Weapons/Zhanmadao20261018/BeiweiRuneV1/Materials/M_TangDaoBladeRuneSurface_Zhanmadao_factory_0_BeiweiV1'
LAYOUTS = json.loads((P.parent/'DaoLongitudinal20261110/layouts.json').read_text(encoding='utf-8'))
CHANNEL = {'BASE_COLOR': 3, 'METALLIC': 1, 'NORMAL': 3, 'ROUGHNESS': 1, 'ANISOTROPY': 1, 'TANGENT': 3}
PIN = dict(BASE_COLOR='BaseColor', NORMAL='Normal', METALLIC='Metallic', ROUGHNESS='Roughness', ANISOTROPY='Anisotropy', TANGENT='Tangent')


def make(m, cls, label, **props):
    n = L.create_material_expression(m, cls)
    n.set_editor_properties(dict(desc=REV+' '+label, **props))
    return n


def custom(m, label, source, channels, inputs):
    n = make(m, u.MaterialExpressionCustom, label, code=source,
             output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT'+str(channels)))
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for name, (value, channel) in inputs.items():
        Z['wire'](value, channel, n, name)
    return n


def add_input(n, name, value):
    pins = list(n.get_editor_property('inputs'))
    if not any(str(pin.get_editor_property('input_name')) == name for pin in pins):
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
        n.set_editor_property('inputs', pins)
    Z['wire'](value, '', n, name)


def ref_code(m, label):
    if m:
        n = next(v for v in L.get_material_expressions(m) if str(v.get_editor_property('desc')) == Z['REV']+' '+label)
        return str(n.get_editor_property('code'))
    # Selective import hosts can omit the reference sword; this is its saved V3 graph.
    snapshot = json.loads((P/'damascus-v3-reference.json').read_text(encoding='utf-8'))
    return snapshot['shaders'][label]


def field_nodes(m):
    result = {}
    for n in L.get_material_expressions(m):
        if not isinstance(n, u.MaterialExpressionCustom):
            continue
        desc = str(n.get_editor_property('desc'))
        pins = [str(k) for k in L.get_material_expression_input_names(n)]
        if 'Mode' not in pins or 'Base' not in pins:
            continue
        match = re.search(r'(?:MP_| )(BASE_COLOR|ROUGHNESS|METALLIC|NORMAL|ANISOTROPY|TANGENT)(?::|$)',desc)
        if match:
            result[match.group(1)] = n
    return result


def input_of(m, n, key):
    for name, parent in zip(L.get_material_expression_input_names(n), L.get_inputs_for_material_expression(m,n)):
        if str(name)==key and parent:
            return parent
    return None


def apply(m):
    if E.get_metadata_tag(m, 'SharedDamascusRevision') == REV:
        return False
    name = m.get_name()
    fields = field_nodes(m)
    if not {'BASE_COLOR','ROUGHNESS','NORMAL','METALLIC'} <= fields.keys():
        raise RuntimeError('Install the native common finish first: '+name)
    reference = u.load_asset(REF) if E.does_asset_exist(REF) else None
    mode = input_of(m, fields['BASE_COLOR'], 'Mode')
    mask = input_of(m, fields['BASE_COLOR'], 'Mask')
    if not mode or not mask:
        raise RuntimeError('Native finish mask or selection is missing: '+name)
    seed = Z['parameter'](m, 'DamascusSeed', 111120.)
    pos = make(m, u.MaterialExpressionPreSkinnedPosition, 'local position')
    nv = make(m, u.MaterialExpressionPreSkinnedNormal, 'local normal')
    n = make(m, u.MaterialExpressionVertexInterpolator, 'local normal interpolator')
    Z['wire'](nv, '', n, 'Input')
    zero = make(m,u.MaterialExpressionConstant,'zero',r=0.)
    bounds = make(m,u.MaterialExpressionPreSkinnedLocalBounds,'local bounds')
    is_hammer = 'Hammer' in name or 'hammer' in m.get_path_name().lower() or 'Runebound' in name
    profile = next((v for k,v in LAYOUTS.items() if k.startswith('tang_dao/') and ('Longitudinal_'+k.split('/')[1]+'_') in name),None)
    family = 'Twist' if is_hammer or 'heavy_spine' in name or 'tengyun' in name else 'Feather' if any(t in name for t in ('feather_edge','yanling_edge','Wedge','GaleFeather')) else 'Flow'
    if profile:
        code=Z['geometry_code'](dict(z=profile['z_cm'],center=profile['center_x_cm'],width=profile['width_cm'],arc=profile['arc_cm']))
        geometry=custom(m,'blade profile',code,4,{'P':(pos,'')})
    else:
        # Local centimetres keep the field stable as the weapon, socket or preview moves.
        # Project each hammer face onto its own plane; a side/end face must not collapse into a stripe.
        code = '''
float3 origin=(Lo+Hi)*.5;float3 local=P-origin;float3 span=max(Hi-Lo,.02);
float3 a=abs(N);
if (a.z>a.y && a.z>a.x) return float4(local.x,local.y,.5+local.x/span.x,2.);
if (a.x>a.y) return float4(local.y,local.z,.5+local.y/span.y,1.);
return float4(local.x,local.z,.5+local.x/span.x,0.);
''' if is_hammer else '''
float center=(Lo.x+Hi.x)*.5;float width=max(Hi.x-Lo.x,.02);
return float4(P.x-center,P.z-Lo.z,.5+(P.x-center)/width,0.);
'''
        geometry=custom(m,'solid profile',code,4,{'P':(pos,''),'N':(nv,''),'Lo':(bounds,'Min'),'Hi':(bounds,'Max')})
    g=make(m,u.MaterialExpressionVertexInterpolator,'surface coordinates')
    Z['wire'](geometry,'',g,'Input')
    uv_code=ref_code(reference,'field coordinates')
    if family=='Feather': uv_code=uv_code.replace('float offset=a;', 'float offset=(a-.5)*.075;')
    uv=custom(m,'field coordinates',uv_code,2,{'G':(g,''),'Seed':(seed,'')})
    tex=Z['load_field_texture'](family)
    field=make(m,u.MaterialExpressionTextureSample,'packed steel field',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    Z['wire'](uv,'',field,'UVs')
    rune=next((v for v in L.get_material_expressions(m) if isinstance(v,u.MaterialExpressionCustom)
               and 'RuneTexture' in str(v.get_editor_property('code')) and v.get_editor_property('output_type')==u.CustomMaterialOutputType.CMOT_FLOAT4),None)
    ink=rune or custom(m,'no ink','return float4(0,0,0,0);',4,{'Zero':(zero,'')})
    steel_code=ref_code(reference,'steel response')
    if is_hammer:
        steel_code=steel_code.replace('abs(normalize(N).y)','max(abs(normalize(N).x),max(abs(normalize(N).y),abs(normalize(N).z)))')
    steel=custom(m,'steel response',steel_code,4,{'Field':(field,'RGBA'),'N':(n,''),'G':(g,''),'Ink':(ink,''),'Mask':(mask,''),'Seed':(seed,'')})
    grad_code=ref_code(reference,'etch gradient')
    brush_code=ref_code(reference,'polish direction')
    if is_hammer:
        grad_code=grad_code.replace('float3 along=normalize(float3(G.w,0,1)), across=normalize(float3(1,0,-G.w));','float3 w=abs(normalize(N)); bool cap=w.z>=max(w.x,w.y); float3 along=cap?float3(0,1,0):float3(0,0,1), across=(cap||w.y>=w.x)?float3(1,0,0):float3(0,1,0);')
        grad_code=grad_code.replace('abs(normalize(N).y)','max(abs(normalize(N).x),max(abs(normalize(N).y),abs(normalize(N).z)))')
        brush_code=brush_code.replace('float3 v=float3(G.w,0,1);','float3 w=abs(normalize(N));float3 v=w.z>=max(w.x,w.y)?float3(0,1,0):float3(0,0,1);')
    delta=custom(m,'etch gradient',grad_code,3,{'Field':(field,'RGBA'),'N':(n,''),'G':(g,'')})
    brush=custom(m,'polish direction',brush_code,3,{'N':(n,''),'G':(g,'')})
    tangent=m.get_editor_property('tangent_space_normal')
    def transform(v,l):
        result=make(m,u.MaterialExpressionTransform,l,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT if tangent else u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        Z['wire'](v,'',result,'Input')
        return result
    delta=transform(delta,'etch gradient space')
    brush=transform(brush,'polish direction space')
    slab=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
    for key in ['BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','ANISOTROPY','TANGENT']:
        old=fields.get(key)
        if not old:
            prop=getattr(u.MaterialProperty,'MP_'+key)
            base=L.get_material_property_input_node(m,prop)
            channel=str(L.get_material_property_input_node_output_name(m,prop)) if base else ''
            if base is None:
                base=zero if key=='ANISOTROPY' else (make(m,u.MaterialExpressionConstant3Vector,'native tangent',constant=u.LinearColor(1,0,0,1)) if tangent else make(m,u.MaterialExpressionVertexTangentWS,'native tangent'))
            old=custom(m,key,'return Base;',CHANNEL[key],{'Mode':(mode,''),'Base':(base,channel)})
            if not L.connect_material_property(old,'',prop): raise RuntimeError('Material output '+key)
            if slab: Z['wire'](old,'',slab,PIN[key])
        add_input(old,'Steel',steel)
        if key=='NORMAL':add_input(old,'DamascusDetail',delta)
        if key=='TANGENT':add_input(old,'DamascusBrush',brush)
        shader=str(old.get_editor_property('code'))
        # Replace only the Damascus branch. All private, native rune, guard-root and inlay gates stay intact.
        marker='// Damascus20261031V1'
        if marker in shader:
            begin=shader.index(marker);opening=shader.index('{',begin);i=opening+1;depth=1
            while depth:
                depth+=(shader[i]=='{')-(shader[i]=='}');i+=1
            shader=shader[:begin]+shader[i:]
        response=ref_code(reference,key).split('return Base;',1)[1].strip().replace('Detail','DamascusDetail').replace('Brush','DamascusBrush')
        old.set_editor_property('code','// '+REV+'\nif(Mode>3.5 && Mode<4.5){'+response+'}\n'+shader)
    E.set_metadata_tag(m,'SharedDamascusRevision',REV)
    E.set_metadata_tag(m,'SharedDamascusField',family)
    return True


def apply_registered(material):
    """Used by native weapon producers after their own geometry, rune and decoration setup."""
    surfaces = json.loads((P/'damascus-v3-surfaces.json').read_text(encoding='utf-8'))['surfaces']
    package = material.get_path_name().split('.')[0]
    if package not in surfaces:
        return False
    refined = False
    if package in {
        '/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
        '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold',
        '/Game/Skills/Whirlwind20260920/ForegroundV3/M_AzureRunesword_c744c7ca_WhirlwindV3',
    }:
        refine = runpy.run_path(str(P/'azure_native_finishes.py'))['apply']
        refined = bool(refine(material, P.parent))
    return apply(material) or refined
