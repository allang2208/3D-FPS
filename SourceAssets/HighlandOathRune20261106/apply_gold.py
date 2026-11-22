"""Author the gold blade surface and two presentation-only judgment trail materials."""
from pathlib import Path
import json
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/HighlandClaymore20260922/OathRune20261106'
EDIT = u.MaterialEditingLibrary
LIB = u.EditorAssetLibrary
DESCRIPTION = 'Highland oath: gold engraving, true-aspect crest and three sequential seals'


def compile_and_save(material):
    errors = EDIT.recompile_material(material)
    if errors or not LIB.save_loaded_asset(material, False):
        raise RuntimeError(f'Could not compile/save {material.get_path_name()}: {errors}')
    u.log('OATH_GOLD_SAVED ' + material.get_path_name())


def custom_with(material, marker):
    return next(n for n in EDIT.get_material_expressions(material)
                if isinstance(n, u.MaterialExpressionCustom) and marker in n.get_editor_property('code'))


def trail_asset(name, parent):
    path = DEST + '/' + name
    return u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(parent, path)


def sync_native_variants():
    root = '/Game/Weapons/HighlandClaymore20260922/'
    base = root + 'Materials/M_HighlandClaymoreSurface'
    ridge = root + 'RidgePiercer20260927/WedgeSpine/M_RidgeWedgeSteel'
    mapping = json.loads((ROOT.parents[1]/'Content/ColdSteelData/whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
    def temporal(path):
        return mapping[path+'.'+path.rsplit('/',1)[1]].split('.')[0]
    def ink_nodes(mat):
        return {str(n.get_editor_property('description')):n for n in EDIT.get_material_expressions(mat)
                if isinstance(n,u.MaterialExpressionCustom)
                and n.get_editor_property('description') in ('Native UV ink tint','Native blue ink or golden breathing')}
    accepted = ink_nodes(u.load_asset(base))
    if len(accepted)!=2:raise RuntimeError('Missing authored Highland ink graph')
    updated = []
    for path in dict.fromkeys((temporal(base), ridge, temporal(ridge))):
        if path==base:continue
        mat=u.load_asset(path)
        targets=ink_nodes(mat)
        if targets.keys()!=accepted.keys():raise RuntimeError('Missing native glyph inputs: '+path)
        if all('HIGHLAND_OATH_NATIVE' in n.get_editor_property('code') for n in targets.values()):continue
        param=next((n for n in EDIT.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionScalarParameter)
                    and str(n.get_editor_property('parameter_name'))=='NativeOath'),None)
        if not param:
            param=EDIT.create_material_expression(mat,u.MaterialExpressionScalarParameter)
            param.set_editor_properties(dict(parameter_name='NativeOath',default_value=0.))
        for desc, dest in targets.items():
            code=dest.get_editor_property('code')
            if 'HIGHLAND_OATH_NATIVE' in code:continue
            prefix=accepted[desc].get_editor_property('code').splitlines()[:2]
            if 'HIGHLAND_OATH_NATIVE' not in prefix[0] or not prefix[1].endswith('}'):
                raise RuntimeError('Unrecognized native oath branch')
            pins=list(dest.get_editor_property('inputs'))
            if not any(str(p.get_editor_property('input_name'))=='Oath' for p in pins):
                pin=u.CustomInput();pin.set_editor_property('input_name','Oath');pins.append(pin)
                dest.set_editor_property('inputs',pins)
            dest.set_editor_property('code','\n'.join(prefix)+'\n'+code)
            if not EDIT.connect_material_expressions(param,'',dest,'Oath'):raise RuntimeError('Oath input '+path)
        compile_and_save(mat)
        updated.append(path)
    return updated


def apply_gold():
    surface = u.load_asset(DEST + '/M_SilverRuneSurface_HighlandOath')
    rune = custom_with(surface, 'RuneTexture')
    rune.set_editor_property('code', (ROOT / 'oath_surface.hlsl').read_text())
    rune.set_editor_property('description', DESCRIPTION)
    compile_and_save(surface)

    # Restore the original native-UV glyphs under this rune only. The rest
    # of each material (blade finishes, native wild ink and normal steel) is shared.
    for name in ('M_HighlandClaymoreSurface', 'M_HighlandClaymoreSurface_Whirlwind'):
        mat = u.load_asset('/Game/Weapons/HighlandClaymore20260922/Materials/' + name)
        for desc, result in (
            ('Native UV ink tint', 'return lerp(Tex,float3(.90,.46,.070),ink);'),
            ('Native blue ink or golden breathing', 'return float3(.78,.34,.040)*ink;')
        ):
            node = next(n for n in EDIT.get_material_expressions(mat)
                        if isinstance(n, u.MaterialExpressionCustom) and n.get_editor_property('description') == desc)
            code = node.get_editor_property('code')
            start = code.index('if(Oath>.5)')
            end = code.index('}', start)
            body = code.index('return ', start)
            node.set_editor_property('code', code[:body] + result + code[end:])
        compile_and_save(mat)

    sync_native_variants()
    rift = trail_asset('M_OathJudgmentRift', '/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift')
    # Duplicate the actual optical graph, including its refraction, normal map,
    # longitudinal reveal and both UV tapers. Replace only colour and coverage.
    for old, label, hlsl in (
        ('0.08,0.48,1.0', 'Oath gold rift emission', (ROOT/'oath_rift.hlsl').read_text()),
        ('Mask*0.13', 'Oath gold rift opacity', 'return Mask*.68;')
    ):
        nodes = [n for n in EDIT.get_material_expressions(rift) if isinstance(n,u.MaterialExpressionCustom)]
        node = next(n for n in nodes if n.get_editor_property('description') == label or old in n.get_editor_property('code'))
        node.set_editor_property('code', hlsl)
        node.set_editor_property('description', label)
    compile_and_save(rift)

    wake = trail_asset('M_OathJudgmentWake', '/Game/Weapons/Zhanmadao20261018/BeiweiRuneV1/Materials/M_BeiweiSwordTrail')
    node = custom_with(wake, 'UV.x')
    node.set_editor_property('code', (ROOT/'oath_wake.hlsl').read_text())
    node.set_editor_property('description', 'Oath gold wake on the animated blade trajectory')
    compile_and_save(wake)


if __name__ == '__main__':
    apply_gold()
