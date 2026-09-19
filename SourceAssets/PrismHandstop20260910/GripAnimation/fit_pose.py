"""Adapt the established M4 arm-chain solver to the actual short Hunyuan handstop."""
from pathlib import Path
O=Path(__file__).parent
reference=O/'ReferenceWorkflow/fit_pose.py'
source=reference.read_text(encoding='utf-8')
start=source.index('root=old[')
end=source.index('# Pure flexion')
source=source[:start]+'''root=old['WPN_root']
# Match the runtime mount in rifle reference space before moving with WPN_root.
rear=rest['WPN_RearSight'].matrix_local;front=rest['WPN_FrontSight'].matrix_local
forward=(front.translation-rear.translation).normalized()
up=rear.to_3x3().col[2].normalized();side=forward.cross(up).normalized()
up=forward.cross(-side).normalized()
mount=Matrix((forward,-side,up)).transposed().to_4x4()
mount.translation=rear.translation+forward*.27-up*.0805
G=root@rest['WPN_root'].matrix_local.inverted()@mount
M=G.copy();forward=G.to_3x3().col[0];side=-G.to_3x3().col[1];up=G.to_3x3().col[2]
with bpy.data.libraries.load(str(O.parent/'Polish/PrismHandstop_Editable.blend'),link=False) as (src,dst):dst.objects=['SM_PrismHandstop']
parts=[]
for ob in dst.objects:
 s.collection.objects.link(ob);ob.name='PH_Handstop';ob.matrix_world=G;parts.append(ob)
''' + source[end:]
source=source.replace('forward*.55-up*.835','-forward*.15-up*.989')
source=source.replace('side*.85+forward*.53','forward')
source=source.replace('[0,60,35]','[-20,55,25]')
source=source.replace('middle=G@Vector((.16,0,.035));middle-=side*.022','middle=G@Vector((-.026,.037,-.049))')
start=source.index('tb=r.pose.bones[')
end=source.index('for ob in s.objects:ob.hide_render',start)
source=source[:start]+source[end:]
source=source.replace("'fit_pose.json'","'fit_final.json'").replace('M4_Foregrip_Pose.blend','M4_Prism_Pose.blend')
exec(compile(source,str(O/'fit_generated.py'),'exec'))
