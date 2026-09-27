"""Shared authoring source for visible fixtures and runtime lights (Blender metres)."""
import json,math
from pathlib import Path

def specs():
    return json.loads((Path(__file__).resolve().parents[1]/'Config/lighting.json').read_text(encoding='utf-8'))['lamps']

def build(H):
    lamps=specs()
    for spec in lamps:
        x,y,z=spec['at']
        group=H['GROUPS'].get('Fixtures')
        first=len(group['v']) if group else 0
        H['lamp'](spec)
        if spec['yaw']:
            angle=math.radians(spec['yaw']);c,s=math.cos(angle),math.sin(angle)
            vertices=H['GROUPS']['Fixtures']['v']
            for i in range(first,len(vertices)):
                vx,vy,vz=vertices[i];dx,dy=vx-x,vy-y
                vertices[i]=(x+c*dx-s*dy,y+s*dx+c*dy,vz)
        mount=[x,y,z+.035]
        axis=0 if spec['wall_axis']=='x' else 1
        mount[axis]=spec['wall_at']
        # The upper entry is immediately below the shaft ceiling. Keep its arm
        # and plate below 3.0 m; no cross-shaft supports above the player's head.
        H['tube']('Fixtures',[mount,(x,y,z+.035)],.018,'BossStructuralSteel',16)
        plate=[.14,.14,.09];plate[axis]=.022
        H['box']('Fixtures',mount,plate,'BossStructuralSteel')
    return lamps

def light_records():
    return [dict(id=l['id'],position=[round(l['at'][0]*100,4),round(-l['at'][1]*100,4),round((l['at'][2]-.085)*100,4)],
                 intensity=l['lumens'],radius=l['radius_cm'],color=[1,.64,.36] if l['warm'] else [.73,.84,1],
                 role='key',cast_shadows=True,max_draw_distance_cm=2400,fade_range_cm=500)
            for l in specs()]
