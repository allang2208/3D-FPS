"""Four editable weapon/V9 family timelines; source delivery only, no rendering."""
from pathlib import Path
O=Path(__file__).parent
template=(O.parent/'RootClearance20261019/export_editable.py').read_text(encoding='utf-8')
for family in ('angled','vertical','canted','prism'):
 code=template.replace('profile_root_clearance.json','Profiles/DA_SVCH_Grip_'+family+'.json')
 code=code.replace('SVCH_RootClearance_', 'SVCH_Foregrip_'+family+'_')
 code=code.replace('scene.frame_set(325)','scene.frame_set(0)')
 code=code.replace('"if role == \'reload_empty\':"','"if role == \'idle\':"')
 inject="""
code=code.replace("for role in ('reload', 'reload_empty'):","for role in motion['clips']:")
code=code.replace("'editable_source.json'","'editable_source_FAMILY.json'")
code=code.replace("scene.frame_end = 400","scene.frame_end = 745")
code=code.replace("world_samples = {}",'''# Exact installed body at the calibrated mount, weighted to the existing gun root.
donors=load('donors')
mount=Matrix(json.loads((O/'mount.json').read_text())['matrix_root_cm'])
rootref=transform(weapon['reference'][indices['WPN_root']])
pp,pq,ps=rootref.decompose();rootref=Matrix.LocRotScale(pp,pq,Vector((1,1,1)))
gripdata=donors['FAMILY']['mesh']
gmesh=bpy.data.meshes.new('SVCH_FAMILY_GripMesh')
gmesh.from_pydata([tuple(CI @ rootref @ mount @ Vector(p)) for p in gripdata['positions']],[],[tuple(reversed(t)) for t in gripdata['triangles']])
gmesh.update()
grip=bpy.data.objects.new('SVCH_FAMILY_Grip',gmesh);scene.collection.objects.link(grip)
vg=grip.vertex_groups.new(name='WPN_root');vg.add(list(range(len(gmesh.vertices))),1.,'REPLACE')
modifier=grip.modifiers.new('FollowWeapon','ARMATURE');modifier.object=rig
grip['ue_source_mesh']=gripdata['path']
world_samples = {}''')
""".replace('FAMILY',family)
 code=code.replace("exec(compile(code,str(source),'exec'),globals())",inject+"\nexec(compile(code,str(source),'exec'),globals())")
 exec(compile(code,str(O/'export_editable.py'),'exec'),{'__file__':str(O/'export_editable.py'),'__name__':'__main__'})
