from pathlib import Path
P=Path(__file__).parent;file=P/'build_sword.py';text=file.read_text(encoding='utf-8')
text=text.replace('import bpy,json,math','import bpy,json,math,sys\nsys.path.insert(0,str(__import__("pathlib").Path(__file__).parent))\nfrom arm_solver import ArmSolver',1)
text=text.replace("export('SM_AzureRunesword.fbx',[sword])","# Uniform 80 percent of the accepted V3 geometry, pivoted at the guard.\nfor v in sword.data.vertices:v.co*=.8\nexport('SM_AzureRunesword.fbx',[sword])",1)
text=text.replace("math.radians(85)","math.radians(65)").replace("ready=(.13,.48,-.08,0,-18,85)","ready=(.13,.48,-.08,0,-18,65)")
start=text.index("grip_source={'l':HL,'r':HR}")
end=text.index('# Bind the blade',start)
replacement='''# Keep the hand anatomy intact; close the palm-to-hilt radial gap by 2.5 mm.
for grasp in [HL,HR]:
    radial=Vector((grasp.translation.x,grasp.translation.y,0))
    if radial.length>.0025:grasp.translation-=radial.normalized()*.0025
solver=ArmSolver(rest,{'l':HL,'r':HR},{'l':left_rel,'r':right_rel})
solver.ready_pose(base)
localrest={n:(rest[r.data.bones[n].parent.name].inverted()@m if r.data.bones[n].parent else m) for n,m in rest.items()}
def apply(swordframe,angles):
    p={n:m.copy() for n,m in rest.items()}
    for side in ['l','r']:solver.apply_arm(p,side,solver.hand(side,swordframe,angles[side]))
    p['WPN_root']=swordframe
    for n in ['Blade_Base','Blade_Tip']:
        local=rest['WPN_root'].inverted()@rest[n];local.translation*=.8
        p[n]=swordframe@local
    for b in r.pose.bones:
        b.matrix_basis=localrest[b.name].inverted()@(p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name])
    bpy.context.view_layer.update()
'''
text=text[:start]+replacement+text[end:]
text=text.replace("(.25+.83*v)","(.25+.83*v)*.8") if False else text.replace("(0,0,.25+.83*v)","(0,0,(.25+.83*v)*.8)")
start=text.index("        if name in sweep_keys:")
end=text.index('        for b in r.pose.bones:',start)
poseblock=text[start:text.index('        settle=',start)]
posefunction='def pose_at(name,donor,t,duration):\n'+''.join(line[4:]+'\n' for line in poseblock.rstrip().splitlines())+'    return sf\n\n'
text=text[:start]+"        sf=frames[f];apply(sf,{side:grasp_path[side][f] for side in ['l','r']})\n"+text[end:]
text=text.replace("clips=[('Idle'",posefunction+"clips=[('Idle'",1)
text=text.replace('apply(base)','apply(base,solver.ready)',1)
text=text.replace('s.frame_start=0;s.frame_end=round(duration*240);previous={};grip_angle=dict(ready_angles);twist_history.clear()',"s.frame_start=0;s.frame_end=round(duration*240);previous={}\n    frames=[pose_at(name,donor,f/240,duration) for f in range(s.frame_end+1)]\n    grasp_path=solver.fit_path(frames,name in ['Idle','Walk','Sprint'])\n    (P/('grasp_path_'+name+'.json')).write_text(json.dumps(grasp_path))")
text=text.replace("'revision':'WristRiftV3'","'revision':'CompactNaturalV4','geometry_scale_from_v3':.8,'blade_roll_from_v3_degrees':-20")
text=text.replace("'idle_blade_roll_delta_degrees':90","'idle_blade_roll_delta_degrees':70")
text=text.replace('ready_angles.items()','solver.ready.items()').replace("'right_below_guard':9,'left_below_guard':21.5","'right_below_guard':7.2,'left_below_guard':17.2")
text=text.replace('Produces editable source and game assets. No acceptance renders or tests.','Produces editable source and game assets; arm inspection is separately user-authorized.')
file.write_text(text,encoding='utf-8')
