"""Publish the final support-base revision and formal map in the same background batch."""
from pathlib import Path
import unreal as u,runpy
R=Path(__file__).resolve().parent
u.EditorLoadingAndSavingUtils.new_blank_map(False)
r=runpy.run_path(str(R/'build_assets.py'))
riverfront=r['D'].get('revision')=='riverfront_gaps_20261026'
for i,row in enumerate(r['G']['meshes']):
    if row['kind']=='ground' or row['key'] in ('Bench','Planter','Shelter','Terraces','Lookout','Fountain_Water'):r['meshes'](i,i+1)
for zone in (('P1','P2','P3','P4','P5','P6') if riverfront else ('P4',)):r['assembly'](zone)
r['finish']()
runpy.run_path(str(R/'publish.py'),run_name='__main__')
