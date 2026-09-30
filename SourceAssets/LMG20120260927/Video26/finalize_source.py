"""Leave an editable assembled source after the isolated texture-baking stage."""
import bpy,re
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_Video26_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local.copy()
# The bake master is the authoritative untransformed high-poly normal source.
with bpy.data.libraries.load(str(O/'LMG201_Video26_HighLow.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n in ['H26_Body','H26_FrontSight','H26_RearSight']]
for donor in dst.objects:
    dest=bpy.data.objects['H26_'+donor['group']]
    normals=[root.to_3x3()@n.vector for n in donor.data.corner_normals]
    dest.data.normals_split_custom_set(normals)
    bpy.data.objects.remove(donor,do_unlink=True)
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    if ob.name.startswith('H26_'):ob.hide_render=True;ob.hide_set(True)
    elif ob.name.startswith('G26_'):ob.hide_render=False;ob.hide_set(False)
    elif ob.name.startswith('LMG201_'):
        retired=any(s in ob.name for s in ['Feed_','OldBelt','NewBelt','AmmoBox'])
        ob.hide_render=retired;ob.hide_set(retired)
steel={'BipodBase','BipodLegA','BipodLegB'}  # BodyRollback27 preserves prior body finish.
for mat in bpy.data.materials:
    key=re.sub(r'\.\d+$','',mat.name).removeprefix('M_LMG201_')
    if key not in steel or not mat.use_nodes:continue
    for n in mat.node_tree.nodes:
        if n.type=='BSDF_PRINCIPLED':
            n.inputs['Base Color'].default_value=(.027,.029,.031,1)
            n.inputs['Metallic'].default_value=.82;n.inputs['Roughness'].default_value=.4
        elif n.type=='MIX_RGB':
            n.inputs[0].default_value=.07;n.inputs[1].default_value=(.027,.029,.031,1)
        elif n.type=='MATH' and n.operation=='MULTIPLY' and abs(n.inputs[1].default_value-.065)<1e-5:
            n.inputs[1].default_value=.024
rig['AuthoringScope']='Video26 editable model: Surface25 body; new high/low lid, rail and sights. Native UE arms, Magazine24 actions, attachment transforms and wetness catalog remain authoritative in UE; no animation export.'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Video26_Editable.blend'))
print('VIDEO26_EDITABLE_ASSEMBLY_SAVED',flush=True)
