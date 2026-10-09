"""Resolve text plate locations from the current authoring recipe, without rebuilding the room."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent
sys.path.insert(0,str(SOURCE/'Scripts'))
import geometry as g
import refined_console
from architecture import architecture
from refined_core import build_core

atlas=json.loads((ROOT/'atlas-source.json').read_text())
cfg=json.loads((SOURCE/'Config/scene.json').read_text('utf8'))
cards=[]
def capture(c,w,h,key,normal=(0,-1,0),atlas=None,console=False):
 mesh={'StoragePrototype':'SM_Power_Accumulator','ConsolePrototype':'SM_Power_ControlConsole_Refined'}.get(g.ROOM,'SM_Power_'+g.ROOM+'_Signs')
 cards.append(dict(mesh=mesh,center=list(c),normal=list(normal),width=w,height=h,key=key,
     family='power',old_depth=.0052 if console else .0181,
     old_margin=.0036 if console else .00001,old_front=.00002,
     depth=.005 if console else .018))
g.plate=capture
refined_console._label=lambda g,atlas,c,normal,width,height,key,screws=True:capture(c,width,height,key,normal,atlas,True)
g.poly=lambda *a,**kw:None
g.hull=lambda *a,**kw:None
architecture(g,cfg,atlas)
g.ROOM='StoragePrototype';build_core(g,atlas=atlas,scale=1.65)
g.ROOM='ConsolePrototype';refined_console.build_console(g,atlas)
# Cabinet plaque locations from the preserved FacilityProp authoring recipe.
for side,x in enumerate((-.4,.4)):
 for z,w,h,key in [(1.716,.320,.083,'cabinet_left' if side==0 else 'cabinet_right'),
                   (1.205,.335,.054,'buttons'),(.811,.273,.113,'warning' if side else 'rating')]:
  cards.append(dict(mesh='SM_Facility_PowerCabinet',center=[x,-.302,z],normal=[0,-1,0],width=w,height=h,key=key,
    family='cabinet',old_depth=.0016,old_front=.0005,old_margin=.00001,depth=.0025))
cards.append(dict(mesh='SM_Facility_PowerCabinet',center=[.7925,-.003,1.27],normal=[1,0,0],width=.230,height=.079,key='service',
    family='cabinet',old_depth=.0016,old_front=.0005,old_margin=.00001,depth=.0025))
for c,w,h in [([.139,-.5517,1.875],.20,.022),([0,-.5467,2.078],.14,.044)]:
 cards.append(dict(mesh='SM_Archive_ServerRack_V1',center=c,normal=[0,-1,0],width=w,height=h,key='server_plate',
    family='server',old_depth=.0065,old_front=.0005,old_margin=.0046,depth=.005))
for i,c in enumerate(cards):c['id']=f"{c['mesh']}_{i:02d}_{c['key']}"
(ROOT/'cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_TEXT_LAYOUT_CAPTURED',len(cards))
