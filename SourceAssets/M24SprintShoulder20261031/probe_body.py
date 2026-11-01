from collections import Counter
weights=Counter();peaks=Counter()
for v in skin.data.vertices:
    for g in v.groups:
        n=skin.vertex_groups[g.group].name
        if n.endswith('_l'):weights[n]+=g.weight;peaks[n]+=int(g.weight>.5)
info={'weights':dict(weights),'majority_vertices':dict(peaks),'upper_bones':{n:{'location':list(rest[n].translation),'parent':parents[n]} for n in ('clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l')},'samples':{}}
folder=O/'BeforeViews';folder.mkdir(exist_ok=True)
for p,phase in ((0,0),(.15,0),(.3,0),(.5,0),(1,0),(1,.5)):
    row=runtime(p,phase);key=f'{p}_{phase}';info['samples'][key]=measures(row)
    view(row,folder/(key+'_fps.png'))
    set_pose(row);r.matrix_world=Matrix.Identity(4);target=(row['upperarm_l'].translation+row['lowerarm_l'].translation)/2
    for label,off in [('outer',(-.45,-.22,.18)),('inner',(.4,.2,.02))]:
        cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.46
        advanced.matrix_world=row['WPN_root']@rest['WPN_root'].inverted()@advanced_rest
        s.render.filepath=str(folder/(key+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
(O/'probe.json').write_text(json.dumps(info,indent=2));print('SHOULDER_PROBE',json.dumps({'weights':{n:w for n,w in weights.items() if any(x in n for x in ('clavicle','upperarm','spine'))},'upper_bones':info['upper_bones']}),flush=True)
