"""Extract actual glove skin and magazine contact surfaces for the bounded grasp fit."""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent
DIGITS=('thumb','index','middle','ring','pinky')
bpy.ops.wm.open_mainfile(filepath=str(S/'AKMReloadPolish20260911/base/A_AKM_reload.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(148)
skin=bpy.data.objects['SK_Manny_Arms_Export']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
names=['hand_l']+[b.name for b in r.data.bones if b.name.endswith('_l') and b.name.startswith(DIGITS)]
H=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()@r.pose.bones['hand_l'].matrix
rest_to_hand=rest['hand_l'].inverted();gn={g.index:g.name for g in skin.vertex_groups}
vertices=[];weights=[];indices=[];labels=[];diagnosis={};bad=[]
for v in skin.data.vertices:
    w={gn[g.group]:g.weight for g in v.groups if g.weight>1e-6}
    if sum(w.get(n,0) for n in names)<.985:continue
    indices.append(v.index);vertices.append(list(r.matrix_world.inverted()@skin.matrix_world@v.co))
    weights.append({n:x for n,x in w.items() if n in names})
    dominant=max(w,key=w.get);labels.append(dominant)
    if dominant.startswith(DIGITS) and dominant.split('_')[1].isdigit():
        digit=dominant.split('_')[0];j=int(dominant.split('_')[1]);other=sum(x for n,x in w.items() if n.startswith(DIGITS) and not n.startswith(digit+'_'))
        d=diagnosis.setdefault(f'{digit}_{j}',{'vertices':0,'other_digit_weight_max':0,'over_5_percent':0})
        d['vertices']+=1;d['other_digit_weight_max']=max(d['other_digit_weight_max'],other)
        d['over_5_percent']+=int(other>.05)
        if j>=2 and other>.05:bad.append({'index':v.index,'dominant':dominant,'other':other,'weights':w})
selected=set(indices)
faces=[list(p.vertices) for p in skin.data.polygons if all(i in selected for i in p.vertices)]
indexmap={old:new for new,old in enumerate(indices)}
data={'names':names,'parents':{n:r.data.bones[n].parent.name for n in names},
      'rest':{n:[list(row) for row in rest[n]] for n in names},
      'hand_in_mag':[list(row) for row in H], 'vertices':vertices,'indices':indices,
      'weights':weights,'labels':labels,'faces':[[indexmap[i] for i in p] for p in faces],
      'donor_basis':json.loads((S/'MannyGraspDonor20260912/donor_fit.json').read_text())['basis'],
      'magazines':{}, 'weight_diagnosis':diagnosis,'distal_cross_weights':bad}
for gun,src in [('AKM','PhantomRearGripIntegration20260913/AKM/AKM_RearGripSections_Editable.blend'),
                ('A762','A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(S/src));r=bpy.data.objects['SK_M4_Infima']
    verts=[];polys=[];obs=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        if gun=='AKM' and ob.name!='AKM_FactoryMagazine_Preview':continue
        if gun=='A762' and not ob.name.startswith('A762_R02_Magazine_'):continue
        group=ob.vertex_groups.get('WPN_SOCKET_Magazine')
        if group is None:continue
        ids={v.index for v in ob.data.vertices if any(g.group==group.index and g.weight>.99 for g in v.groups)}
        fs=[p for p in ob.data.polygons if all(i in ids for i in p.vertices)]
        if not fs:continue
        used=sorted({i for p in fs for i in p.vertices});mapping={i:len(verts)+j for j,i in enumerate(used)}
        xf=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()@r.matrix_world.inverted()@ob.matrix_world
        verts.extend([list(xf@ob.data.vertices[i].co) for i in used]);polys.extend([[mapping[i] for i in p.vertices] for p in fs]);obs.append(ob.name)
    if not verts:raise RuntimeError('Missing magazine geometry '+gun)
    data['magazines'][gun]={'vertices':verts,'faces':polys,'objects':obs,'source':src}
for gun,source in [('A762_extended','A762Meshy20260920/Accessories05/Exports/SM_A762_ext_mag.fbx')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(S/source));verts=[];faces=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        offset=len(verts);verts.extend([list(ob.matrix_world@v.co) for v in ob.data.vertices])
        faces.extend([[offset+i for i in p.vertices] for p in ob.data.polygons])
    data['magazines'][gun]={'vertices':verts,'faces':faces,'source':source,'objects':['imported FBX']}
(O/'fit_input.json').write_text(json.dumps(data))
(O/'weight_diagnosis.json').write_text(json.dumps({'segments':diagnosis,'distal_cross_weights':bad},indent=2))
print('GRASP_INPUT',len(vertices),len(faces),'distal_cross_weights',len(bad),'magazines',[(k,len(v['vertices']),v['objects']) for k,v in data['magazines'].items()],flush=True)
