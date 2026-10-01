"""Regenerate only the floor cut, pit walls/floor and combined stairs after expansion."""
import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
ns=runpy.run_path(str(HALL/'Scripts/author_hall.py'),init_globals={'SKIP_HALL_EXPORT':True},run_name='ash_architecture')
ns['G']={key:ns['G'][key] for key in ('Floors','AshPit','Stairs')}
ns['OUT']=ROOT/'Authored/Architecture';ns['EXPORT_SUFFIX']='_AshV3';ns['EXPORT_BLEND_NAME']='ExpandedAshPit_Architecture.blend'
ns['CFG']=dict(ns['CFG'],revision='ash_station_expansion_v3_20260930')
script=HALL/'Scripts/export_geometry.py'
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
