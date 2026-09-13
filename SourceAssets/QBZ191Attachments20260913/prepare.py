import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
def rows(m):return [list(v) for v in m]
def box(points):return {'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
def setpose(r,name,f):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191ContactWear20260913/QBZ191_ContactWear_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];setpose(r,'QBZ191_base_idle',0);inv=r.pose.bones['WPN_root'].matrix.inverted();restroot=r.data.bones['WPN_root'].matrix_local
report={'qbz':{'root_rest':rows(restroot),'mag0':rows(inv@r.pose.bones['WPN_SOCKET_Magazine'].matrix),'parts':{}}}
for ob in bpy.data.collections['QBZ_LOW'].objects:
 if ob.type!='MESH' or ob.get('is_static_head'):continue
 bone=ob.get('bone','WPN_root');points=[inv@r.pose.bones[bone].matrix@r.data.bones[bone].matrix_local.inverted()@v.co for v in ob.data.vertices]
 report['qbz']['parts'][ob.name]={'source_component':ob.get('source_component'),'bone':bone,**box(points)}
 if ob.name=='QBZ_Part19':
  report['qbz']['barrel_sections']={str(round(y,3)):box([v for v in points if abs(v.y-y)<.0027]) for y in [-.56+i*.005 for i in range(19)] if any(abs(v.y-y)<.0027 for v in points)}
bpy.ops.wm.open_mainfile(filepath=str(S/'M4DrumGrip20260910/Revision7/M4_DrumMatch_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];setpose(r,'A_M4_DrumMatch_reload',95)
rest={b.name:b.matrix_local.copy() for b in r.data.bones};M=r.pose.bones['WPN_SOCKET_Magazine'].matrix
report['donor']={'root_rest':rows(rest['WPN_root']),'mag_rest':rows(rest['WPN_SOCKET_Magazine']),'grasp_in_asset':rows(rest['WPN_SOCKET_Magazine']@M.inverted()@r.pose.bones['hand_l'].matrix),'fingers':{}}
for b in r.pose.bones:
 if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky')):report['donor']['fingers'][b.name]=rows(b.matrix_basis)
report['sources']={}
for key,info in json.loads((O/'sources.json').read_text()).items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=info['fbx'])
 objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
 pts=[ob.matrix_world@v.co for ob in objects for v in ob.data.vertices]
 entry={'objects':[ob.name for ob in objects],**box(pts)}
 if key=='drum':
  I=Matrix(report['donor']['root_rest']).inverted();entry['in_donor_root']=box([I@v for v in pts])
 report['sources'][key]=entry
(O/'geometry_inputs.json').write_text(json.dumps(report,indent=2));print('QBZ_ATTACHMENT_AUTHOR_INPUTS',json.dumps(report),flush=True)
