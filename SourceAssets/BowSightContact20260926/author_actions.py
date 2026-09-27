"""Bow V11: route the support forearm outside the string plane, native bind retained."""
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME')
P=Path(__file__).parent
base=ROOT/'SourceAssets/DarkBow20260925'
source=(base/'ReferenceUpgradeV10/author_actions.py').read_text(encoding='utf8')
source=source.replace("PROJECT=P.parents[2]", "PROJECT=Path('D:/FPS3D/FPSGAME')")
source=source.replace("V9=P.parent/'ContactV9'", "V9=PROJECT/'SourceAssets/DarkBow20260925/ContactV9'")
source=source.replace("P.parent/'", "PROJECT/'SourceAssets/DarkBow20260925/")
source=source.replace("shoulder_target=SHOULDERS[side].lerp(raised_shoulder,raised)",
    "shoulder_target=SHOULDERS[side].lerp(raised_shoulder,raised)\n"
    "        if side=='l':\n"
    "            # Keep the unloaded elbow and forearm on the palm side of the string.\n"
    "            safe_shoulder=bow@bow_frame(0.).inverted()@PREP_SHOULDERS[side]\n"
    "            shoulder_target=safe_shoulder.lerp(raised_shoulder,raised)\n"
    "            safe_clav=bow.to_3x3()@bow_frame(0.).to_3x3().transposed()@rest[clav].to_3x3()\n"
    "            world[clav]=mat(world[clav].translation,safe_clav.to_quaternion().slerp(rest[clav].to_quaternion(),raised).to_matrix())")
source=source.replace("bend=(pole-shoulder)-axis*(pole-shoulder).dot(axis)",
    "if side=='l':pole=(bow@bow_frame(0.).inverted()@PREP_ELBOW_POLES[side]).lerp(pole,raised)\n"
    "        bend=(pole-shoulder)-axis*(pole-shoulder).dot(axis)")
source=source.replace("world[up]=mat(shoulder,du@rest[up].to_3x3())",
    "if side=='l':\n"
    "            # Distribute a quarter of the palm-side roll across the upper arm,\n"
    "            # avoiding the skinned inner-elbow fold without moving a joint.\n"
    "            compatible=limb_frame(ud,hands[side]@ref_across)@limb_frame(ru,ref_across).transposed()\n"
    "            du=du.to_quaternion().slerp(compatible.to_quaternion(),.25).to_matrix()\n"
    "        world[up]=mat(shoulder,du@rest[up].to_3x3())")
source=source.replace("bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_BareArmsV7_Actions.blend'))", "bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_SupportClearanceV11.blend'))")
source=source.replace('Raised Draw[0], short support travel, rearward follow-through; ADS/crouch use runtime pivot',
    'V11 unloaded support shoulder/elbow outside string plane; hand contact and draw timing retained')
(P/'generated_actions.py').write_text(source,encoding='utf8')
exec(compile(source,str(P/'generated_actions.py'),'exec'),{'__file__':str(P/'generated_actions.py')})
