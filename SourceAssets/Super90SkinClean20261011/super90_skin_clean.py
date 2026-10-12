"""Super90 surface-only cleanup. No geometry, skin weights, UV or rig editing."""
import hashlib
import json
from pathlib import Path
import unreal as u

O = Path('D:/FPS3D/FPSGAME/SourceAssets/Super90SkinClean20261011')
SOURCE = '/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials'
DEST = '/Game/Weapons/Super90/SkinClean20261011/Materials'
MARKER = '// Super90 skin line cleanup 20261011: material only; existing coordinates.'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()


def replace_one(code, old, new):
    if code.count(old) != 1:
        raise RuntimeError('Skin source no longer matches the local surface recipe: ' + old[:80])
    return code.replace(old, new, 1)


def clean_shader(source):
    # Preserve the current graph, maps, coordinate interpretation, skin tint,
    # nails and scattering. This is separate from the rejected twist revision.
    code = replace_one(source, 'float skinDetail=(1-nail)*(1-.60*palmDetail);',
        'float skinDetail=(1-nail)*(1-.60*palmDetail);\n'
        'float cleanPalm=saturate(Surface.a)*(1-ForearmMode);\n'
        '// Filter the micro field only, leaving anatomical atlas UVs intact.\n'
        'float3 cleanDx=dx*2.0,cleanDy=dy*2.0;')
    for projection in ('yz', 'xz', 'xy'):
        code = replace_one(code,
            'MicroTextureSampler,q.' + projection + ',dx.' + projection + ',dy.' + projection,
            'MicroTextureSampler,q.' + projection + ',cleanDx.' + projection + ',cleanDy.' + projection)
        code = replace_one(code,
            'ColourDetailSampler,q.' + projection + ',dx.' + projection + ',dy.' + projection,
            'ColourDetailSampler,q.' + projection + ',cleanDx.' + projection + ',cleanDy.' + projection)
    code = replace_one(code, 'MicroNormalStrength*.22*fade*skinDetail*(8/tile)',
        'MicroNormalStrength*lerp(.11,.065,cleanPalm)*fade*skinDetail*(8/tile)')
    code = replace_one(code, 'min(1,.10/max(length(microSlope),.000001))',
        'min(1,.055/max(length(microSlope),.000001))')
    code = replace_one(code,
        'AnatomicalNormal=normalize(float3(AnatomicalNormal.xy*lerp(.65,1,nail),AnatomicalNormal.z));',
        '// Keep the palm creases readable while softening dorsal and wrist relief.\n'
        'float cleanAnatomy=lerp(.42,.62,cleanPalm)*lerp(.75,1,handAnatomy);\n'
        'AnatomicalNormal=normalize(float3(AnatomicalNormal.xy*lerp(cleanAnatomy,1,nail),AnatomicalNormal.z));')
    code = replace_one(code, 'float3 colour=lerp(sharedColour,BaseColour,handAnatomy);',
        '// The atlas author multiplies skin by 1-.10*crease. Retain a 3.5%\n'
        '// painted crease instead; never lift the nail colour with this term.\n'
        'float cleanCrease=saturate(Surface.b);\n'
        'float cleanDarkLine=(1-.035*cleanCrease)/max(1-.10*cleanCrease,.90);\n'
        'float3 cleanBaseColour=BaseColour*lerp(1,cleanDarkLine,1-nail);\n'
        'float3 colour=lerp(sharedColour,cleanBaseColour,handAnatomy);')
    code = replace_one(code, 'ColourDetailStrength*.20*skinDetail*fade',
        'ColourDetailStrength*.065*skinDetail*fade')
    code = replace_one(code,
        'float rough=lerp(sharedRough,lerp(sharedRough,Surface.g,.65),handAnatomy);',
        'float rough=lerp(sharedRough,lerp(sharedRough,Surface.g,lerp(.38,.65,nail)),handAnatomy);')
    code = replace_one(code, '-.48)*skinDetail*.12*fade;', '-.48)*skinDetail*.045*fade;')
    return MARKER + '\n' + code


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def create_materials():
    if (O / 'REJECTED.json').exists():
        raise RuntimeError('This surface revision is retired.')
    (O / 'Before/SourceShaders').mkdir(parents=True, exist_ok=True)
    report = {}
    for suffix in ('Arms', 'Hands'):
        source_parent = u.load_asset(SOURCE + '/M_BareFamily_' + suffix)
        source_instance = u.load_asset(SOURCE + '/MI_BareFamily_' + suffix)
        if source_parent is None or source_instance is None:
            raise RuntimeError('Missing current V7 material ' + suffix)
        custom_source = L.get_material_property_input_node(source_parent, u.MaterialProperty.MP_NORMAL)
        source_code = custom_source.get_editor_property('code')
        code = clean_shader(source_code)
        before = O / 'Before/SourceShaders' / ('M_BareFamily_' + suffix + '.hlsl')
        if not before.exists():
            before.write_text(source_code)
        name = 'M_Super90SkinClean_' + suffix
        parent = u.load_asset(DEST + '/' + name) if E.does_asset_exist(DEST + '/' + name) else None
        if parent is None:
            parent = A.duplicate_asset(name, DEST, source_parent)
        custom = L.get_material_property_input_node(parent, u.MaterialProperty.MP_NORMAL)
        custom.set_editor_property('code', code)
        errors = L.recompile_material(parent)
        if errors:
            raise RuntimeError('Skin compilation failed: ' + str(errors))
        E.set_metadata_tag(parent, 'Super90SkinClean', '20261011: micro filtering, softer dark lines, regional skin relief')
        save(parent)
        iname = 'MI_Super90SkinClean_' + suffix
        instance = u.load_asset(DEST + '/' + iname) if E.does_asset_exist(DEST + '/' + iname) else None
        if instance is None:
            instance = A.duplicate_asset(iname, DEST, source_instance)
        L.set_material_instance_parent(instance, parent)
        L.update_material_instance(instance)
        save(instance)
        (O / (name + '.hlsl')).write_text(code)
        report[suffix] = dict(parent=parent.get_path_name(), instance=instance.get_path_name(),
            source_parent=source_parent.get_path_name(), source_instance=source_instance.get_path_name(),
            source_shader_sha256=hashlib.sha256(source_code.encode()).hexdigest(),
            shader_sha256=hashlib.sha256(code.encode()).hexdigest(), texture_sources_reused=True)
        print('SUPER90_SKIN_CLEAN_MATERIAL_SAVED', suffix, flush=True)
    (O / 'materials_saved.json').write_text(json.dumps(report, indent=2))
    return report


def bind_materials(mesh):
    slots = [slot.copy() for slot in mesh.materials]
    changed = []
    for index, slot in enumerate(slots):
        name = str(slot.material_slot_name)
        if not name.startswith('Manny_S90_Skin_'):
            continue
        suffix = 'Hands' if 'hand' in name.lower() else 'Arms'
        material = u.load_asset(DEST + '/MI_Super90SkinClean_' + suffix)
        if material is None:
            raise RuntimeError('Missing saved Super90 surface ' + suffix)
        changed.append(dict(index=index, slot=name,
            before=slot.material_interface.get_path_name() if slot.material_interface else None,
            after=material.get_path_name()))
        slot.material_interface = material
    if changed:
        mesh.set_editor_property('materials', slots)
    return changed
