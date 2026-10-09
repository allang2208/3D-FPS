"""Produce short per-mesh import batches using the established material binding."""
from pathlib import Path
TOOLS=Path(__file__).resolve().parent
for role in ['outfit','clothing']:
    script=(TOOLS/('import_mesh_'+role+'.py')).read_text(encoding='utf-8').replace('V01','V02')
    script=script.replace('Background import into an independent security namespace; no game/preview tests.',
        'Import researcher reaction tailoring; no game/preview tests.')
    script=script.replace('Saved V02 candidate; not rendered or gameplay tested',
        'V02 preserves V01 shapes and adds clothed-leg clearance throughout hit reaction; not gameplay tested')
    (TOOLS/('import_reaction_'+role+'_v02.py')).write_text(script,encoding='utf-8')
print('Researcher V02 mesh import batches written')
