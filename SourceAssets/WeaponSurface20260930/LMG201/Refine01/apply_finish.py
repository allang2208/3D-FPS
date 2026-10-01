"""Create fine-finish adapters/instances, bind current meshes and save weather mapping.
Preserve current geometry, cloth, belt, normals and mixed-material region masks.
Production only: no PIE, screenshots, preview rendering or test pass.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
L, E, A = u.MaterialEditingLibrary, u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
C = json.loads((O / 'Input/current.json').read_text())
R = json.loads((O / 'recipe.json').read_text())
ROOT = '/Game/Weapons/LMG201/SurfaceStandard20261001'
RP = O / 'apply_receipt.json'
receipt = json.loads(RP.read_text()) if RP.exists() else {'version': R['version'], 'textures': {},
    'masters': {}, 'instances': {}, 'meshes': {}, 'weather': {}, 'backups': {},
    'complete': False, 'geometry_changed': False, 'tested': False}


def record():
    RP.write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def disk(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing production asset ' + path)
    return obj


def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Asset save failed ' + obj.get_path_name())


def backup(path):
    if path in receipt['backups']:
        return
    dest = O / 'Before' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(disk(path), dest)
    receipt['backups'][path] = str(dest)
    record()


dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE active; preserve the current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT + '/') for p in dirty):
    raise RuntimeError('Unsaved 201 finish assets')
sources = {t[k] for t in R['targets'].values() for k in ('source', 'base')}
for path in sources:
    if path.split('.')[0] in dirty or sha(disk(path)) != C['sources'][path]:
        raise RuntimeError('Changed or unsaved material source ' + path)
for path, bindings in R['bindings'].items():
    if path.split('.')[0] in dirty:
        raise RuntimeError('Unsaved mesh ' + path)
    mesh = load(path)
    prop = 'materials' if C['meshes'][path]['skeletal'] else 'static_materials'
    current = {str(s.material_slot_name): s.material_interface.get_path_name() if s.material_interface else None
        for s in mesh.get_editor_property(prop)}
    for b in bindings:
        target = R['targets'][b['key']]['asset']
        expected = target + '.' + target.rsplit('/', 1)[1] if path in receipt['meshes'] else b['before']
        if current.get(b['slot']) != expected:
            raise RuntimeError('Changed target slot ' + path + ' ' + b['slot'])
wetpath = C['weather']['path']
if wetpath.split('.')[0] in dirty:
    raise RuntimeError('Unsaved weather map ' + wetpath)
weather = load(wetpath)

spec = R['texture']
if sha(Path(spec['source'])) != spec['sha256']:
    raise RuntimeError('Regenerate recipe for changed texture source')
if not receipt['textures']:
    if E.does_asset_exist(spec['asset']):
        raise RuntimeError('Texture destination occupied')
    task = u.AssetImportTask()
    task.filename = spec['source']
    task.destination_path, task.destination_name = spec['asset'].rsplit('/', 1)
    task.automated, task.replace_existing, task.save = True, False, False
    A.import_asset_tasks([task])
    tex = load(spec['asset'])
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
    tex.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
    tex.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
    E.set_metadata_tag(tex, 'WeaponSurfaceVersion', R['version'])
    save(tex)
    receipt['textures'][spec['asset']] = {'saved': True, 'source_sha256': spec['sha256']}
    record()
grain = load(spec['asset'])


def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def wire(src, dest, pin):
    n, output = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, output, dest, pin):
        raise RuntimeError('Connect failed ' + pin)


def input_of(m, n, name):
    names = [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]
    src = L.get_inputs_for_material_expression(m, n)[names.index(name)]
    return src, str(L.get_input_node_output_name_for_material_expression(n, src))


def output_of(m, prop):
    return L.get_material_property_input_node(m, prop), str(L.get_material_property_input_node_output_name(m, prop))


def custom(m, label, code, inputs, size):
    n = node(m, u.MaterialExpressionCustom, description=label, code=code,
        output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for name in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', name)
        pins.append(p)
    n.set_editor_property('inputs', pins)
    for name, src in inputs.items():
        wire(src, n, name)
    return n


def output(m, n, prop):
    if not L.connect_material_property(n, '', prop):
        raise RuntimeError('Connect material output failed')


DETAIL = ('float3 w=pow(abs(normalize(N)),4);w/=max(dot(w,float3(1,1,1)),.0001);'
    'float3 q=P/4.;return Texture2DSample(T,TSampler,q.yz)*w.x+'
    'Texture2DSample(T,TSampler,q.xz+float2(.37,.61))*w.y+'
    'Texture2DSample(T,TSampler,q.xy+float2(.71,.13))*w.z;')


def master(t):
    source = t['base']
    if source in receipt['masters']:
        return load(receipt['masters'][source]['path'])
    path = ROOT + '/Master/M_LMG201_R01_' + hashlib.sha1(source.encode()).hexdigest()[:12]
    if E.does_asset_exist(path):
        raise RuntimeError('Adapter destination occupied ' + path)
    m = E.duplicate_asset(source, path)
    if not m:
        raise RuntimeError('Material clone failed')
    expr = list(L.get_material_expressions(m))
    cs = {str(n.get_editor_property('description')): n for n in expr if isinstance(n, u.MaterialExpressionCustom)}
    params = {str(n.get_editor_property('parameter_name')): n for n in expr
        if isinstance(n, (u.MaterialExpressionScalarParameter, u.MaterialExpressionVectorParameter))}
    zero = node(m, u.MaterialExpressionConstant, r=0.)
    one = node(m, u.MaterialExpressionConstant, r=1.)
    settings = {}
    for name, default in [('GrainRoughness', .012), ('MottleRoughness', .005), ('PolymerStipple', 0.), ('EdgeHighlight', .035)]:
        settings[name] = node(m, u.MaterialExpressionScalarParameter,
            parameter_name='R01_' + name, default_value=default, group='201 Fine Finish')
    tex = node(m, u.MaterialExpressionTextureObjectParameter, parameter_name='R01_GrainTexture',
        texture=grain, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, group='201 Fine Finish')
    if t['adapter'] in ('G43', 'F50'):
        desc = 'G43 attached physical coating detail' if t['adapter'] == 'G43' else 'F50 shared 6 cm coating texture'
        detail = cs[desc]
        detail.set_editor_property('code', DETAIL)
        wire(tex, detail, 'T')
        if t['adapter'] == 'G43':
            old = cs['G43 roughness hierarchy and single wet film']
            inputs = {k: input_of(m, old, k) for k in ('Base', 'Center', 'D', 'Edge', 'Region', 'Wet')}
            cs['G43 base coating and restrained wear'].set_editor_property('code',
                'float v=dot(Base,float3(.2126,.7152,.0722));'
                'float3 tone=Tint*lerp(1.,clamp(v/.032,.7,1.3),.04);'
                'tone=lerp(tone,Wear,saturate(Edge)*.025);'
                'return lerp(Base,tone,Region)*(1-saturate(Wet)*.12);')
        else:
            old = cs['F50 fine roughness and one wet film']
            inputs = {k: input_of(m, old, k) for k in ('Center', 'D', 'Wet')}
            inputs.update(Base=inputs['Center'], Edge=zero, Region=one)
            cs['F50 restrained coating color'].set_editor_property('code', 'return Tint*(1-saturate(Wet)*.12);')
        rough_code = ('float fine=Center+(D.r-.5)*2.*GrainRoughness+(D.g-.5)*2.*MottleRoughness'
            '+(D.a-.375)*PolymerStipple-Edge*EdgeHighlight;'
            'float r=lerp(Base,clamp(fine,.20,.85),Region);'
            'return lerp(r,max(.20,r*.78),saturate(Wet)*Region);')
    else:
        # Drum sources include historical nested wet wrappers. Make those dry
        # inputs and append one final film, retaining source normals and AO.
        for n in expr:
            if isinstance(n, u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name')) == 'WeaponWetness':
                n.set_editor_property('parameter_name', 'R01_LegacyWetDisabled')
                n.set_editor_property('default_value', 0.)
        wet = node(m, u.MaterialExpressionScalarParameter, parameter_name='WeaponWetness', default_value=0.)
        pos = node(m, u.MaterialExpressionVertexInterpolator)
        nor = node(m, u.MaterialExpressionVertexInterpolator)
        wire(node(m, u.MaterialExpressionPreSkinnedPosition), pos, 'VS')
        wire(node(m, u.MaterialExpressionPreSkinnedNormal), nor, 'VS')
        detail = custom(m, '201 R01 physical drum grain', DETAIL, {'P': pos, 'N': nor, 'T': tex}, 4)
        drycolor = output_of(m, u.MaterialProperty.MP_BASE_COLOR)
        dryrough = output_of(m, u.MaterialProperty.MP_ROUGHNESS)
        color = custom(m, '201 R01 drum restrained source and single wet film',
            'return lerp(Tint,Base,.25)*(1-saturate(Wet)*.12);',
            {'Base': drycolor, 'Tint': params['201FinishTint'], 'Wet': wet}, 3)
        output(m, color, u.MaterialProperty.MP_BASE_COLOR)
        inputs = {'Base': dryrough, 'Center': params['201FinishRoughness'], 'D': detail,
            'Edge': zero, 'Region': one, 'Wet': wet}
        rough_code = ('float r=clamp(Center+(Base-Center)*.30+(D.r-.5)*2.*GrainRoughness'
            '+(D.g-.5)*2.*MottleRoughness+(D.a-.375)*PolymerStipple,.20,.85);'
            'return lerp(r,max(.20,r*.78),saturate(Wet));')
    inputs.update(settings)
    rough = custom(m, '201 R01 fine roughness and single wet film', rough_code, inputs, 1)
    output(m, rough, u.MaterialProperty.MP_ROUGHNESS)
    E.set_metadata_tag(m, 'WeaponSurfaceGraph', R['version'])
    E.set_metadata_tag(m, 'WeaponSurfaceSourceGraph', source)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compilation failed ' + path + ' ' + str(errors))
    save(m)
    receipt['masters'][source] = {'path': m.get_path_name(), 'adapter': t['adapter'], 'saved': True}
    record()
    return m


for index, (key, t) in enumerate(R['targets'].items()):
    if key in receipt['instances']:
        continue
    parent = master(t)
    path = t['asset']
    if E.does_asset_exist(path):
        raise RuntimeError('Instance destination occupied ' + path)
    dest, name = path.rsplit('/', 1)
    mi = A.create_asset(name, dest, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    if not mi:
        raise RuntimeError('Create instance failed ' + path)
    L.set_material_instance_parent(mi, parent)
    for name, value in t['scalars'].items():
        L.set_material_instance_scalar_parameter_value(mi, name, float(value))
    for name, value in t['vectors'].items():
        L.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*value, 1))
    L.set_material_instance_texture_parameter_value(mi, 'R01_GrainTexture', grain)
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', R['version'])
    save(mi)
    receipt['instances'][key] = {'path': mi.get_path_name(), 'parent': parent.get_path_name(), 'role': t['role'], 'saved': True}
    record()
    if (index + 1) % 10 == 0:
        print('WEAPON_SURFACE_201_R01_MATERIALS', index + 1, flush=True)

if not receipt['weather']:
    mapping = dict(weather.get_editor_property('wet_materials'))
    for v in receipt['instances'].values():
        mapping[v['path']] = load(v['path'])
    backup(wetpath)
    weather.set_editor_property('wet_materials', mapping)
    save(weather)
    receipt['weather'] = {'path': wetpath, 'added_self_mappings': len(receipt['instances']), 'saved': True}
    record()

for path, bindings in R['bindings'].items():
    if path in receipt['meshes']:
        continue
    mesh = load(path)
    prop = 'materials' if C['meshes'][path]['skeletal'] else 'static_materials'
    slots = mesh.get_editor_property(prop)
    selected = {b['slot']: receipt['instances'][b['key']]['path'] for b in bindings}
    for i, slot in enumerate(slots):
        name = str(slot.material_slot_name)
        if name in selected:
            slot.material_interface = load(selected[name])
            slots[i] = slot
    backup(path)
    mesh.set_editor_property(prop, slots)
    E.set_metadata_tag(mesh, '201SurfaceFinishRevision', R['version'])
    save(mesh)
    receipt['meshes'][path] = {'saved': True, 'bindings': selected, 'geometry_changed': False, 'saved_sha256': sha(disk(path))}
    record()
    print('WEAPON_SURFACE_201_R01_BOUND', path, len(selected), flush=True)
receipt['complete'] = True
record()
print('WEAPON_SURFACE_201_R01_SAVED', len(receipt['instances']), 'instances', len(receipt['masters']),
    'adapters', len(receipt['meshes']), 'meshes; geometry_changed=False; tested=False', flush=True)
