"""Retain the selected UC source and current M870 authoring inputs locally."""
import hashlib,json,shutil,subprocess
from pathlib import Path
O=Path(__file__).parent
repo=Path(r'C:\Users\allan\AppData\Local\Temp\m870-workfiles-research-708e69dc')
source=repo/'Urban1 Decay/[MAIN]/870'
if not (source/'anims/reloadinsert.smd').is_file():
    raise RuntimeError('Selected source checkout is not ready')
shutil.copytree(source,O/'Original/870',dirs_exist_ok=True)
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
files={str(p.relative_to(O)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (O/'Original').rglob('*') if p.is_file()}
(O/'acquisition.json').write_text(json.dumps(dict(repository='https://github.com/Urban-Coalition/UC_Workfiles',commit=commit,source_directory='Urban1 Decay/[MAIN]/870',files=files,license='No explicit independent-game redistribution license found; local working copy only',publication_authorized=False),indent=2))
print('M870_UC_SOURCE_RETAINED',len(files),commit)
