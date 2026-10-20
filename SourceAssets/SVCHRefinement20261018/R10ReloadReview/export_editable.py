"""Reuse the R9 source exporter for the reviewed R10 profile, retaining both sources."""
from pathlib import Path
import hashlib,json
O = Path(__file__).parent
source = O.parent / 'R9ReloadGrip/export_editable.py'
code = source.read_text().replace("I = O / 'Inputs'", "I = O.parent / 'R9ReloadGrip/Inputs'")
code = code.replace('profile_reload_grip.json', 'profile_native_registration.json')
code = code.replace('SVCH_R9_', 'SVCH_R10_')
exec(compile(code, str(source), 'exec'), {'__file__': __file__})
receipt=O/'editable_source.json'
report=json.loads(receipt.read_text())
report['profile_source_sha256']=hashlib.sha256((O/'profile_native_registration.json').read_bytes()).hexdigest()
receipt.write_text(json.dumps(report,indent=2))
