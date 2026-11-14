"""Recompose decorative use-zones while retaining the accepted entrance and original room."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parent/'FreightWarehouseEntranceSample20261111'
# Reuse the existing surface-contact authoring functions without rebuilding its sample.
scope={'__file__':str(PRIOR/'author_layout.py')}
exec(compile((PRIOR/'author_layout.py').read_text('utf8').split('# Packing remnant:')[0],'warehouse_contact_authoring','exec'),scope)
fresh=json.loads((ROOT/'inputs.json').read_text('utf8'))
for p,r in fresh['extra_meshes'].items():scope['meshes'][p.split('/')[-1].split('.')[0]]=dict(r,path=p)
scope['floor']=scope['np'].concatenate([scope['floor'],scope['geometry']('SM_CargoWarehouse_Dock')])
P={'map':'/Game/GameMaps/Design/L_FreightTransit_Theme_Subject','tag':'FreightWarehouse.DerelictPass20261111',
   'origin':[3760,-900,0],'parts':[],'decals':[],'remove_labels':[],'preserve_entrance':True,
   'reference':'https://www.fab.com/listings/d825ff9c-77da-45a4-9619-c989e6dfdda6'}
scope['plan']=P;part=scope['part'];decal=scope['decal']
old=json.loads((ROOT.parent/'FreightWarehouseWeathering20261110/Config/layout.json').read_text('utf8'))
# Keep existing major cargo and handling tools. Replace the old unmotivated rubble
# around cargo and the electrical corner with packing/maintenance-specific remnants.
for r in old['parts']:
    if r['group'] in ('WestRackGap','ElectricalCorner') or (r['group'] in ('CargoWest','CargoEast','DockService') and ('/Decals/' in r['mesh'] or 'DebrisPile' in r['mesh'])):
        P['remove_labels'].append('WarehouseWeathering_'+r['id'])
part('Storage_ReturnCableReel','SM_WoodenCableReel',[-1360,0],-8,.95,group='Storage')
part('Maintenance_CableReel','SM_WoodenCableReel',[1242,1027],17,1.,group='Maintenance')
part('Storage_UpperBucket','SM_Bucket01b',[-1362,-187],13,.9,support='rack:346',group='Storage')
part('Storage_UpperToolbox','Sm_Toolbox01a',[-1309,-229],72,1.,support='rack:346',group='Storage')
part('Storage_UpperSlat','SM_WoodBoard01h',[-1337,-318],93,.8,support='rack:346',flat=True,group='Storage')
for key,xy,yaw,s in [('DockPipeA',[1333,-1138],-14,1.),('DockPipeB',[1360,-1173],62,.9),('ElectricalSpare',[1364,1035],11,1.2)]:
    part(key,'SM_RustyPipeJoint',xy,yaw,s,flat=True,group='Maintenance')
for i,(variant,xy,yaw,s) in enumerate([
    (2,[-948,285],24,1.),(6,[-978,352],-27,.82),(4,[-924,210],68,.85),
    (1,[941,146],-14,.9),(5,[1032,113],28,.78),(7,[981,230],-41,.95),
    (3,[-1325,-1294],17,.75),(6,[-1175,-1270],61,.8)]):
    part('PackingRemnant_'+str(i),'SM_Decal_Junk0'+str(variant)+'a',xy,yaw,s,flat=True,group='CargoRemnants')
for i,(xy,yaw) in enumerate([([-904,274],-34),([935,235],81),([-1133,-1195],-12)]):
    part('DiscardedDispatch_'+str(i),'SM_IncidentDetail_Paper'+str(i),xy,yaw,.9,flat=True,group='CargoRemnants')
for i,(xy,yaw,s) in enumerate([([-1459,-34],24,1.3),([-1441,21],-17,.85),([1452,636],33,1.1),([1430,671],-56,.75)]):
    part('ConcreteFragment_'+str(i),'SM_ConcreteRubble',xy,yaw,s,flat=True,group='WallFoot')
# Scattered fragments have a corresponding source patch immediately above them.
decal('WallWest_LocalSpall','Damage',[0,5,63],[90,98],face='west',angle=-5,depth=1.0,group='WallFoot')
decal('WallEast_LocalSpall','Damage',[0,658,80],[108,125],face='west',angle=9,depth=1.0,group='WallFoot')
P['decals'][-1]['position'][0]=3760+1485.65;P['decals'][-1]['rotation'][1]=0
# Rack dust sits on known deck tops, while floor wear follows only activity edges.
for i,(xy,z,wh) in enumerate([([-1384,-214],346,[34,210]),([-1330,-402],346,[115,48]),([1384,322],346,[32,170])]):
    decal('ShelfSettledDust_'+str(i),'Dust',xy+[z],wh,face='deck',angle=3-i*4,depth=.6,group='Storage')
for key,kind,xy,wh,angle in [
    ('CableReelFoot','Dust',[-1371,0],[140,150],-7),
    ('ElectricalFoot','Dust',[1270,1030],[200,130],11),
    ('CargoWestRemnant','Dust',[-958,284],[145,150],-14),
    ('CargoEastRemnant','Dust',[980,157],[140,190],17),
    ('DockBarrelResidue','Oil',[1327,-1190],[53,70],31),
    ('EntranceHandlingA','Scuff',[-630,1040],[35,148],-7),
    ('EntranceHandlingB','Scuff',[-590,1030],[30,160],-7),
    ('CargoWestHandling','Scuff',[-937,190],[45,180],6),
    ('CargoEastHandling','Scuff',[944,297],[43,145],-12)]:
    decal(key,kind,xy+[0],wh,angle=angle,depth=3.,group='UseTraces')
# Localised upper staining extends existing column sources instead of distributing
# identical tall cracks around every wall. Route geometry and lighting are untouched.
decal('DockWestUpperLeak','Leak',[-1160,0,480],[95,260],face='south',depth=1.2,group='WallFoot')
P['decals'][-1]['position'][1]=-900-1385.65;P['decals'][-1]['rotation'][1]=-90
(ROOT/'Config').mkdir(exist_ok=True)
(ROOT/'Config/layout.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf8')
print('DERELICT_LAYOUT_AUTHORED',len(P['parts']),len(P['decals']),len(P['remove_labels']))
