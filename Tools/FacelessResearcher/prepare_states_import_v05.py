from pathlib import Path
TOOLS=Path(__file__).resolve().parent
for role in ['outfit','clothing']:
    code=(TOOLS/('import_stable_'+role+'_v04.py')).read_text(encoding='utf-8').replace('V04','V05')
    code=code.replace('V05 fixed garment cage, smooth sewn weights and temporal ease; not gameplay tested',
        'V05 accepted V04 base/curves plus fall, supine/prone get-up and dizzy garment shapes; not gameplay tested')
    (TOOLS/('import_states_'+role+'_v05.py')).write_text(code,encoding='utf-8')
print('M05 V05 mesh import batches prepared')
