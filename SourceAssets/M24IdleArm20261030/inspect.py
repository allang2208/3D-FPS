from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24QuickMeleeContact20261028/library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
import numpy as np
skin=bpy.data.objects['M24_V9_BareArms']
source_pose=pose
code=(O.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
pose=source_pose
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
tree=ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full');exec(compile(ast.unparse(node),'morphs','exec'))
def set_pose(row):
    r.matrix_world=Matrix.Identity(4);r.animation_data_clear()
    for n,m in row.items():
        loc=row[parents[n]].inverted()@m if parents[n] else m;r.pose.bones[n].matrix_basis=local_rest[n].inverted()@loc
    bpy.context.view_layer.update();morphs_full()
def measures(row):
    result={}
    for n in ('clavicle_l','upperarm_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l'):
        loc=row[parents[n]].inverted()@row[n];lr=local_rest[n];delta=lr.inverted()@loc
        result[n]={'local_translation_cm':list(loc.translation*100),'ref_translation_cm':list(lr.translation*100),'local_scale':list(loc.to_scale()),'basis_rotation_deg':[math.degrees(x) for x in delta.to_euler()]}
    U=row['lowerarm_l'].translation-row['upperarm_l'].translation;L=row['hand_l'].translation-row['lowerarm_l'].translation;H=row['middle_01_l'].translation-row['hand_l'].translation
    result['chain']={'upper_len_cm':U.length*100,'fore_len_cm':L.length*100,'ref_upper_cm':(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).length*100,'ref_fore_cm':(rest['hand_l'].translation-rest['lowerarm_l'].translation).length*100,'elbow_bend':angle(U,L),'wrist_axis_bend':angle(L,H)}
    return result
if __name__=='__main__':
    out={};folder=O/'BeforeViews';folder.mkdir(exist_ok=True);s.render.resolution_x=800;s.render.resolution_y=540
    for label,row in [('raw',pose('idle',0,layer=False)[0]),('idle',pose('idle',0)[0]),('aim',pose('aim',0)[0]),('reference',rest)]:
        out[label]=measures(row);set_pose(row)
        for view in ('side','wrist','fps'):
            root=row['WPN_root']@rest['WPN_root'].inverted()
            if view=='fps':r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
            else:
                r.matrix_world=Matrix.Identity(4);target=row['hand_l'].translation if view=='wrist' else (row['hand_l'].translation+row['upperarm_l'].translation)*.5
                off=Vector((-.23,.08,.15)) if view=='wrist' else Vector((-.5,-.14,.20));cam.location=target+root.to_3x3()@off;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.24 if view=='wrist' else .67
            s.render.filepath=str(folder/(label+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
    (O/'inspection.json').write_text(json.dumps(out,indent=2));print('IDLE_CHAIN',json.dumps({k:v['chain'] for k,v in out.items()}),flush=True)
