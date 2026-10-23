"""Runs inside the private engine host after model materials have been saved."""
import math
# Generic bounded soft mote shader, tinted at runtime for gold or destruction red.
m=material('M_FinalToll_Mote')
m.set_editor_property('used_with_nanite',False)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
m.set_editor_property('two_sided',True)
c=node(m,u.MaterialExpressionCustom,code='float2 d=(UV-.5)*2.;float r=dot(d,d);float a=saturate(exp(-r*5.)-exp(-5.))*Strength;return float4(EnergyTint*(1.+exp(-r*20.)*2.),a*.8);',output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
inputs={'UV':node(m,u.MaterialExpressionTextureCoordinate),'Strength':node(m,u.MaterialExpressionScalarParameter,parameter_name='Strength',default_value=0.),'EnergyTint':node(m,u.MaterialExpressionVectorParameter,parameter_name='EnergyTint',default_value=u.LinearColor(1,.64,.22,1))}
pins=[]
for key in inputs:
    pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
c.set_editor_property('inputs',pins)
for key,value in inputs.items():wire(value,c,key)
rgb=node(m,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
alpha=node(m,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
wire(c,rgb,str(L.get_material_expression_input_names(rgb)[0]))
wire(c,alpha,str(L.get_material_expression_input_names(alpha)[0]))
L.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
L.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
L.recompile_material(m);save(m)

mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=mesh.get_editor_property('skeleton')
opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
task=u.AssetImportTask();task.filename=str(P/'Motion/A_Runebound_FinalToll_DoubleHeavy.fbx');task.destination_path=D;task.destination_name='A_Runebound_FinalToll_DoubleHeavy';task.automated=True;task.save=False;task.options=opt
A.import_asset_tasks([task]);animation=u.load_asset(D+'/A_Runebound_FinalToll_DoubleHeavy')
if not animation:raise RuntimeError('Cannot import authored two-hand double heavy')
animation.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
animation.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(240,1))
u.AnimationLibrary.add_animation_notify_track(animation,'FinalTollTiming')
for key,t in [('Contact',.10),('SecondContact',.42),('Release',.54)]:u.AnimationLibrary.add_animation_sync_marker(animation,key,t,'FinalTollTiming')
save(animation);receipt['first_person_animation']=animation.get_path_name()

def quaternion_mix(a,b,w):
    qa=[a.w,a.x,a.y,a.z];qb=[b.w,b.x,b.y,b.z];dot=sum(x*y for x,y in zip(qa,qb))
    if dot<0:qb=[-x for x in qb];dot=-dot
    if dot>.9995:q=[x*(1-w)+y*w for x,y in zip(qa,qb)]
    else:
        angle=math.acos(max(-1.,min(1.,dot)));q=[(x*math.sin((1-w)*angle)+y*math.sin(w*angle))/math.sin(angle) for x,y in zip(qa,qb)]
    n=math.sqrt(sum(x*x for x in q));return u.Quat(q[1]/n,q[2]/n,q[3]/n,q[0]/n)
def blend_transform(a,b,w):
    return (u.Vector(a.translation.x*(1-w)+b.translation.x*w,a.translation.y*(1-w)+b.translation.y*w,a.translation.z*(1-w)+b.translation.z*w),quaternion_mix(a.rotation,b.rotation,w),u.Vector(a.scale3d.x*(1-w)+b.scale3d.x*w,a.scale3d.y*(1-w)+b.scale3d.y*w,a.scale3d.z*(1-w)+b.scale3d.z*w))
def pose(asset,t):
    opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.SOURCE
    return u.AnimPoseExtensions.get_anim_pose_at_time(asset,max(0.,min(t,asset.get_play_length())),opts)
def marker(asset,key,fallback):
    return next((x.time for x in u.AnimationLibrary.get_animation_sync_markers(asset) if str(x.marker_name)==key),fallback)
body_assets=[]
for row in json.loads((P/'body_roles.json').read_text('utf-8')):
    heavy=u.load_asset(row['heavy']);upper=u.load_asset(row['upper'])
    if not heavy or not upper:raise RuntimeError('Missing current hammer body donors '+row['variant'])
    skeleton=heavy.get_editor_property('skeleton');reference=u.AnimPoseExtensions.get_reference_pose(skeleton)
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(reference)]
    hc=marker(heavy,'Contact',heavy.get_play_length()*.40);uc=marker(upper,'Contact',upper.get_play_length()*.40);ur=marker(upper,'Release',upper.get_play_length()*.65)
    landed=pose(heavy,hc);rising=pose(upper,uc*.55)
    fps=120;frames=150;samples={n:[] for n in names}
    for frame in range(frames+1):
        t=frame/fps
        if t<=.10:one=pose(heavy,hc*(.7+.3*(t/.10)**1.6));two=one;w=0.
        elif t<.24:one=landed;two=rising;w=(t-.10)/.14;w=w*w*(3-2*w)
        elif t<=.42:one=pose(upper,uc*.55+(ur-uc*.55)*((t-.24)/.18)**1.5);two=one;w=0.
        else:one=pose(upper,ur+(upper.get_play_length()-ur)*max(0.,min(1.,(t-.42)/.83)));two=one;w=0.
        for n in names:samples[n].append(blend_transform(u.AnimPoseExtensions.get_bone_pose(one,n,u.AnimPoseSpaces.LOCAL),u.AnimPoseExtensions.get_bone_pose(two,n,u.AnimPoseSpaces.LOCAL),w))
    name='A_Runebound_FinalToll_Body_'+row['variant'];factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',skeleton)
    asset=existing(name) or A.create_asset(name,D,u.AnimSequence,factory)
    asset.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(fps,1))
    ctrl=asset.get_editor_property('controller');ctrl.open_bracket('Native hammer two-strike body performance',False)
    try:
        ctrl.set_frame_rate(u.FrameRate(fps,1),False);ctrl.set_number_of_frames(u.FrameNumber(frames),False)
        for n,keys in samples.items():
            ctrl.add_bone_curve(n,False)
            if not ctrl.set_bone_track_keys(n,[k[0] for k in keys],[k[1] for k in keys],[k[2] for k in keys],False):raise RuntimeError('Cannot author body bone '+n)
    finally:ctrl.close_bracket(False)
    asset.set_editor_property('enable_root_motion',False);asset.set_editor_property('force_root_lock',True)
    u.AnimationLibrary.add_animation_notify_track(asset,'FinalTollTiming')
    for key,t in [('Contact',.10),('SecondContact',.42),('Release',.54),('NativeWarhammerGrip',0.),('NativeWarhammerContinuousGrip',0.)]:u.AnimationLibrary.add_animation_sync_marker(asset,key,t,'FinalTollTiming')
    save(asset);body_assets.append(dict(row,asset=asset.get_path_name()))
    print('FINAL_TOLL_BODY_SAVED',row['variant'],flush=True)
receipt.update(complete=True,body_animations=body_assets,animation_assets_modified=1+len(body_assets),native_triangles=111240)
record()
