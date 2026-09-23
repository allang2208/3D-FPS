"""Update only the left magazine contact in the ten installed SVD reload clips."""
import bpy,ast,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True)
def read_functions(path,names):
 tree=ast.parse(path.read_text(encoding='utf-8-sig'))
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(path),'exec'),globals())
read_functions(S/'SVDCompletion20260923/author_svd.py',['sample','bake','select','smooth','mix'])
read_functions(S/'SVDHandRepair20260923/author_animations.py',['copy','arm','basis','finger_names','apply_fingers','setup','lerp_fingers'])
fit=json.loads((O/'grasp_fit.json').read_text());previous=json.loads((S/'SVDHandRepair20260923/authoring.json').read_text())
H=Matrix(fit['hand_in_mag']);closed={n:Quaternion(q) for n,q in fit['finger_basis'].items()};opened={n:Quaternion(q) for n,q in fit['open_basis'].items()}
bpy.context.preferences.filepaths.save_version=0;report={}
for family in ['base','vertical','canted','prism','angled']:
 source=S/'SVDHandRepair20260923'/f'SVD_{family}_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));setup()
 # Include the completed mouth in the editable animation scenes as well.
 with bpy.data.libraries.load(str(O/'SVD_MagazineComplete_Editable.blend'),link=False) as (src,dst):
  dst.meshes=['SVD_MagazineMouth_ClosedInterior']
 mesh=dst.meshes[0];original=bpy.data.objects['SM_SVD_Magazine']
 ob=bpy.data.objects.new('SM_SVD_MagazineInterior',mesh);bpy.context.collection.objects.link(ob)
 ob.parent=original.parent;ob.matrix_parent_inverse=original.matrix_parent_inverse.copy();ob.matrix_world=original.matrix_world.copy()
 ob.vertex_groups.new(name='WPN_SOCKET_Magazine').add(list(range(len(mesh.vertices))),1,'REPLACE');ob.modifiers.new('SharedManny','ARMATURE').object=r
 for clip in ['reload','reload_empty']:
  key=family+'/'+clip;info=previous[key];name=info['name'];source_action=bpy.data.actions[name];poses=[]
  for f in range(info['frames']+1):
   p=sample(r,source_action,f)
   if 18<f<302:
    original_hand=p['hand_l'].copy();original_fingers=basis(p,'l');mag=p['WPN_SOCKET_Magazine'];held=mag@H
    if f<=49:
     approach=held.copy();approach.translation+=mag.to_3x3()@Vector((.025*(1-smooth((f-34)/15)),.006*(1-smooth((f-34)/15)),0))
     hand=mix(original_hand,approach,smooth((f-18)/16));q={}
     for n in closed:
      digit=n.split('_')[0];delay={'thumb':0,'index':1,'middle':2,'ring':3,'pinky':4}[digit]
      ready=original_fingers[n].slerp(opened[n],smooth((f-18)/14))
      q[n]=ready.slerp(closed[n],smooth((f-34-delay)/(15-delay)))
    elif f<=240:hand=held;q=closed
    else:
     q={}
     for n in closed:
      digit=n.split('_')[0];delay={'thumb':0,'index':1,'middle':2,'ring':3,'pinky':4}[digit]
      q[n]=closed[n].slerp(opened[n],smooth((f-240-delay)/10))
     hand=held.copy();hand.translation+=mag.to_3x3()@Vector((.060,.010,-.012))*smooth((f-254)/20)
     weight=smooth((f-274)/28);hand=mix(hand,original_hand,weight)
     # Outside detour is shared by the whole hand; the thumb keeps its rear opening.
     hand.translation+=mag.to_3x3()@Vector((.010*math.sin(math.pi*weight),0,-.010*math.sin(math.pi*weight)))
     q=lerp_fingers(q,original_fingers,smooth((f-282)/20))
    arm(p,hand,'l');apply_fingers(p,q,'l')
   poses.append(p)
  source_action.name='REFERENCE_PRE_MAGFIT_'+name
  action=bake(r,poses,name.removeprefix('A_SVD_'),120)
  report[key]={**info,'source':str(D/(name+'.fbx')),'previous_blend':str(source),
   'blend':str(O/f'SVD_{family}_Editable.blend'),'changed':'left magazine hold and approach/release 18-302; original rig, right side, mechanical tracks and event timing retained',
   'grasp_donor':fit['donor'],'game_tested':False}
  (O/'authoring.json').write_text(json.dumps(report,indent=2));print('SVD_MAG_ANIMATION_AUTHORED',key,flush=True)
 sample(r,bpy.data.actions[previous[family+'/reload']['name']],180)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'SVD_{family}_Editable.blend'))
print('SVD_MAG_ANIMATIONS_COMPLETE',len(report),flush=True)
