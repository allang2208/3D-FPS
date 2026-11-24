"""Unwrapped shelter grime field and per-corner contact masks for timber and iron."""
import math
from yard_sites import WEST, HALF, wall

def clamp(v):
    return max(0.,min(1.,v))

def apply(objects):
    for ob in objects:
        data=ob.data
        # Channel 1 is reserved for the FBX importer's lightmap unwrap.
        data.uv_layers.new(name='Lightmap',do_init=True)
        layer=data.uv_layers.new(name='WorkWear',do_init=False)
        name=ob.name
        for face in data.polygons:
            slot=ob.material_slots[face.material_index].name
            for index in face.loop_indices:
                v=data.vertices[data.loops[index].vertex_index].co
                xyz=ob.matrix_world@v
                x,y,z=xyz.x,-xyz.y,xyz.z
                if slot=='Canvas':
                    # Legacy FBX import flips V at the Unreal texture origin.
                    mask=((x-WEST)/(wall(y)+.12-WEST),(HALF-y)/(2*HALF))
                else:
                    foot=clamp(1.-z/.51)
                    dirty=.12+.70*foot
                    rub=.10
                    if 'Cart grip' in name:
                        rub=.67+.27*math.cos(7*v.z)
                        dirty=.29
                    elif 'Cart wheel' in name or 'spoke' in name:
                        rub=.64 if slot=='Iron' and abs(face.normal.z)>.45 else .29
                        dirty=.19+.68*foot
                    elif 'Cart bed' in name or 'Shallow bed' in name or 'Splintered' in name:
                        rub=.30+.54*abs(face.normal.z)
                        dirty=.32+.29*clamp(-v.z*7.)
                    elif 'pin' in name.lower() or 'rivet' in name.lower():
                        rub=.56
                        dirty=.49
                    elif 'repair' in name.lower() or 'ferrule' in name:
                        rub=.35
                        dirty=.47
                    elif 'hub' in name.lower() or 'Axle' in name:
                        dirty=.86
                    elif 'ash' in name.lower() or 'rake' in name.lower():
                        dirty=.69
                    elif 'upright' in name or 'rafter' in name or 'Wall ledger' in name:
                        dirty+=.52*math.exp(-((x-7.)/1.65)**2)*(z>2.6)
                    mask=(rub,1.-clamp(dirty))
                layer.data[index].uv=mask
        data.uv_layers.active_index=0
