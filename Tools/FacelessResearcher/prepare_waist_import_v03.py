"""Prepare separate mesh import batches for researcher circumferential tailoring."""
from pathlib import Path
TOOLS=Path(__file__).resolve().parent
for role in ['outfit','clothing']:
    script=(TOOLS/('import_mesh_'+role+'.py')).read_text(encoding='utf-8').replace('V01','V03')
    script=script.replace('Background import into an independent security namespace; no game/preview tests.',
        'Import researcher circumferential waist tailoring; no game/preview tests.')
    script=script.replace('Saved V03 candidate; not rendered or gameplay tested',
        'V03 smooth circumferential waist transition and clothed clearance in idle/walk/attack/hit; not gameplay tested')
    (TOOLS/('import_waist_'+role+'_v03.py')).write_text(script,encoding='utf-8')
print('Researcher V03 import batches written')
