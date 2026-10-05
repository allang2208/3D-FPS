"""Reduce a duplicate of the high-poly master, then export only its reduced geometry."""
from pathlib import Path
import sys, traceback
sys.path.insert(0, str(Path(__file__).resolve().parent))
from author_common import *

record = dict(revision=REV, stage='started', saved=[], runtime_tested=False, rendered=False,
              source_triangles=6524740, target_triangles=TARGETS[0])
def stage(name):
    record['stage'] = name
    write_receipt('reduction_receipt.json', record)
    u.log('M25_OPTIMIZATION ' + name)

try:
    production_context()
    work = owned(DEST + '/' + WORK_NAME)
    if work is None:
        stage('duplicating_original_mesh')
        original = load(BASE + '/SK_M25_VortexCoffer')
        work = TOOLS.duplicate_asset(WORK_NAME, DEST, original)
        if work is None:
            raise RuntimeError('Duplicate failed')
        LIB.set_metadata_tag(work, 'M25.OptimizationRevision', REV)
        original = None
        u.SystemLibrary.collect_garbage()
    if LIB.get_metadata_tag(work, 'M25.BaseReductionComplete') != REV + '.ExplicitLODSetter':
        stage('preparing_reduction')
        settings = lod_settings('DA_M25_BaseReduction_V01', [TARGETS[0]])
        # UE Python hides BlueprintGetter/Setter functions as properties. Invoke the
        # reflected setter so it copies settings into LODInfo, beyond changing its pointer.
        work.call_method('SetLODSettings', (settings,))
        stage('reducing_6524740_to_350000')
        # Reloading a mesh with a changed LOD settings asset can already rebuild it.
        # Do not submit that completed base reduction to the builder a second time.
        built_triangles = int(u.AssetRegistryHelpers.create_asset_data(work).get_tag_value('Triangles'))
        if built_triangles > TARGETS[0]:
            if not EDITOR.regenerate_lod(work, 1, True, True):
                raise RuntimeError('Base LOD reduction failed')
        LIB.set_metadata_tag(work, 'M25.BaseReductionComplete', REV + '.ExplicitLODSetter')
        record['saved'].append(save(work))
    record.update(mesh=mesh_receipt(work),
                  original_retained=BASE + '/SK_M25_VortexCoffer', priority_bones=PRIORITY_BONES)
    stage('reduced_mesh_saved_export_pending')
except Exception:
    record['error'] = traceback.format_exc()
    stage('production_failed')
    raise
