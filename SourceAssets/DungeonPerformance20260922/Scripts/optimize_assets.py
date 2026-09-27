"""Apply one bounded batch to the live authored dungeon's assets; no play or acceptance run.

Read the installed generator catalog, including new rooms and side sockets. Preserve full
fallback geometry/collision when enabling Nanite. Record each saved asset before continuing.
Re-run to process the next batch after a successful response (not after an uncertain write).
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / 'Receipts'
RECEIPTS.mkdir(parents=True, exist_ok=True)
receipt_path = RECEIPTS / 'assets.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {
    'saved_materials': {}, 'saved_meshes': {}, 'skipped': {}, 'tests_run': False}
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():
    raise RuntimeError('Preserve the running play session; asset preparation needs editor mode')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def persist():
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')


def clean_target(path):
    if path.split('.')[0] in dirty:
        raise RuntimeError('Preserve existing unsaved asset changes: ' + path)


# Analytic derivatives of the existing authored shape: identical WPO, opacity, color,
# roughness, lighting mode, UV conventions and local-to-world normal transform.
sheet_normal = '''// DungeonPerformance.AnalyticSheet.v1
float2 q=clamp(UV,float2(.001,.001),float2(.999,.999));
float a=q.x*2-1, v=q.y, pi=3.14159265;
float s=sin(pi*v), c=cos(pi*v), t=12*v-2.4*T+2*a, r=15*v-1.8*T;
float root=sqrt(max(10.,289.-110.25*a*a));
float top=17.-root+.3;
float3 du=float3(.68*cos(t)*s,2*(10.5*pow(max(0.,1-v),1.12)+.17)+.4*sin(r)*s,
    (220.5*a/root)*(1-v));
float3 dv=float3(1.2+.6*pi*c+.17*(12*cos(t)*s+pi*sin(t)*c),
    -11.76*a*pow(max(0.,1-v),.12)+.44*v*sin(T*1.35)+.20*a*(15*cos(r)*s+pi*sin(r)*c),
    -top-11.2+.32*v*sin(T*.9));
float3 n=normalize(cross(dv,du));
n.y+=sin(UV.x*48+UV.y*6-T*1.6)*.023;
return normalize(n)*float3(1,-1,1);'''
drop_normal = '''// DungeonPerformance.AnalyticDrops.v1
float2 q=float2(UV.x,clamp(UV.y,.002,.998));
float age=frac(T/2.35+Meta.r)*2.35, t=clamp(age-1.48,0.,Fall);
float theta=q.y*3.14159265, phi=q.x*6.2831853;
float st=sin(theta), ct=cos(theta), sp=sin(phi), cp=cos(phi);
float radius=.87*Meta.g*(age<1.48?(.22+.78*smoothstep(.08,1.48,age)):1.);
float radial=radius*st*(1-.16*ct);
float derivative=radius*3.14159265*(ct*(1-.16*ct)+.16*st*st);
float3 du=float3(-sp,cp,0)*radial*6.2831853;
float3 dv=float3(cp*derivative,sp*derivative,-radius*st*(1.1+.45*t/Fall)*3.14159265);
return normalize(cross(dv,du))*float3(1,-1,1);'''

for name, signature, code in [
    ('M_RoutePusSheet', 'shape.animated(q+float2(.001,0)', sheet_normal),
    ('M_RoutePusDrops', 'shape.position(q+float2(.001,0)', drop_normal),
]:
    path = '/Game/Dungeons/Routes20260922/Materials/' + name
    if path in receipt['saved_materials']:
        continue
    clean_target(path)
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing active route fluid material: ' + path)
    candidates = [e for e in L.get_material_expressions(mat) if isinstance(e, u.MaterialExpressionCustom)
                  and signature in e.get_editor_property('code')]
    if len(candidates) != 1:
        raise RuntimeError('Authored normal has changed; preserve its graph: ' + path)
    expression = candidates[0]
    previous = expression.get_editor_property('code')
    (RECEIPTS / (name + '-previous-normal.hlsl')).write_text(previous, encoding='utf-8')
    mat.modify()
    expression.set_editor_property('code', code)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation: ' + str(errors))
    if not E.save_loaded_asset(mat, False):
        raise RuntimeError('Cannot save ' + path)
    receipt['saved_materials'][path] = {'normal': 'analytic_v1', 'wpo_and_opacity': 'unchanged'}
    persist()

actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
generators = [a for a in actors if a.get_class().get_name() == 'AuthoredDungeonGenerator']
if not generators:
    raise RuntimeError('Open the authored random dungeon before applying its mesh settings')
parts = []
for generator in generators:
    catalog = json.loads(generator.get_editor_property('module_catalog_json'))
    for module in catalog['modules']:
        parts += module['parts']
        for side in module.get('side_sockets', []):
            parts += side.get('parts', [])
paths = sorted({p['mesh'] for p in parts if not p.get('fluid') and 'half_size' not in p
                and p['mesh'].startswith('/Game/Dungeons/')})
MES = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
saved_this_batch = 0
for path in paths:
    if path in receipt['saved_meshes'] or path in receipt['skipped']:
        continue
    clean_target(path)
    mesh = u.load_asset(path)
    if not isinstance(mesh, u.StaticMesh):
        raise RuntimeError('Missing rigid mesh: ' + path)
    used_slots = {MES.get_lod_material_slot(mesh, lod, section) for lod in range(MES.get_lod_count(mesh))
                  for section in range(mesh.get_num_sections(lod))}
    slots = mesh.get_editor_property('static_materials')
    materials = {slots[index].material_interface for index in used_slots if 0 <= index < len(slots)}
    for part in parts:
        if part['mesh'] == path:
            materials.update(u.load_asset(p) for index, p in enumerate(part.get('materials', [])) if p and index in used_slots)
    compatible = True
    for material in materials:
        while isinstance(material, u.MaterialInstance):
            material = material.get_editor_property('parent')
        if not isinstance(material, u.Material) or material.get_editor_property('blend_mode') not in (u.BlendMode.BLEND_OPAQUE, u.BlendMode.BLEND_MASKED):
            compatible = False
            break
    if not compatible:
        receipt['skipped'][path] = 'translucent or unsupported material; keep original rendering'
        persist()
        continue
    settings = MES.get_nanite_settings(mesh)
    previous = {key: str(settings.get_editor_property(key)) for key in (
        'enabled', 'explicit_tangents', 'generate_fallback', 'fallback_target', 'fallback_percent_triangles', 'fallback_relative_error')}
    settings.enabled = True
    settings.explicit_tangents = True
    settings.generate_fallback = u.NaniteGenerateFallback.ENABLED
    settings.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles = 1.0
    settings.fallback_relative_error = 0.0
    mesh.modify()
    MES.set_nanite_settings(mesh, settings, True)
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Cannot save ' + path)
    receipt['saved_meshes'][path] = {'previous': previous, 'collision': 'unchanged; full fallback mesh retained'}
    persist()
    saved_this_batch += 1
    if saved_this_batch >= 8:
        break
receipt['remaining'] = len(set(paths) - set(receipt['saved_meshes']) - set(receipt['skipped']))
receipt['stage'] = 'assets_saved' if receipt['remaining'] == 0 else 'next_batch'
persist()
print(json.dumps({'materials_saved': len(receipt['saved_materials']), 'meshes_saved': len(receipt['saved_meshes']),
                  'remaining': receipt['remaining'], 'receipt': str(receipt_path)}, ensure_ascii=False))
