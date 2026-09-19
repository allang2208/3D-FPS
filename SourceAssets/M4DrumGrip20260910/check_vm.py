exec(open('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910/debug_live.py').read())
controller=bp.get_or_create_controller();graph=controller.get_graph()
r={'events':[str(n) for n in rig.get_supported_events()],'can_execute':rig.can_execute(),'nodes':len(graph.get_nodes()),'links':len(graph.get_links()),'pins':{}}
for node in graph.get_nodes():
 if node.get_name() in ['Forward','Backward','Get_Forward_hand_l','Set_Forward_hand_l']:
  r['pins'][node.get_name()]={p.get_name():p.get_default_value() for p in node.get_pins()}
hk=unreal.RigElementKey(name='hand_l',type=unreal.RigElementType.BONE)
r['before']=str(h.get_global_transform(hk));r['execute']=rig.execute('BeginExecution');r['after']=str(h.get_global_transform(hk))
(O/'vm_check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
