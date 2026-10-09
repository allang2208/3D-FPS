"""Authoring adapter: decorate the three selected route IDs; never draw random themes.
This module returns scoped catalog parts for accepted future Junction integration.
The production generator is deliberately not modified while the room is a subject.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
def compose(selected_route_themes):
 cfg=json.loads((ROOT/'Config/layout.json').read_text('utf8'));manifest=json.loads((ROOT/'manifest.json').read_text('utf8'));parts=[]
 available={t['id'] for t in cfg['themes']}
 for gate in cfg['gates']:
  route=gate['route'];theme=selected_route_themes[route]
  if theme not in available:raise ValueError('No authored portal for '+theme)
  p=gate['position_m']
  for m in manifest['meshes']:
   if m['room']!=theme or m['preview_only']:continue
   parts.append(dict(mesh=m['mesh'],position=[p[0]*100,-p[1]*100,p[2]*100],yaw=-gate['yaw_deg'],scale=[1,1,1],collision=m['collision'],cast_shadow=m['cast_shadow'],route=route,theme=theme))
 return parts
