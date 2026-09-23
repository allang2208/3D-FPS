"""Production edits only: static magazine shader usage and compatible plaza Nanite data."""
import json, shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).parent;PROJECT=ROOT.parents[1]
BACKUP_ROOT=PROJECT/'trash/main-scene-performance-20260923/SourceAssets/MainScenePerformance20260923/Before'
RECEIPTS=ROOT/'Receipts';RECEIPTS.mkdir(exist_ok=True)
receipt_file=RECEIPTS/'assets.json'
report=json.loads(receipt_file.read_text(encoding='utf-8')) if receipt_file.exists() else {'materials':{},'meshes':{},'skipped':{},'runtime_tested':False}
report.setdefault('instance_materials',{})
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():raise RuntimeError('Play session active; preserve it')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def persist():receipt_file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def prepare(path):
    package=path.split('.')[0]
    if package in dirty:raise RuntimeError('Preserve unsaved asset '+package)
    source=PROJECT/'Content'/Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    dest=BACKUP_ROOT/'Content'/source.relative_to(PROJECT/'Content')
    if source.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())

# These graphs belong exclusively to static magazine attachments. Their cloned rifle bases
# inherited skeletal usage; the 7-channel seam data is legal for these static meshes, not GPUSkin.
# Retain every UV and graph node: no seam, normal, roughness or wetness approximation.
for name in ['AKM','AKMWet','M4','M4Wet']:
    path='/Game/Weapons/ExtMagContinuity20260919/Materials/M_'+name+'_Continuous_Graph'
    if path in report['materials']:continue
    prepare(path);mat=u.load_asset(path)
    if not mat:continue
    before={k:bool(mat.get_editor_property(k)) for k in ['used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing','automatically_set_usage_in_editor']}
    mat.modify()
    for k in before:mat.set_editor_property(k,False)
    L.recompile_material(mat);save(mat)
    report['materials'][path]={'previous':before,'policy':'static attachment only; original UV0-6 and seam graph retained'};persist()

actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
meshes={}
for actor in actors:
    if not isinstance(actor,u.StaticMeshActor):continue
    tags={str(t) for t in actor.tags};c=actor.static_mesh_component;m=c.static_mesh
    if not m or 'ColdSteel.MainPlaza.Paving' in tags:continue
    if 'ColdSteel.MainPlaza.Generated' in tags or m.get_name()=='SM_RomanPavilion_Dome_20':meshes[m.get_path_name()]=m
count=0
for path,mesh in sorted(meshes.items()):
    if path in report['meshes'] or path in report['skipped']:continue
    prepare(path)
    materials={s.material_interface for s in mesh.static_materials}
    for actor in actors:
        if isinstance(actor,u.StaticMeshActor) and actor.static_mesh_component.static_mesh==mesh:
            materials.update(actor.static_mesh_component.get_materials())
    bases={m.get_base_material() for m in materials if m}
    if not bases or any(m.get_editor_property('blend_mode') not in (u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED) for m in bases):
        report['skipped'][path]='retain unsupported or translucent materials';persist();continue
    # Actor-position shaders would change meaning after grouping. Animated/displaced materials
    # stay on their original geometry path as well.
    if any(L.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET) or
           any(e.get_class().get_name()=='MaterialExpressionActorPositionWS' for e in L.get_material_expressions(m)) for m in bases):
        report['skipped'][path]='retain actor-position or vertex-displaced material';persist();continue
    for material in sorted(bases,key=lambda m:m.get_path_name()):
        material_path=material.get_path_name()
        if material_path in report['instance_materials']:continue
        previous={k:bool(material.get_editor_property(k)) for k in ['used_with_instanced_static_meshes','used_with_nanite']}
        if not all(previous.values()):
            prepare(material_path);material.modify()
            for k in previous:material.set_editor_property(k,True)
            L.recompile_material(material);save(material)
        report['instance_materials'][material_path]={'previous':previous,'nanite_and_instances':True};persist()
    settings=mesh.get_editor_property('nanite_settings')
    before={k:str(settings.get_editor_property(k)) for k in ['enabled','explicit_tangents','generate_fallback','fallback_target','fallback_percent_triangles','fallback_relative_error']}
    mesh.modify();settings.enabled=True;settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED
    settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.0;settings.fallback_relative_error=0.0
    # set_editor_property emits the same Nanite property-change/build notification and
    # works in commandlets, where StaticMeshEditorSubsystem is not instantiated.
    mesh.set_editor_property('nanite_settings',settings)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite production build failed '+path)
    save(mesh)
    report['meshes'][path]={'previous':before,'collision':'unchanged','fallback':'full geometry'};count+=1;persist()
    if count>=8:break
report['remaining']=len(set(meshes)-set(report['meshes'])-set(report['skipped']));persist()
print(json.dumps({'materials':len(report['materials']),'nanite_meshes':len(report['meshes']),'remaining':report['remaining'],'skipped':report['skipped']},ensure_ascii=False))
