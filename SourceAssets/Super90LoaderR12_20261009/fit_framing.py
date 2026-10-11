"""Shouldered camera-space pose fit to the recorded empty reload reference."""
from pathlib import Path
O=Path(__file__).parent
g={'__file__':str(O/'r12_core.py')}
for part in ('r12_core.py','skin_arm.py','r12_motion.py'):
    exec(compile((O/part).read_text(),str(O/part),'exec'),g)
globals().update({k:v for k,v in g.items() if not k.startswith('__')})
mouth=BIND_TO_IDLE@MOUTH
muzzle=idle['WPN_FrontSight'].translation
def uv(p):
    x,y,z=screen(p); return ((x+1)/2,(1-y)/2)
def cost(pitch,yaw):
    lay=dict(LAYOUT,pitch=pitch,yaw=yaw)
    mv=gun_move(100,7,True,lay)
    a,b=uv(mv@mouth),uv(mv@muzzle)
    return sum((x-y)**2 for x,y in zip(a,(.62,.67)))*2+sum((x-y)**2 for x,y in zip(b,(.55,.43)))
best=min((cost(p,y),p,y) for p in range(0,36) for y in range(-40,31))
print('FIT',best,flush=True)
for p,y in [(26,0),best[1:]]:
    mv=gun_move(100,7,True,dict(LAYOUT,pitch=p,yaw=y))
    print('FRAMING',p,y,'mouth',uv(mv@mouth),'muzzle',uv(mv@muzzle),'buttcam',tuple(cam(BUTT)),flush=True)
