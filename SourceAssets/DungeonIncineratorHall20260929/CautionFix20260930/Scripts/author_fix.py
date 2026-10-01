"""Re-export only the ash sign assembly after relocating its caution board."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
sys.path.insert(0,str(HALL/'AshStation20260930/Scripts'))
import author_station as station
fx=station.fx;g=station.g
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
atlas=json.loads((station.ROOT/'Authored/sign_atlas.json').read_text(encoding='utf-8'))
def tex(surface,u,v):
    x0,y0,x1,y1=atlas['rects'].get(surface,[2,834,18,850])
    return ((x0+u*(x1-x0))/2048,1-(y0+v*(y1-y0))/2048)
g.tex=tex;g.MATERIAL=station.BASE+'/Materials/M_AshStation_Signage'
fx.ROOT=ROOT;fx.BASE='/Game/Dungeons/IncineratorHall20260929/CautionFixV4'
record=fx.export('AshSigns',station.signs,[],station.sign_material(),'_V4')
record['collision_policy']='none'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'AshSigns_CautionClearanceV4.blend'))
(OUT/'manifest.json').write_text(json.dumps({'objects':[record],'caution_position_m':station.CFG['caution_sign_position_m'],
    'previous_caution_position_m':[-9.31,-2.525,.75],'tests_run':False,'rendered':False},indent=2),encoding='utf-8')
print('CAUTION_SIGN_V4_AUTHORED',flush=True)
