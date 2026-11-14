"""Hand-compose linked use zones on source triangles, without changing base scenery."""
from pathlib import Path
import json,gzip,math
import numpy as np
ROOT=Path(__file__).resolve().parent
I=json.loads((ROOT/'inputs.json').read_text('utf8'))
A={a['name']:a for a in I['actors']}
M={}
for p,m in I['meshes'].items():
    n=p.rsplit('/',1)[-1].split('.')[0]
    if n not in M or p.startswith('/Game/UndergroundTunnel/'):M[n]=dict(m,path=p)
G={}
def rotation(yaw):
    c,s=math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def geometry(actor):
    if actor in G:return G[actor]
    c=A[actor]['components'][0];m=I['meshes'][c['mesh']]
    with gzip.open(ROOT/'Geometry'/m['geometry'],'rt',encoding='utf8') as f:g=json.load(f)
    if abs(c['rotation'][0])+abs(c['rotation'][1])>.01:raise RuntimeError('Support needs full orientation '+actor)
    v=np.array(g['vertices'])*c['scale'];v=v@rotation(c['rotation'][2]).T+c['position']
    G[actor]=v[np.array(g['indices']).reshape(-1,3)]
    return G[actor]
def hits(tris,point,axis=2):
    dims=[d for d in range(3) if d!=axis];a=tris[:,0];b=tris[:,1]-a;c=tris[:,2]-a
    i,j=dims;det=b[:,i]*c[:,j]-c[:,i]*b[:,j];valid=np.abs(det)>1e-7;det=np.where(valid,det,1.)
    u=((point[i]-a[:,i])*c[:,j]-c[:,i]*(point[j]-a[:,j]))/det
    v=(b[:,i]*(point[j]-a[:,j])-(point[i]-a[:,i])*b[:,j])/det
    return (a[:,axis]+u*b[:,axis]+v*c[:,axis])[valid&(u>=-.00001)&(v>=-.00001)&(u+v<=1.00001)]
supports={
 'station':np.concatenate([geometry('StaticMeshActor_92'),geometry('StaticMeshActor_93')]),
 'link':geometry('StaticMeshActor_86'),'bridge':geometry('StaticMeshActor_108'),
 'stairs':geometry('StaticMeshActor_110'),'pit':geometry('StaticMeshActor_94'),
 'desk':geometry('StaticMeshActor_70'),'rack':geometry('StaticMeshActor_126'),
 'cart':geometry('StaticMeshActor_130')}
# Warehouse support remains the approved original mesh at its unchanged transform.
whroot=ROOT.parent/'FreightWarehouseWeathering20261110/Geometry'
whinputs=json.loads((whroot.parent/'inputs.json').read_text('utf8'))
whmeshes={p.rsplit('/',1)[-1].split('.')[0]:m for p,m in whinputs['meshes'].items()}
wg=[]
for name in ('SM_CargoWarehouse_Floors','SM_CargoWarehouse_Paving'):
    with gzip.open(whroot/whmeshes[name]['geometry'],'rt',encoding='utf8') as f:g=json.load(f)
    wg.append(np.array(g['vertices'])[np.array(g['indices']).reshape(-1,3)]+[3760,-900,0])
supports['warehouse']=np.concatenate(wg)
def surface(kind,xy,wanted=0):
    h=hits(supports[kind],list(xy)+[wanted]);h=h[np.abs(h-wanted)<3]
    if not len(h):raise RuntimeError('No receiving surface '+str((kind,xy,wanted)))
    return float(max(h))
PLAN={'map':I['map'],'tag':'FreightStation.UnifiedPatina20261111','reference':'Derelict Corridor layered decay; existing original materials retained',
      'parts':[],'decals':[],'preserve':['all existing actors and transforms','all original material bindings','all lights','doors, containers, spawns and gameplay'],
      'placement_units':'UE centimetres, world coordinates','tests_run':False,'rendered':False}
OR=np.array([7760.,-1400.,0.])
def station(x,y):return [x+7760,y-1400]
def part(key,name,xy,yaw=0,scale=1.,group='Station',support='station',wanted=0,blocking=False):
    m=M[name];s=np.array([scale]*3);r=rotation(yaw);mid=(np.array(m['min'])+m['max'])/2
    ex=(np.abs(r)@((np.array(m['max'])-m['min'])*s/2))[:2]
    q=np.array([*xy,0.])-r@(mid*s*[1,1,0])
    z=max(surface(support,[xy[0]+dx,xy[1]+dy],wanted) for dx,dy in ((0,0),(-ex[0],-ex[1]),(-ex[0],ex[1]),(ex[0],-ex[1]),(ex[0],ex[1])))
    q[2]=z-m['min'][2]*scale+.04
    # All solid additions are deliberately peripheral, outside the authored routes.
    if blocking:
        for a in I['actors']:
            if 'Door' not in a['class'] and 'Container' not in a['class'] and 'Treasure' not in a['class']:continue
            if all(abs(xy[j]-a['center'][j])<ex[j]+a['extent'][j]+90 for j in (0,1)):
                raise RuntimeError('Interactive approach reserved '+key)
    PLAN['parts'].append({'id':key,'mesh':m['path'],'group':group,'position':q.tolist(),'rotation':[0,yaw,0],'scale':s.tolist(),
                          'support':support,'support_z':z,'collision':'NoCollision',
                          'shadow':not ('/Decals/' in m['path']),'draw_distance':5200 if blocking else 4000})
def patch(key,material,xy,size,angle=0,group='Station',support='station',wanted=0):
    z=surface(support,xy,wanted)
    PLAN['decals'].append({'id':key,'material':material,'group':group,'position':list(xy)+[z+.16],
        'rotation':[-90,angle,0],'size':[.8 if support in ('desk','rack','cart','stairs','bridge') else 2.5,size[1]/2,size[0]/2],
        'receiver':support,'support_z':z})
def wall(key,material,point,width,height,actor,axis,inside,group='WallFoot',roll=0,depth=1.5):
    # Trace towards the receiving face from the room; tile relief is sampled where present.
    t=geometry(actor);h=hits(t,point,axis);h=h[np.abs(h-point[axis])<45]
    if not len(h):raise RuntimeError('No receiving wall '+key)
    coord=float(max(h) if inside>0 else min(h));p=list(point);p[axis]=coord+inside*.18
    yaw=(180 if inside>0 else 0) if axis==0 else (-90 if inside>0 else 90)
    PLAN['decals'].append({'id':key,'material':material,'group':group,'position':p,'rotation':[0,yaw,roll],
                          'size':[depth,width/2,height/2],'receiver':actor,'contact_plane':coord})

# The same dust and handling wear continue through the warehouse's east vestibule.
for key,xy,size,angle in [('WHExitDustSouth',[5304,-1528],[180,40],-4),('WHExitDustNorth',[5390,-1274],[115,35],6)]:
    patch(key,'DustEdge',xy,size,angle,'WarehouseExit','warehouse')
patch('WHExitHandling','Scuff',[5196,-1505],[155,26],-5,'WarehouseExit','warehouse')
part('WHExitPackingSlip','SM_IncidentDetail_Paper0',[5308,-1515],-23,.9,'WarehouseExit','warehouse')
part('WHExitCardboard','SM_Decal_Junk07a',[5416,-1282],31,.85,'WarehouseExit','warehouse')

# Keep a broad clear centre in the narrow 4 m link. No solid prop is added here.
for key,xy,size,angle in [('LinkSouth',[5568,-1540],[154,28],2),('LinkNorth',[5731,-1261],[190,25],-3)]:
    patch(key,'DustEdge',xy,size,angle,'ConnectingPassage','link')
patch('LinkEdgeRub','Scuff',[5665,-1521],[113,18],-7,'ConnectingPassage','link')
part('LinkPaper','SM_IncidentDetail_Paper2',[5608,-1529],26,.8,'ConnectingPassage','link')
part('LinkSmallPacking','SM_Decal_Junk07a',[5798,-1272],-37,.8,'ConnectingPassage','link')
wall('LinkTileFoot','DustWall',[5700,-1246,42],183,52,'StaticMeshActor_89',1,-1,'ConnectingPassage',depth=3)
wall('LinkShortLeak','LeakSoft',[5760,-1238,222],49,100,'StaticMeshActor_88',1,-1,'ConnectingPassage')

# Vestibule marks widen gradually towards the concourse, leaving the centre plain.
patch('VestibuleSouth','DustEdge',[5965,-1582],[158,62],-6,'StationEntrance')
patch('VestibuleNorth','DustEdge',[6070,-1207],[145,42],4,'StationEntrance')
part('VestibuleForm','SM_IncidentDetail_Paper3',[6104,-1227],68,.85,'StationEntrance')
wall('VestibuleUpperSeep','LeakSoft',[6018,-1170,231],65,144,'StaticMeshActor_97',1,-1,'StationEntrance')
wall('VestibuleTileFoot','DustWall',[5960,-1630,51],141,62,'StaticMeshActor_98',1,1,'StationEntrance',depth=3)

# Two local deterioration sources, each with restrained fragments at its own wall foot.
wall('ConcourseWestSpall','Damage',[6174,-760,213],83,90,'StaticMeshActor_97',0,1,'ConcourseWall')
wall('ConcourseWestLowDust','DustWall',[6174,-763,58],172,76,'StaticMeshActor_98',0,1,'ConcourseWall',depth=3)
patch('ConcourseWestFoot','DustEdge',[6220,-762],[64,236],-3,'ConcourseWall')
for i,(xy,yaw,s) in enumerate([([6210,-748],23,1.05),([6240,-786],-37,.8),([6209,-825],71,.65)]):
    part('ConcourseFragment'+str(i),'SM_ConcreteRubble',xy,yaw,s,'ConcourseWall')
part('ConcourseBlownPaper','SM_IncidentDetail_Paper1',[6252,-665],-26,.8,'ConcourseWall')
wall('PowerWallSeep','Leak',[7040,-3036,393],113,360,'StaticMeshActor_97',1,1,'PowerService')
wall('PowerWallOldDamp','DampWall',[7005,-3036,188],171,78,'StaticMeshActor_97',1,1,'PowerService')
patch('PowerCabinetSettledDust','DustEdge',[6456,-2916],[185,81],3,'PowerService')
patch('PowerServiceToe','DustEdge',[7041,-2988],[231,69],-5,'PowerService')
part('PowerOldJoint','SM_RustyPipeJoint',[7029,-3004],17,.9,'PowerService')
part('PowerOldJointSmall','SM_RustyPipeJoint',[7061,-2977],-48,.7,'PowerService')
part('PowerPacking','SM_Decal_Junk02a',[6990,-2971],-17,.7,'PowerService')

# Maintenance remnant at the opposite platform wall, ahead of the existing stairs.
repair=station(1025,-1510)
part('PlatformToolbox','Sm_Toolbox01a',repair,82,1.,'PlatformMaintenance',blocking=True)
part('PlatformEmptyCan','SM_Paintcan01a',station(1080,-1548),-14,.85,'PlatformMaintenance')
part('PlatformSpareJoint','SM_RustyPipeJoint',station(1053,-1461),34,1.,'PlatformMaintenance')
part('PlatformPackingSlat','SM_WoodBoard01h',station(1113,-1499),83,.65,'PlatformMaintenance')
part('PlatformCardboard','SM_Decal_Junk01a',station(994,-1447),-21,.8,'PlatformMaintenance')
patch('PlatformMaintenanceDust','DustEdge',station(1055,-1519),[266,160],-4,'PlatformMaintenance')
patch('PlatformMaintenanceResidue','Oil',station(1055,-1475),[68,43],21,'PlatformMaintenance')
wall('PlatformMaintenanceTileWear','ScuffWall',[8807,-3036,83],135,51,'StaticMeshActor_98',1,1,'PlatformMaintenance',depth=3)
wall('PlatformMaintenanceLeak','LeakSoft',[8852,-3036,360],78,251,'StaticMeshActor_97',1,1,'PlatformMaintenance')

# Workroom dirt follows actual furniture; leave all searchable containers and door arcs alone.
patch('WorkshopWindowFoot','DustEdge',[7826,-584],[331,37],1,'WorkshopExterior')
wall('WorkshopWindowBaseDust','DustWall',[7830,-557,34],321,43,'StaticMeshActor_55',1,-1,'WorkshopExterior')
wall('WorkshopLowerRub','ScuffWall',[7917,-557,70],83,24,'StaticMeshActor_55',1,-1,'WorkshopExterior')
part('WorkshopExteriorPaper','SM_IncidentDetail_Paper0',[7825,-608],-34,.95,'WorkshopExterior')
part('WorkshopExteriorPaperFold','SM_IncidentDetail_Paper3',[7950,-594],51,.85,'WorkshopExterior')
patch('WorkshopCartResidue','Oil',[8419,-303],[112,74],-9,'WorkshopExterior')
patch('WorkshopCartDust','DustEdge',[8430,-314],[182,119],4,'WorkshopExterior')
for suffix,xy in [('Left',[8387,-405]),('Right',[8469,-405])]:patch('WorkshopCartWheel'+suffix,'Scuff',xy,[18,129],0,'WorkshopExterior')
part('WorkshopCartJoint','SM_RustyPipeJoint',[8507,-312],46,.85,'WorkshopExterior')
part('WorkshopCartPacking','SM_Decal_Junk04a',[8502,-372],-26,.9,'WorkshopExterior')
part('WorkshopCartForm','SM_IncidentDetail_Paper2',[8493,-423],17,.85,'WorkshopExterior')
part('WorkshopUnderDeskPaper','SM_IncidentDetail_Paper0',[7925,-509],14,.85,'WorkshopInterior')
part('WorkshopDiscardedForm','SM_IncidentDetail_Paper3',[8044,-393],-32,.9,'WorkshopInterior')
part('WorkshopUnderRackCan','SM_Paintcan01a',[8139,97],16,.85,'WorkshopInterior')
part('WorkshopBackEmptyBucket','SM_Bucket01b',[8267,98],-9,.9,'WorkshopInterior',blocking=True)
patch('WorkshopDeskFloorDust','DustEdge',[7922,-502],[178,29],0,'WorkshopInterior')
patch('WorkshopMotorResidue','Oil',[7776,-2],[103,70],15,'WorkshopInterior')
patch('WorkshopRackFoot','DustEdge',[8073,121],[177,34],-1,'WorkshopInterior')
patch('WorkshopBucketFoot','DustEdge',[8257,95],[71,82],-12,'WorkshopInterior')
patch('WorkshopDeskRearDust','DustFine',[7873,-509],[64,13],0,'WorkshopInterior','desk',77.5)
patch('WorkshopDeskFrontWear','Scuff',[8006,-448],[22,13],-8,'WorkshopInterior','desk',77.5)
patch('WorkshopRackUpperDust','DustFine',[8168,94],[12,44],0,'WorkshopInterior','rack',181.5)
patch('WorkshopRackMiddleDust','DustFine',[8072,120],[113,11],0,'WorkshopInterior','rack',131.5)
wall('WorkshopBackLowDirt','DustWall',[8266,143,55],65,72,'StaticMeshActor_55',1,-1,'WorkshopInterior')

# Non-uniform peripheral dust breaks the long platform surfaces, away from the yellow coping.
for key,xy,size,ang in [('NorthMid',station(45,-1540),[280,88],-8),('SouthBeforeStair',station(1062,1512),[214,104],11),
                      ('NorthFar',station(2880,-1503),[214,127],-12),('SouthFar',station(2910,1509),[239,110],8)]:
    patch('PlatformDust'+key,'DustEdge',xy,size,ang,'PlatformEdges')
part('PlatformSouthPacking','SM_Decal_Junk05a',station(1113,1530),41,.82,'PlatformEdges')
part('PlatformSouthForm','SM_IncidentDetail_Paper2',station(1035,1497),-31,.9,'PlatformEdges')
part('PlatformFarPaper','SM_IncidentDetail_Paper1',station(2890,-1510),19,.85,'PlatformEdges')
part('PlatformFarFragmentA','SM_ConcreteRubble',station(2958,1586),-18,1.2,'PlatformEdges')
part('PlatformFarFragmentB','SM_ConcreteRubble',station(2919,1566),61,.75,'PlatformEdges')
wall('PlatformFarSpall','Damage',[10678,236,200],81,77,'StaticMeshActor_97',1,-1,'PlatformEdges')
wall('PlatformFarSouthDust','DustWall',[10670,236,54],207,72,'StaticMeshActor_98',1,-1,'PlatformEdges',depth=3)
wall('PlatformNorthFarLeak','LeakSoft',[10601,-3036,401],136,324,'StaticMeshActor_97',1,1,'PlatformEdges')

# Raised routes get only shallow deposits along their perimeter. No clutter on treads.
for i,(x,y,sx,sy) in enumerate([(2260,-745,35,201),(2264,775,43,239),(2728,-1055,31,205),(2733,945,34,173)]):
    patch('BridgeEdgeDust'+str(i),'DustFine',station(x,y),[sx,sy],0,'RaisedRoute','bridge',480)
for i,(x,y,step) in enumerate([(1400,-1555,3),(1700,-1557,13),(2180,-1553,29),(1490,1556,6),(1940,1554,21)]):
    patch('StairEdgeDust'+str(i),'DustFine',station(x,y),[18,56],0,'RaisedRoute','stairs',step*16)

# Recessed track bed: tiny windblown scraps beside the wall, outside rails and recovery stairs.
for i,(x,y) in enumerate([(740,-478),(1940,474)]):
    patch('TrackFootDirt'+str(i),'Damp',station(x,y),[201,46],(-1 if i else 1)*7,'TrackBed','pit',-180)
    part('TrackBlownPaper'+str(i),'SM_IncidentDetail_Paper'+str(i+1),station(x+41,y),43-i*71,.85,'TrackBed','pit',-180)

(ROOT/'Config').mkdir(exist_ok=True)
(ROOT/'Config/layout.json').write_text(json.dumps(PLAN,ensure_ascii=False,indent=2),encoding='utf8')
print('FREIGHT_STATION_LAYOUT_AUTHORED',len(PLAN['parts']),len(PLAN['decals']))
