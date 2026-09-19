"""Adapt the retained V5 author to the V6 paired grip/blade motion channels."""
from pathlib import Path
P=Path(__file__).parent
path=P/'build_sword.py';s=path.read_text(encoding='utf-8')
s=s.replace('from arm_solver import ArmSolver','from arm_solver import ArmSolver\nfrom diagonal_motion import poses,READY,IDLE_FACE,WINDUP_END,CONTACT_START,CONTACT_END,ATTACK_END')
s=s.replace("export('SM_AzureRunesword.fbx',[sword])",'# Existing static mesh and skin remain installed; this revision authors animation only.')
start=s.index('base=Matrix.Translation((.13,.48,-.08))')
end=s.index('# Keep the hand anatomy',start)
s=s[:start]+'base=READY\nface_flip=IDLE_FACE\n'+s[end:]
s=s.replace('HL=face_flip.inverted()@HL;HR=face_flip.inverted()@HR\n','')
s=s.replace('solver.ready_pose(base@face_flip)','solver.ready_pose(base)')
s=s.replace('def apply(swordframe,angles,support=None):','def apply(gripframe,angles,support=None,swordframe=None):\n    swordframe=swordframe if swordframe is not None else gripframe@face_flip')
s=s.replace('solver.hand(side,swordframe,angles[side])','solver.hand(side,gripframe,angles[side])')
s=s.replace("r.data.pose_position='REST';export('SK_AzureRunesword_Manny.fbx',[arms,sword,r]);r.data.pose_position='POSE'","r.data.pose_position='POSE'")
start=s.index("idle=Matrix(motion['Sword_Idle']")
end=s.index('# Bake the blade',start)
s=s[:start]+"report={}\n\n"+s[end:]
s=s.replace('sf=sweep_pose(clip,CONTACT_START+(CONTACT_END-CONTACT_START)*u)','_,sf=poses(clip,CONTACT_START+(CONTACT_END-CONTACT_START)*u)')
start=s.index('def pose_at(')
end=s.index('s.render.fps=240',start)
s=s[:start]+"clips=[('Slash1',ATTACK_END),('Slash2',ATTACK_END)]\n"+s[end:]
s=s.replace('apply(base@face_flip,solver.ready)','apply(base,solver.ready)')
s=s.replace('for name,donor,duration in clips:','for name,duration in clips:')
s=s.replace('frames=[pose_at(name,donor,f/240,duration) for f in range(s.frame_end+1)]','paired_frames=[poses(name,f/240) for f in range(s.frame_end+1)]\n    frames=[pair[0] for pair in paired_frames]')
s=s.replace("hold=(math.ceil(WINDUP_END*240),math.floor(CONTACT_START*240)) if name in sweep_keys else None",'hold=(math.ceil(WINDUP_END*240),math.floor(CONTACT_START*240))')
s=s.replace("solver.fit_path(frames,name in ['Idle','Walk','Sprint'],hold)",'solver.fit_path(frames,False,hold)')
s=s.replace('support_path=solver.fit_support(frames,grasp_path,hold)','support_path=solver.fit_support(frames,grasp_path,hold)\n    support_path=solver.separate_arms(frames,grasp_path,support_path,hold)')
s=s.replace("{side:support_path[side][f] for side in ['l','r']})","{side:support_path[side][f] for side in ['l','r']},paired_frames[f][1])")
start=s.index('    report[name]=')
end=s.index("r.animation_data.action=bpy.data.actions['A_RuneSword_Idle']",start)
s=s[:start]+"    report[name]={'duration':duration,'fps':240,'frames':s.frame_end+1,'loop':False,'contact_window':[CONTACT_START,CONTACT_END],'hold_window':[WINDUP_END,CONTACT_START]}\n    print('AUTHORED',name,flush=True)\n# Retain exact accepted idle/locomotion/equip actions in the editable source.\nwith bpy.data.libraries.load(str(ROOT/'WeightLeftV5/AzureRunesword_Manny_Editable.blend'),link=False) as (src,dst):\n    dst.actions=['A_RuneSword_'+n for n in ['Idle','Walk','Equip','Sprint']]\n"+s[end:]
start=s.index("(P/'authoring.json').write_text")
s=s[:start]+"""(P/'authoring.json').write_text(json.dumps({'revision':'DiagonalHeavyV6','geometry_scale_from_v3':.8,'idle_blade_roll_degrees':115,'blade_contact_orientation':'width axis tangent to diagonal arc; independent of idle face','windup_seconds':WINDUP_END,'hold_seconds':CONTACT_START-WINDUP_END,'fast_phase_seconds':[CONTACT_START,CONTACT_END],'attack_seconds':ATTACK_END,'contact_arc_degrees':220,'followthrough_arc_end_degrees':208,'load_guard_cm':[27,30,10],'finish_guard_cm':[-37,26,-31],'second_slash':'mirror weapon trajectory across X; preserve anatomical left/right grips','ready_grasp_degrees':{k:math.degrees(v) for k,v in solver.ready.items()},'clips':report,'source':str(source),'retained_actions_source':str(ROOT/'WeightLeftV5/AzureRunesword_Manny_Editable.blend'),'arm_solution':'continuous grasp path, fixed load hold, joint elbow separation, unchanged bone lengths/rest/weights'},indent=2))
"""
path.write_text(s,encoding='utf-8')
