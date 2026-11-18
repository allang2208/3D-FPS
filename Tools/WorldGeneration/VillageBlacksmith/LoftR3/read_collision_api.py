"""Read the current engine's collision struct interface after a production import error."""
import unreal as u
b=u.KBoxElem()
u.log('KBOX_API '+str([n for n in dir(b) if not n.startswith('_')]))
for key,value in [('center',u.Vector()),('x',10.),('y',10.),('z',10.),('rotation',u.Rotator())]:
    try:b.set_editor_property(key,value);u.log('KBOX_SET '+key+' OK')
    except Exception as e:u.log('KBOX_SET '+key+' '+str(e))
m=u.load_asset('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakTable')
u.log('TABLE_STATE '+str(bool(m)))
