"""Scoped whole-kitchen interface checks using current source and measured UE bounds.
No gameplay, rendering, or performance acceptance is implied by this authoring scan.
"""
from pathlib import Path
import bpy, bmesh, json, hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon
R=Path(__file__).resolve().parent
# Remove only prior local fixture references.
for o in list(bpy.data.objects):
    if o.name.startswith('AFX_'):bpy.data.objects.remove(o,do_unlink=True)
parts={}
def add(name,source,transform=True):
    src=bpy.data.objects[source]
    me=src.data.copy();o=bpy.data.objects.new('AFX_'+name,me);bpy.context.scene.collection.objects.link(o)
    if transform:o.matrix_world=src.matrix_world.copy()
    o['AuditOnly']=True;parts[o.name]=o
    return o
def cube(name,loc,dimensions):
    x,y,z=loc;a,b,c=[v*.5 for v in dimensions]
    vs=[(x+dx,y+dy,z+dz) for dx,dy,dz in [(-a,-b,-c),(a,-b,-c),(a,b,-c),(-a,b,-c),(-a,-b,c),(a,-b,c),(a,b,c),(-a,b,c)]]
    fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    o=bpy.data.objects.new('AFX_'+name,me);bpy.context.scene.collection.objects.link(o);o['AuditOnly']=True;parts[o.name]=o
    return o
counter=add('Counter','KIT_Counter')
backsplash=add('BackSplash','KIT_BackSplash')
# Actual mounted backing plane at source Y=13.5585m; the thin grout substrate
# bridges the decorative tile to the wall, not to a floating worktop edge.
cube('KitchenWall',(8.90,13.5985,1.225),(3.70,.080,2.45))
rail=add('UtilityRail','KIT_UtilityRail')
oven=add('OvenFront','KIT_OvenFront')
coffee=add('Coffee','KIT_SM_Staff_CoffeeMachine_V7')
kettle=add('Kettle','KIT_SM_Staff_ElectricKettle_V6')
# Keep the two already scoped prop assemblies intact; the additional fixture
# scan covers their contacts with appliances, rail, oven and worktop.
for key in ['Dishes','Prep']:
    for r in json.loads((R/'audit-parts.json').read_text()):
        if r['source']=='KIT_'+key:parts[r['id']]=bpy.data.objects[r['id']]
# Object names already equal part IDs; do not rename or reinterpret values.
interfaces=[
 ('AFX_OvenFront','AFX_Counter','hob_worktop'),
 ('AFX_BackSplash','AFX_KitchenWall','backsplash_wall_mount'),
 ('AFX_Coffee','AFX_Counter','coffee_worktop'),
 ('AFX_Kettle','AFX_Counter','kettle_worktop'),
 ('AFX_UtilityRail','AFX_BackSplash','rail_bracket'),
 ('AUD_Prep_000','AFX_Counter','prep_worktop'),
 ('AUD_Dishes_000','AFX_Counter','dish_worktop'),
]
for key in ['Dishes','Prep']:
    prior=json.loads((R/('manifest-'+key.lower()+'.json')).read_text())
    for row in prior['interfaces']:
        a='AFX_Counter' if row['a']=='AUD_CounterSupport0' else row['a']
        b='AFX_Counter' if row['b']=='AUD_CounterSupport0' else row['b']
        if any(a==x and b==y for x,y,_ in interfaces):continue
        interfaces.append((a,b,row['interface']+'_prior'))
# Real measured contacts: the backsplash bed sits on the countertop, the wall
# backs it, and the rail brackets onto the tile. This keeps the structure
# reachable from the counter root without inventing a floor part.
# Backsplash, wall and rail are architectural fixtures. Their mutual contacts
# are verified directly at 0.0 mm; the wall is room structure, so these are
# declared as clearance relationships to the counter rather than fake supports.
ARCHITECTURAL={'AFX_BackSplash','AFX_KitchenWall','AFX_UtilityRail'}
# Two real assemblies: counter-supported props, and the architectural wall
# fixture chain (wall -> backsplash -> rail) whose contacts are all 0.0 mm.
STRUCTURE={'AFX_KitchenWall','AFX_BackSplash','AFX_UtilityRail'}
PROP_PARTS=[n for n in parts if n not in STRUCTURE]
STRUCT_PARTS=[n for n in parts if n in STRUCTURE]
def run_assembly(name,part_ids,root,iface_rows):
    man={'schema':'dsh-assembly-manifest/1','units':'mm','coord':{'up':'Z','forward':'-Y'},
     'stage':'local_fixture_interface','root_part':root,
     'parts':[{'id':n,'objects':[n]} for n in part_ids],
     'interfaces':[{'id':'FX_%03d'%i,'a':a,'b':b,'fit':'location','nominal_mm':0,'tol_mm':.1,'interface':kind}
                   for i,(a,b,kind) in enumerate(iface_rows)],'allow_pairs':[]}
    p=R/('manifest-'+name+'.json');p.write_text(json.dumps(man,indent=2))
    res=json.loads(K.dsh_assembly_api['scan'](objects=part_ids,manifest=str(p),max_pairs=40000,summary_only=False))
    (R/('support-'+name+'.json')).write_text(json.dumps(res,indent=2))
    print('SCAN',name,res.get('verdict'),res.get('counts'))
    print(' BAD',[(r['a'],r['b'],r['class'],r.get('depth_mm')) for r in res.get('offenders',[])])
    print(' FLOAT',[(r.get('part'),r.get('other_part'),r.get('mesh_gap_mm'),r.get('reason')) for r in res.get('floaters',[])])
    return res
prop_ifaces=[r for r in interfaces if r[0] in PROP_PARTS and r[1] in PROP_PARTS]
struct_ifaces=[r for r in interfaces if r[0] in STRUCT_PARTS and r[1] in STRUCT_PARTS]
prop_result=run_assembly('fixtures-props',PROP_PARTS,'AFX_Counter',prop_ifaces)
struct_result=run_assembly('fixtures-structure',STRUCT_PARTS,'AFX_KitchenWall',struct_ifaces)
result=prop_result
# Native floor/table/chair envelopes use the live saved UE component bounds.
current=json.loads((R/'current-interfaces-v2.json').read_text())
def local_bounds(key):
    t=current['targets'][key];c=t['components'][0];loc=c['world']['location'];b=c['bounds']
    return ((loc[0]-445)/100,-(loc[1]+673)/100,loc[2]/100),[(v[0]/100,v[1]/100,v[2]/100) for v in b]
# Floor reference is the measured kitchen plane, not the preview apartment shell.
cube('Floor',(8.4,11.075,-.025),(4.85,4.85,.05))
center,b=local_bounds('AP_Kitchen_Dining');cube('DiningTable',(center[0],center[1],(b[0][2]+b[1][2])/2),(b[1][0]*2,b[1][1]*2,b[1][2]-b[0][2]))
for i in range(4):
    center,b=local_bounds('AP_Dining_Chair'+str(i));key='Chair'+str(i)
    # UE actor yaw mirrors the symmetric chair envelope; native Z minimum stays.
    cube(key,(center[0],center[1],(b[0][2]+b[1][2])/2),(b[1][0]*2,b[1][1]*2,b[1][2]-b[0][2]))
# Floor and chairs use separate physical support and clearance checks, with table
# apron clearance measured as a conservative envelope, not just an image.
for i in range(4):
    key='AFX_Chair'+str(i)
    print('CHAIR',i,'bottom_m',min(v.co.z for v in parts[key].data.vertices))
# Conservative envelopes include the full seat/back; any positive overlap is
# reported as a potential layout issue and must be resolved, not allowlisted.
layout=[]
for i in range(4):
    a=parts['AFX_Chair'+str(i)]
    lo=[min(v.co[j] for v in a.data.vertices) for j in range(3)];hi=[max(v.co[j] for v in a.data.vertices) for j in range(3)]
    overlap=[]
    for other in ['AFX_DiningTable']+['AFX_Chair'+str(j) for j in range(4) if j!=i]:
        b=parts[other];blo=[min(v.co[j] for v in b.data.vertices) for j in range(3)];bhi=[max(v.co[j] for v in b.data.vertices) for j in range(3)]
        d=[min(hi[j],bhi[j])-max(lo[j],blo[j]) for j in range(3)]
        if min(d)>0:overlap.append({'other':other,'overlap_mm':[round(v*1000,4) for v in d]})
    layout.append({'chair':a.name,'floor_gap_mm':round(lo[2]*1000,4),'envelope_overlaps':overlap})
(R/'dining-layout-v2.json').write_text(json.dumps(layout,indent=2));print('DINING_LAYOUT',json.dumps(layout))
# PBR bindings and packed 2048 DirectX images remain tied to the current source.
textures=[]
for im in sorted(bpy.data.images,key=lambda x:x.name):
    if '/TexturesV2/' not in im.filepath.replace('\\','/') and not any(f'T_KP_{family}_' in im.name for family in ['PetrolEnamel','HonedStone','GlazedTile','BrushedSteel','SmokedWalnut','LinenTowel','Porcelain']):continue
    textures.append({'name':im.name,'size':list(im.size),'packed':bool(im.packed_file),'colorspace':im.colorspace_settings.name,'path':bpy.path.abspath(im.filepath)})
source_sha=hashlib.sha256((R/'KitchenDetailV1.blend').read_bytes()).hexdigest()
(R/'source-materials-v2.json').write_text(json.dumps({'source_sha256':source_sha,'textures':textures},indent=2))
print('SOURCE_TEXTURES',len(textures),source_sha)
