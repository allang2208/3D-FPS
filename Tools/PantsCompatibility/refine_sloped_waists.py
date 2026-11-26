"""Finish the two low/sloped waist authoring inputs; no pose tests or rendering."""
import hashlib,runpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from pants_compatibility_paths import *
manifest=read(R/'authored.json')
for signature,group in manifest['groups'].items():
    if group['waist_top_cm']>=98.5:continue
    out=R/'Fits'/signature
    runpy.run_path(str(P/'Tools/RangerCrouchFit/author_tucked.py'),init_globals=dict(OUTPUT_ROOT=str(out),PANTS_FILE=group['guide'],PANTS_ITEM=','.join(group['items']),WAIST_TOP=group['waist_top_cm']),run_name='__main__')
    for row in manifest['records']:
        if row['signature']==signature:row['author_sha256']=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
write(R/'authored.json',manifest)
runpy.run_path(str(P/'Tools/PantsCompatibility/author_default.py'),run_name='__main__')
