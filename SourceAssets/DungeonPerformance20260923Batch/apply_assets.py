"""Author bounded asset batches. No play session, camera capture or acceptance test."""
import json, shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).parent
PROJECT=ROOT.parents[1]
RECEIPT=ROOT/'Receipts/assets.json'
RECEIPT.parent.mkdir(parents=True,exist_ok=True)
report=json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else {
    'meshes':{},'materials':{},'unchanged':{},'skipped':{},'runtime_tested':False}
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active play session; asset batch needs editor mode')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

def persist():
    RECEIPT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def prepare(path):
    package=path.split('.')[0]
    if package in dirty:raise RuntimeError('Preserve unsaved target '+package)
    source=PROJECT/'Content'/Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    dest=ROOT/'Before/Content'/source.relative_to(PROJECT/'Content')
    if not source.exists():raise RuntimeError('Missing asset file '+str(source))
    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())

# The ASH-12 extended magazine is a static attachment; its seven seam UV channels
# must not inherit the cloned rifle's GPUSkin shader permutations.
for name in ('ASH12','ASH12Wet'):
    path='/Game/Weapons/ASH12/ExtendedMagazine20260919/Materials/M_'+name+'_Continuous_Graph'
    if path in report['materials']:continue
    mat=u.load_asset(path)
    if not isinstance(mat,u.Material):raise RuntimeError('Missing static ASH-12 seam material')
    before={key:bool(mat.get_editor_property(key)) for key in (
        'used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing','automatically_set_usage_in_editor')}
    if any(before.values()):
        prepare(path);mat.modify()
        for key in before:mat.set_editor_property(key,False)
        if L.recompile_material(mat):raise RuntimeError('ASH-12 material compilation failed')
        save(mat)
    report['materials'][path]={'previous':before,'saved':any(before.values()),'graph_and_uvs':'unchanged'}
    persist()

paths=json.loads((ROOT/'mesh-targets.json').read_text(encoding='utf-8'))
# Earlier batch classified this rigid grille by its GateWater folder; use mesh names only.
report['skipped'].pop('/Game/Dungeons/AtmosphereV2/GateWater/Meshes/SM_DungeonRefinedGrille',None)
count=0
for path in paths:
    if any(path in report[key] for key in ('meshes','unchanged','skipped')):continue
    # Retain authored fluid deformation and thin transparent surfaces.
    if any(word in path.rsplit('/',1)[-1].lower() for word in ('pus','slime','water','puddle','cobweb','curtain')):
        report['skipped'][path]='fluid, deforming or thin transparent geometry';persist();continue
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Missing dungeon static mesh '+path)
    triangles=mesh.get_num_triangles(0)
    settings=mesh.get_editor_property('nanite_settings').copy()
    if triangles<10000:
        report['unchanged'][path]={'triangles':triangles,'reason':'small mesh; retain authored LODs'};persist();continue
    if settings.enabled:
        report['unchanged'][path]={'triangles':triangles,'reason':'Nanite already enabled'};persist();continue
    materials={s.material_interface.get_base_material() for s in mesh.get_editor_property('static_materials') if s.material_interface}
    if not materials or any(m.get_editor_property('blend_mode') not in (u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED) for m in materials):
        report['skipped'][path]='unsupported material blend mode';persist();continue
    # Avoid rewriting animated material geometry. This deliberately does not call
    # get_material_property_input_node, which crashes this editor's remote bridge.
    if any(any(e.get_class().get_name() in ('MaterialExpressionTime','MaterialExpressionSimpleGrassWind')
               for e in L.get_material_expressions(m)) for m in materials):
        report['skipped'][path]='animated material; retain existing rendering';persist();continue
    previous={key:str(settings.get_editor_property(key)) for key in (
        'enabled','explicit_tangents','generate_fallback','fallback_target','fallback_percent_triangles','fallback_relative_error')}
    prepare(path);mesh.modify()
    settings.enabled=True;settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED
    settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.0;settings.fallback_relative_error=0.0
    mesh.set_editor_property('nanite_settings',settings)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite data build failed '+path)
    save(mesh)
    report['meshes'][path]={'previous':previous,'triangles':triangles,'fallback':'full geometry','collision':'unchanged'}
    count+=1;persist()
    if count>=6:break
report['remaining']=len(set(paths)-set(report['meshes'])-set(report['unchanged'])-set(report['skipped']))
report['stage']='assets_saved' if report['remaining']==0 else 'next_batch'
persist()
print(json.dumps({'saved_meshes':len(report['meshes']),'unchanged':len(report['unchanged']),
                  'skipped':len(report['skipped']),'remaining':report['remaining'],'runtime_tested':False}))
