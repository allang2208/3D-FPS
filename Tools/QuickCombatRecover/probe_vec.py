import unreal
v=unreal.Vector(3,4,0)
print("type",type(v))
print([m for m in dir(v) if 'norm' in m.lower() or 'safe' in m.lower() or m in ('cross','dot','length','size')])
