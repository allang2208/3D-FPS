"""RSH rail-fit common grips and sparse, left-arm-only 715 animation layers."""
import bpy,bmesh,json,sys,copy,math,runpy
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1];S=O.parent
sys.path.insert(0,str(S/'RSH12InspectGrip20261004'))
sys.path.insert(0,str(S/'RSH12Speedloader20261003'))
from grip_scene import load,pose,matrix,applied,track_at,set_pose
from contact_motion import carry_arm,mix,smooth
sys.path.insert(0,str(S/'RSH12ResonanceWrist20261005'))
from arm_support import support_arm
sys.path.insert(0,str(S/'RSH12InspectArmRepair20261005'))
from inspect_support import rewrite_inspect
for folder in ('Exports','Profiles'): (O/folder).mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
donors=json.loads((S/'M16UniversalAttachments20260920/authoring.json').read_text())['donors']
ash=json.loads((S/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
sources=json.loads((S/'ASH12UniversalAttachments20260919/sources.json').read_text())
record={'parts':{},'source':'Existing common grips, original body proportions and UVs','rail_width_m':.016536,'runtime_tested':False}
finish_materials=runpy.run_path(str(S/'RSH12MaterialFinish20261005/finish_blender.py'))['foregrip_materials']
bpy.ops.wm.read_factory_settings(use_empty=True)
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def jaw(side,x0,x1,material):
    # Adapt only the contact insert to the narrower 16.536 mm RSH rail.
    sec=[(side*y,z) for y,z in ((.00829,-.001),(.0107,-.001),(.0107,.0019),(.0093,.0034),(.00829,.0018))]
    if side<0:sec.reverse()
    v=[(x,y,z) for x in (x0,x1) for y,z in sec];n=len(sec)
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new('RSH rail contact insert');me.from_pydata(v,[],f);me.materials.append(material)
    ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
    select([ob]);b=ob.modifiers.new('Contact edge radius','BEVEL');b.width=.00012;b.segments=2;bpy.ops.object.modifier_apply(modifier=b.name)
    return ob
for key in ('vertical','tactical_vertical','canted','prism','angled'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if key=='angled':
        path=S/'ResonanceGrip20260913/MeshyIntegration/M4/ResonanceGrip_Surface_Editable.blend'
        with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=['SM_ResonanceGrip']
        ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
        ob.data.transform(Matrix(ash['donors']['angled']['mount']).inverted())
    else:
        path=S/'TacticalVerticalForegrip20260919/Integration/M4/Export/SM_TacticalVerticalForegrip.fbx' if key=='tactical_vertical' else Path(sources[key]['fbx'])
        bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=True)
        obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
        for ob in obs:ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
        select(obs)
        if len(obs)>1:bpy.ops.object.join()
        ob=bpy.context.object
    # Tactical already uses the exact common vertical contact frame, Z=0.
    lift=0. if key=='tactical_vertical' else -max(v.co.z for v in ob.data.vertices)
    for v in ob.data.vertices:v.co.z+=lift
    material=bpy.data.materials.new('RSH_Foregrip_Insert');ob.data.materials.append(material)
    x0,x1=(-.026,.021) if key in ('angled','prism','tactical_vertical') else (-.014,.014)
    extras=[jaw(side,x0,x1,material) for side in (-1,1)]
    for ex in extras:
        for i in range(max(1,len(ob.data.uv_layers))):
            layer=ex.data.uv_layers.new(name=ob.data.uv_layers[i].name if i<len(ob.data.uv_layers) else 'UVMap')
            for f in ex.data.polygons:
                for li in f.loop_indices:
                    p=ex.data.vertices[ex.data.loops[li].vertex_index].co;layer.data[li].uv=(p.x/.04,p.z/.04)
    select([*extras,ob]);bpy.ops.object.join();ob.name='SM_RSH12_'+key
    finish_materials(ob)
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'Exports'/(ob.name+'_Editable.blend')))
    # Keep the contact behind the muzzle and ahead of cylinder swing.
    mount=Matrix(((0,1,0,0),(-1,0,0,-.094),(0,0,1,.0194712),(0,0,0,1)))
    family='vertical' if key=='tactical_vertical' else key
    hand=Matrix(donors[family]['hand_in_mount']);hand.translation.z+=lift
    record['parts'][key]={'family':family,'body_lift':lift,'mount':list(map(list,mount)),'hand':list(map(list,hand)),'slots':[m.name for m in ob.data.materials]}
    print('RSH_FOREGRIP_MODEL',key,flush=True)
(O/'models.json').write_text(json.dumps(record,indent=2))

rig,D,_,meta=load();profile=json.loads((S/'RSH12UnifiedGrip20261004/Single/profile.json').read_text())
names=list(D['parents']);rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
reflect=Matrix.Diagonal((1,-1,1,1));to_native=rig.matrix_world.inverted()@reflect@Matrix.Diagonal((.01,.01,.01,1));to_ue=to_native.inverted()
alignment=Matrix(meta['alignment'])
def palm(rest):
    inv=rest['hand_l'].inverted()
    a=inv@rest['index_01_l'].translation;b=inv@rest['pinky_01_l'].translation;c=inv@rest['middle_01_l'].translation
    y=c.normalized();x=(a-b).normalized();z=x.cross(y).normalized();x=y.cross(z).normalized()
    return Matrix((x,y,z)).transposed().to_4x4()
def weight(kind,t,duration):
    if kind.startswith(('single_','speed_')):
        # Original reload contacts own the whole middle, including opening,
        # cartridge pickup, loader insertion, cylinder closure and settling.
        return 1-smooth(t/.18) if t<.18 else smooth((t-(duration-.30))/.30)
    if kind=='quickcombat':return 1-smooth(t/.09) if t<.09 else smooth((t-(duration-.16))/.16)
    if kind.startswith('equip'):return smooth((t-(duration-.30))/.30)
    return 1.

for family in ('vertical','canted','prism','angled'):
    donor=donors[family];part=record['parts'][family];mount=Matrix(part['mount']);hand=Matrix(part['hand'])
    donor_rest={n:Matrix(v) for n,v in donor['rest'].items()}
    correction=palm(donor_rest)@palm(rest).inverted()
    result=copy.deepcopy(profile);result['family']=family
    finger_names=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
    for entry in result['clips']:
        kind=entry['kind'];times=[];tracks={}
        for sample in D['clips'][kind]['samples']:
            t=sample['time'];times.append(t);p=pose(rig,D,profile,kind,sample);old={n:m.copy() for n,m in p.items()}
            w=weight(kind,t,entry['duration']);held=p['WPN_root']@alignment@mount@hand@correction
            target=mix(old['hand_l'],held,w)
            # Small downward separation before the native lower/reload gesture.
            if kind=='quickcombat' or kind.startswith(('single_','speed_')):
                local=alignment@mount
                target.translation+=(p['WPN_root'].to_quaternion()@Vector((0,0,-.025)))*(math.sin(math.pi*w)**2)
            changed=carry_arm(p,old,names,'l',target)
            for n in finger_names:
                parent=D['parents'][n]
                if n not in donor['finger_basis'] or parent not in rest:continue
                local_rest=rest[parent].inverted()@rest[n]
                desired=local_rest@Matrix(donor['finger_basis'][n])
                original=old[parent].inverted()@old[n]
                # Retain RSH/V7 bone length; transfer the accepted rifle flexion.
                desired.translation=original.translation
                p[n]=p[parent]@mix(original,desired,w);changed.add(n)
            if family=='angled':
                changed.update(support_arm(p,rest,w))
            world={n:to_ue@m@reflect for n,m in p.items()}
            original=applied({n:matrix(v) for n,v in sample['local'].items()},entry,t)
            for n in changed:
                parent=D['parents'][n];lp=world[parent].inverted()@world[n]
                nt,nq,ns=lp.decompose();bt,bq,bs=matrix(sample['local'][n]).decompose()
                if not n.startswith(('clavicle_','ik_hand_')):nt=original[n].translation
                ns=original[n].to_scale();q=nq@bq.inverted()
                if q.w<0:q.negate()
                if n not in tracks:tracks[n]=[None]*(len(times)-1)
                tracks[n].append([*(nt-bt),q.x,q.y,q.z,q.w,*(ns-bs)])
            for n in tracks:
                if len(tracks[n])<len(times):tracks[n].append(None)
        existing={tr['bone']:tr for tr in entry['tracks']}
        for n,values in tracks.items():
            for i,v in enumerate(values):
                if v is None:values[i]=track_at(existing[n],times[i]) if n in existing else [0,0,0,0,0,0,1,0,0,0]
            constant=all(max(abs(a-b) for a,b in zip(values[0],v))<.00001 for v in values[1:])
            existing[n]=dict(bone=n,times=[0.] if constant else times,values=values[0] if constant else [x for v in values for x in v])
        entry['tracks']=list(existing.values())
        print('RSH_FOREGRIP_CLIP',family,kind,flush=True)
    if family=='angled':rewrite_inspect(rig,D,result)
    (O/'Profiles'/(family+'.json')).write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
    set_pose(rig,pose(rig,D,result,'idle',D['clips']['idle']['samples'][0]))
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'Profiles'/('RSH12_'+family+'_Editable.blend')))
print('RSH_FOREGRIP_AUTHORING_COMPLETE',flush=True)
