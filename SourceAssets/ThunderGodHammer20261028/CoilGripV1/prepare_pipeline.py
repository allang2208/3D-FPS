"""Prepare dedicated Coil export, icon, saved UE assets, and scoped catalog entry."""
from pathlib import Path
P=Path(__file__).resolve().parent;V2=P.parent/'StaticFieldGripV2'
s=(V2/'finalize.py').read_text(encoding='utf-8')
for a,b in [('StaticField_Design','Coil_Design'),('StaticField_EditableParts','Coil_EditableParts'),
            ('SM_ThunderGodHammer_grip_static_field_V2','SM_ThunderGodHammer_grip_coil'),
            ('StaticFieldGripV2','CoilGripV1'),('StaticField_Editable','Coil_Editable'),
            ('StaticFieldGrip.glb','CoilGrip.glb'),('StaticField_Icon','Coil_Icon'),('static_field_grip_framed','coil_grip_framed')]:s=s.replace(a,b)
s=s.replace("design='../StaticFieldGripV1/Design/StaticField_ThreeViews.png'", "design='Design/Coil_ThreeViews.png'")
s=s.replace("geometry='Closed skived leather wrap with seam-adaptive topology, two-ply stitches, broad chased silver interlace and curved solid field seals; native end lands retained'", "geometry='Closed insulated sleeves, continuous copper induction winding, seated copper buses and titanium guards; exact native mating lands'")
s=s.replace("normal_maps='4096x8192 leather atlas plus 4096x4096 steel/silver; cellular grain, exact needle sockets, forged grain, directional scratches; OpenGL source, UE flip green'", "normal_maps='2048x2048 Rubber/Titanium/Copper PBR: physical-scale insulation grain, directional brushed metals and scratches; OpenGL source, UE flip green'")
(P/'finalize.py').write_text(s,encoding='utf-8')
s=(V2/'import_assets.py').read_text(encoding='utf-8')
for a,b in [('StaticFieldGripV2','CoilGripV1'),('T_StaticField_','T_Coil_'),('static_field_grip','coil_grip'),('StaticField_Icon','Coil_Icon')]:s=s.replace(a,b)
s=s.replace("8192 if family=='Leather' else 4096",'2048')
s=s.replace('ue_thunder_god_hammer_grip_static_field','ue_thunder_god_hammer_grip_coil_grip')
s=s.replace('settings.fallback_percent_triangles = 1.', 'settings.fallback_percent_triangles = .15')
s=s.replace('full_fidelity_fallback=True','full_fidelity_fallback=False,nanite_triangles=mesh.get_num_nanite_triangles(),fallback_triangles=mesh.get_num_triangles(0)')
s=s.replace("generator='Blender render of current V2 model'", "generator='Blender render of current Coil production model'")
(P/'import_assets.py').write_text(s,encoding='utf-8')
(P/'install.ps1').write_text((V2/'install.ps1').read_text(encoding='utf-8'),encoding='utf-8')
print('COIL_PIPELINE_PREPARED')
