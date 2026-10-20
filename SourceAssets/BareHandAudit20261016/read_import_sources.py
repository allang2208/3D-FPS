"""Read the import source file of every repaired mesh (no save)."""
import json
from pathlib import Path
import unreal as u
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareHandAudit20261016')
paths = [json.loads(f.read_text())['path'] for f in (R / 'Installed').glob('*.json') if not f.name.endswith('.failed.json')]
paths += ['/Game/Weapons/Super90/JointSurface20261012/Candidates/SK_Super90JointCandidate_arms.SK_Super90JointCandidate_arms',
          '/Game/Weapons/Super90/JointSurface20261012/Candidates/SK_Super90JointCandidate_full.SK_Super90JointCandidate_full']
rows = []
for i, p in enumerate(paths):
    a = u.load_asset(p)
    imp = a.get_editor_property('asset_import_data') if a else None
    files = []
    if imp:
        try: files = [str(x) for x in imp.extract_filenames()]
        except Exception: files = [imp.get_first_filename()]
    rows.append(dict(path=p, sources=files))
    a = None
    if i % 8 == 7: u.SystemLibrary.collect_garbage()
(R / 'import_sources.json').write_text(json.dumps(rows, indent=1))
print('BARE_V8_IMPORT_SOURCES', len(rows), flush=True)
