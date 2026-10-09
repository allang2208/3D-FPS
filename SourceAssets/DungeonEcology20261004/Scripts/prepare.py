"""Current ecology author entry. Retain the original signage, then apply user layout revision."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parents[1]
if not (ROOT/'Authored/atlas.json').exists() or not (ROOT/'Authored/T_Eco_Labels_BaseColor.png').exists():
    original=(ROOT/'Revisions/v2/Scripts/prepare.py').read_text('utf8')
    exec(compile(original,'ecology_original_signage','exec'),dict(__file__=__file__,__name__='__main__'))
sys.path.insert(0,str(ROOT/'Scripts'))
runpy.run_path(str(ROOT/'Scripts/prepare_v7.py'),run_name='__main__')
