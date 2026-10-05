"""UE 5.8 skeletal FBX export needs an RHI even with material baking disabled.
Run with -AllowCommandletRendering -RenderOffscreen, without -nullrhi.
This performs source export only, without gameplay, screenshots or acceptance rendering.
"""
from pathlib import Path
import sys, traceback
sys.path.insert(0, str(Path(__file__).resolve().parent))
from author_common import *

record = dict(revision=REV, stage='exporting', runtime_tested=False, rendered=False)
try:
    production_context()
    mesh = owned(DEST + '/' + WORK_NAME)
    if mesh is None or LIB.get_metadata_tag(mesh, 'M25.BaseReductionComplete') != REV + '.ExplicitLODSetter':
        raise RuntimeError('Base reduction must complete before game FBX export')
    export_fbx(mesh, FBX)
    record.update(stage='reduced_game_source_saved', mesh=mesh_receipt(mesh), fbx=str(FBX), fbx_bytes=FBX.stat().st_size)
    write_receipt('export_receipt.json', record)
    reduction_record = json.loads((ROOT / 'reduction_receipt.json').read_text(encoding='utf-8'))
    reduction_record.update(stage='reduced_mesh_saved', mesh=record['mesh'], export_receipt=str(ROOT / 'export_receipt.json'),
                            export_route='Separate offscreen RHI commandlet; initial combined NullRHI FBX export was interrupted after mesh save')
    write_receipt('reduction_receipt.json', reduction_record)
    u.log('M25_OPTIMIZATION reduced_game_source_saved')
except Exception:
    record.update(stage='production_failed', error=traceback.format_exc())
    write_receipt('export_receipt.json', record)
    raise
