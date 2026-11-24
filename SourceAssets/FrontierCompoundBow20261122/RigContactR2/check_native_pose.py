"""Call the built bow component in an isolated editor commandlet on transient objects."""
import ctypes as C,json,os,re
from pathlib import Path
import unreal as u
out=Path(os.environ['FRONTIER_BATCH'])
review=Path(os.environ['FRONTIER_REVIEW'])
source=Path(__file__).resolve().parent
# These public C++ methods are exported by FPSGAME, but are not Blueprint UFUNCTIONs.
module=C.CDLL(str(Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))/'Binaries/Win64/UnrealEditor-FPSGAME.dll'))
class V(C.Structure):
    _fields_=[('x',C.c_double),('y',C.c_double),('z',C.c_double)]
    def as_list(self):return [self.x,self.y,self.z]
def method(symbol,ret,args):
    f=getattr(module,symbol);f.restype=ret;f.argtypes=args;return f
vref=C.POINTER(V)
set_mesh=method('?SetFlexMesh@UBowFlexMeshComponent@@QEAAXPEAVUSkeletalMesh@@@Z',None,[C.c_void_p,C.c_void_p])
load=method('?ApplyStringLoad@UBowFlexMeshComponent@@QEAAXAEBU?$TVector@N@Math@UE@@0MM@Z',None,[C.c_void_p,vref,vref,C.c_float,C.c_float])
tips=method('?Tips@UBowFlexMeshComponent@@QEBA_NAEAU?$TVector@N@Math@UE@@0@Z',C.c_bool,[C.c_void_p,vref,vref])
def ptr(ob):
    m=re.search(r'\((0x[0-9A-Fa-f]+)\)',str(ob))
    if not m:raise RuntimeError('Unrecognized engine object representation '+str(ob))
    return int(m.group(1),16)
root='/Game/Weapons/FrontierCompoundBow/'
mesh=u.load_asset(root+'RigContactR2/SK_Frontier_Assembly')
redirects={}
for name in ('SK_Frontier_Assembly','SK_Frontier_Assembly_Skeleton','SM_Frontier_Rest'):
    # Use the same soft-object resolution as saved equipment.
    path=root+name+'.'+name
    asset=u.load_object(None,path)
    redirects[name]=asset.get_path_name() if asset else None
(out/'saved-paths.json').write_text(json.dumps(redirects,indent=2),encoding='utf8')
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
actor=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.Actor,u.Vector(),transient=True)
component=u.BowFlexMeshComponent(outer=actor)
engine=C.CDLL('UnrealEditor-Engine.dll')
register=getattr(engine,'?RegisterComponent@UActorComponent@@QEAAXXZ')
register.argtypes=[C.c_void_p];register.restype=None;register(ptr(component))
set_mesh(ptr(component),ptr(mesh))
anchors=json.loads((source/'anchors.json').read_bytes())
brace=V(*anchors['brace']);rows=[]
for index in range(25):
    nock=V(*[anchors['brace'][i]+(anchors['draw'][i]-anchors['brace'][i])*index/24 for i in range(3)])
    load(ptr(component),C.byref(nock),C.byref(brace),1.15,0.)
    upper,lower=V(),V()
    if not tips(ptr(component),C.byref(upper),C.byref(lower)):raise RuntimeError('No live string endpoints')
    row={'frame':index+1,'upper':upper.as_list(),'lower':lower.as_list(),'cables':{}}
    for s in ('upper','lower'):
        for k in range(2):
            name=s+'_cable'+str(k)
            pos=component.get_bone_transform_by_name(name,u.BoneSpaces.COMPONENT_SPACE).translation
            row['cables'][name]=[pos.x,pos.y,pos.z]
    rows.append(row)
(out/'native-poses.json').write_text(json.dumps(rows,indent=1),encoding='utf8')
def dist(actual,expected):
    return sum((x-y)**2 for x,y in zip(actual,(expected[0],-expected[1],expected[2])))**.5
expected=json.loads((review/'mesh-contact.json').read_bytes())
errors=[]
for a,b in zip(rows,expected):
    for side in ('upper','lower'):
        errors.append(dist(a[side],b['sides'][side]['tip']))
        for i,c in enumerate(b['sides'][side]['cables']):
            errors.append(dist(a['cables'][side+'_cable'+str(i)],c['pos']))
result={'poses':len(rows),'worst_endpoint_delta_cm':max(errors),'all_contacts_match':max(errors)<.003}
(out/'native-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8')
if not result['all_contacts_match']:raise RuntimeError(str(result))
if any('/RigContactR2/' not in str(path) for path in redirects.values()):raise RuntimeError('Retired factory path did not migrate')
# Replay the shipped right-hand draw markers with this bow's shared-contact offsets.
catalog=json.loads((Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir()))/'ColdSteelData/bows.json').read_bytes())['bow_frontier_compound']
clip=u.load_asset(catalog['bow_animation_prefix']+'Draw')
rb,rd=([float(v) for v in catalog[k].split(',')] for k in ('bow_reference_brace_cm','bow_reference_draw_cm'))
arms=u.BowArmsMeshComponent(outer=actor);register(ptr(arms))
arms.set_skeletal_mesh_asset(u.load_asset(catalog['bow_viewmodel']))
arms.play_animation(clip,False)
set_fit=method('?SetContactFit@UBowArmsMeshComponent@@QEAAX_NAEBU?$TVector@N@Math@UE@@111@Z',None,[C.c_void_p,C.c_bool,vref,vref,vref,vref])
set_weight=method('?SetContactFitWeight@UBowArmsMeshComponent@@QEAAXM@Z',None,[C.c_void_p,C.c_float])
set_fit(ptr(arms),True,C.byref(V(*rb)),C.byref(V(*rd)),C.byref(brace),C.byref(V(*anchors['draw'])))
set_weight(ptr(arms),1.)
tick=getattr(engine,'?TickAnimation@USkeletalMeshComponent@@QEAAXM_N@Z')
tick.argtypes=[C.c_void_p,C.c_float,C.c_bool];tick.restype=None
refresh=getattr(engine,'?RefreshBoneTransforms@USkeletalMeshComponent@@UEAAXPEAUFActorComponentTickFunction@@@Z')
refresh.argtypes=[C.c_void_p,C.c_void_p];refresh.restype=None
record=[]
for i in range(25):
    time=clip.get_play_length()*i/24.
    arms.set_position(time,False);tick(ptr(arms),0.,False);refresh(ptr(arms),None)
    grip=arms.get_socket_transform('bow_grip',u.RelativeTransformSpace.RTS_COMPONENT)
    mark=arms.get_socket_transform('bow_nock',u.RelativeTransformSpace.RTS_COMPONENT)
    grip.scale3d=u.Vector(1,1,1)
    v=u.MathLibrary.inverse_transform_location(grip,mark.translation)
    n=V(v.x,v.y,v.z)
    load(ptr(component),C.byref(n),C.byref(brace),1.15,0.)
    upper,lower=V(),V()
    if not tips(ptr(component),C.byref(upper),C.byref(lower)):raise RuntimeError('Missing animated exit')
    record.append({'time':time,'nock':n.as_list(),'upper':upper.as_list(),'lower':lower.as_list()})
(out/'draw-clip-contacts.json').write_text(json.dumps(record,indent=1),encoding='utf8')
