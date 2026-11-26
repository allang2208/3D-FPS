"""Native sleeve production now uses the fixed-wrist workflow."""
import sys,shutil,runpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_fp import build as native_build
from combat3_cuff_solver import R,C,read,write
from combat3_cuff_tailor import tailor
def build(rig):
    if rig=='Body':
        runpy.run_path(str(Path(__file__).with_name('combat3_cuff_body.py')),run_name='__main__')
        row=read(C/'fp-batch-Body.json')['rows'][0]
    else:row=native_build(rig)
    tailor(rig)
    target=R/'Authored'/Path(row['file']).name;shutil.copy2(row['file'],target);row['file']=str(target);return row
if __name__=='__main__':
    rows=[]
    for item in read(R.parent/'CombatShirtR2/fp-authored.json')['rows']:
        rows.append(build(item['rig']));write(R/'fp-authored.json',dict(completed=False,rows=rows,cuff_revision='CuffRepairR1'))
    write(R/'fp-authored.json',dict(completed=True,rows=rows,cuff_revision='CuffRepairR1'))
