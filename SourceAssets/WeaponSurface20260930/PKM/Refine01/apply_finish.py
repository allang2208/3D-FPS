"""Compile and save PKM-only finish instances on the current meshes.

Reuse each existing wet graph's source regions, normal/AO and single rain layer.
No mesh reimport, animation changes, scene execution or test pass.
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
ROOT = R['root']
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
        raise RuntimeError('PIE active; preserve current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT + '/') for p in dirty):
    raise RuntimeError('Unsaved PKM finish assets')
for path in {t[k] for t in R['targets'].values() for k in ('source', 'wet_source', 'base')}:
    if path.split('.')[0] in dirty or sha(disk(path)) != C['sources'][path]:
        raise RuntimeError('Changed or unsaved source material ' + path)
for path, bindings in R['bindings'].items():
    if path.split('.')[0] in dirty:
        raise RuntimeError('Unsaved target mesh ' + path)
    mesh = load(path)
    prop = 'materials' if C['meshes'][path]['skeletal'] else 'static_materials'
    slots = list(mesh.get_editor_property(prop))
    for b in bindings:
        s = slots[b['index']]
        target = R['targets'][b['key']]['asset']
        expected = target + '.' + target.rsplit('/', 1)[1] if path in receipt['meshes'] else b['before']
        if str(s.material_slot_name) != b['slot'] or s.material_interface.get_path_name() != expected:
            raise RuntimeError('Changed target slot ' + path + ' ' + b['slot'])
wetpath = C['weather']['path']
if wetpath.split('.')[0] in dirty:
    raise RuntimeError('Unsaved weather table')
weather = load(wetpath)

spec = R['texture']
if sha(Path(spec['source'])) != spec['sha256']:
    raise RuntimeError('Texture source changed; regenerate recipe')
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


def parameter(m, cls, name, value):
    n = L.create_material_expression(m, cls)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('group', 'PKM Fine Finish')
    n.set_editor_property('texture' if cls == u.MaterialExpressionTextureObjectParameter else 'default_value', value)
    return n


def add_input(n, name, source):
    pins = list(n.get_editor_property('inputs'))
    if name not in [str(i.get_editor_property('input_name')) for i in pins]:
        p = u.CustomInput()
        p.set_editor_property('input_name', name)
        pins.append(p)
        n.set_editor_property('inputs', pins)
    if not L.connect_material_expressions(source, '', n, name):
        raise RuntimeError('Material connection failed ' + name)


DETAIL = ('float3 w=pow(abs(normalize(N)),4);w/=max(dot(w,float3(1,1,1)),.0001);'
    'float3 q=P/4.;return Texture2DSample(FinishTex,FinishTexSampler,q.yz)*w.x+'
    'Texture2DSample(FinishTex,FinishTexSampler,q.xz+float2(.37,.61))*w.y+'
    'Texture2DSample(FinishTex,FinishTexSampler,q.xy+float2(.71,.13))*w.z;')


def master(t):
    source = t['base']
    key = source + '|' + t['usage']
    if key in receipt['masters']:
        return load(receipt['masters'][key]['path'])
    path = ROOT + '/Master/M_PKM_R01_' + hashlib.sha1(key.encode()).hexdigest()[:12]
    if E.does_asset_exist(path):
        raise RuntimeError('Adapter destination occupied ' + path)
    m = E.duplicate_asset(source, path)
    if not m:
        raise RuntimeError('Material clone failed')
    cs = {str(n.get_editor_property('description')): n for n in L.get_material_expressions(m)
        if isinstance(n, u.MaterialExpressionCustom)}
    detail, color, rough = [cs[k] for k in ('PKM20 physical micro finish', 'PKM20 restrained scuffs', 'PKM20 varied roughness')]
    tex = parameter(m, u.MaterialExpressionTextureObjectParameter, 'R01_GrainTexture', grain)
    tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    add_input(detail, 'FinishTex', tex)
    detail.set_editor_property('code', DETAIL)
    parameters = {}
    for name, value in t['scalars'].items():
        if name.startswith('R01_'):
            parameters[name] = parameter(m, u.MaterialExpressionScalarParameter, name, value)
    tint = parameter(m, u.MaterialExpressionVectorParameter, 'R01_FinishTint', u.LinearColor(*t['vectors']['R01_FinishTint'], 1.))
    add_input(color, 'FinishTint', tint)
    add_input(color, 'SourceBlend', parameters['R01_ColorWeight'])
    for pin, param in [('FinishCenter', 'R01_Roughness'), ('GrainAmplitude', 'R01_GrainRoughness'),
        ('VariationAmplitude', 'R01_VariationRoughness'), ('SourceWeight', 'R01_SourceRoughnessWeight'),
        ('Stipple', 'R01_PolymerStipple')]:
        add_input(rough, pin, parameters[param])
    if t['family'] == 'metal':
        region = 'saturate(Region)*smoothstep(.20,.60,Metal)'
        color_code = ('float marks=smoothstep(.32,.66,max(Base.r,max(Base.g,Base.b)));'
            'float shade=lerp(1.,clamp(dot(Base,float3(.2126,.7152,.0722))/.034,.75,1.25),.06);'
            'float3 finish=lerp(Base,FinishTint*shade,SourceBlend);'
            'return lerp(Base,finish,' + region + '*(1-marks));')
        cs['PKM20 fine exposed metal'].set_editor_property('code', 'return Base;')
    elif t['family'] == 'paint':
        region = 'saturate(Region)'
        color_code = ('float shade=lerp(1.,clamp(dot(Base,float3(.2126,.7152,.0722))/.028,.9,1.1),.10);'
            'return lerp(Base,FinishTint*shade,saturate(Region));')
        cs['PKM20 fine exposed metal'].set_editor_property('code', 'return lerp(Base,0.,saturate(Region));')
    else:
        region = 'saturate(Region)*(1-smoothstep(.20,.60,Metal))'
        color_code = ('float marks=smoothstep(.32,.66,max(Base.r,max(Base.g,Base.b)));'
            'return lerp(Base,lerp(Base,FinishTint,SourceBlend),' + region + '*(1-marks));')
    rough_code = ('float structure=clamp((Base-.40)*SourceWeight,-.025,.025);'
        'float finish=FinishCenter+structure+(Detail.r-.5)*2.*GrainAmplitude'
        '+(Detail.g-.5)*2.*VariationAmplitude+(Detail.a-.375)*Stipple;'
        'return lerp(Base,clamp(finish,.25,.85),' + region + ');')
    color.set_editor_property('code', color_code)
    rough.set_editor_property('code', rough_code)
    # Keep the inherited, single PKM weather chain attached to these dry inputs.
    if 'PKM20 wet roughness' not in cs or 'PKM20 subtle water beads' not in cs:
        raise RuntimeError('Expected PKM wet source graph')
    if t['usage'] == 'static':
        for prop in ('used_with_skeletal_mesh', 'used_with_morph_targets', 'used_with_clothing'):
            m.set_editor_property(prop, False)
    E.set_metadata_tag(m, 'WeaponSurfaceGraph', R['version'])
    E.set_metadata_tag(m, 'WeaponSurfaceSourceGraph', source)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compilation failed ' + path + ': ' + str(errors))
    save(m)
    receipt['masters'][key] = {'path': m.get_path_name(), 'source': source, 'usage': t['usage'], 'saved': True}
    record()
    return m


for index, (key, t) in enumerate(R['targets'].items()):
    if key in receipt['instances']:
        continue
    parent = master(t)
    path = t['asset']
    if E.does_asset_exist(path):
        raise RuntimeError('Instance destination occupied ' + path)
    source = load(t['wet_source'])
    if isinstance(source, u.MaterialInstanceConstant):
        mi = E.duplicate_asset(t['wet_source'], path)
    else:
        dest, name = path.rsplit('/', 1)
        mi = A.create_asset(name, dest, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    if not mi:
        raise RuntimeError('Create instance failed ' + path)
    L.set_material_instance_parent(mi, parent)
    # Preserve effective source overrides, including inherited instance values.
    original = C['materials'][t['source']]['parameters']
    for name, value in {**original['scalar'], **t['scalars']}.items():
        L.set_material_instance_scalar_parameter_value(mi, name, float(value))
    for name, value in {**original['vector'], **t['vectors']}.items():
        L.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*(value if len(value) == 4 else value + [1.])))
    for name, value in original['texture'].items():
        if value:
            L.set_material_instance_texture_parameter_value(mi, name, load(value))
    L.set_material_instance_texture_parameter_value(mi, 'R01_GrainTexture', grain)
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', R['version'])
    save(mi)
    receipt['instances'][key] = {'path': mi.get_path_name(), 'parent': parent.get_path_name(), 'role': t['role'], 'saved': True}
    record()
    if (index + 1) % 10 == 0:
        print('WEAPON_SURFACE_PKM_R01_MATERIALS', index + 1, flush=True)

if not receipt['weather']:
    mapping = dict(weather.get_editor_property('wet_materials'))
    for row in receipt['instances'].values():
        mapping[row['path']] = load(row['path'])
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
    slots = list(mesh.get_editor_property(prop))
    selected = {}
    for b in bindings:
        slot = slots[b['index']]
        target = receipt['instances'][b['key']]['path']
        slot.material_interface = load(target)
        slots[b['index']] = slot
        selected[b['slot']] = target
    backup(path)
    mesh.set_editor_property(prop, slots)
    E.set_metadata_tag(mesh, 'PKMSurfaceFinishRevision', R['version'])
    save(mesh)
    receipt['meshes'][path] = {'saved': True, 'bindings': selected, 'geometry_changed': False, 'saved_sha256': sha(disk(path))}
    record()
    print('WEAPON_SURFACE_PKM_R01_BOUND', path, len(selected), flush=True)
receipt['complete'] = True
record()
print('WEAPON_SURFACE_PKM_R01_SAVED', len(receipt['instances']), 'instances', len(receipt['masters']),
    'adapters', len(receipt['meshes']), 'meshes; geometry_changed=False; tested=False', flush=True)
