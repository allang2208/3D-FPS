"""Reuse native bow import and scoped close-up rendering, with V4 backup."""
from pathlib import Path
P=Path(__file__).parent
OLD=P.parent/'BowQuickCombatContact20260927'
source=(OLD/'import_contact.py').read_text()
source=source.replace('surface-fitted right grasp', 'open right palm push')
source=source.replace('generated_contact_v4.py', 'author_palm.py')
source=source.replace('BOW_RIGHT_CONTACT_SAVED', 'BOW_OPEN_PALM_SAVED')
(P/'import_palm.py').write_text(source,encoding='utf-8')

source=(OLD/'inspect_contact.py').read_text()
start=source.index('# Frame the right grip')
source='''"""Requested visual inspection of actual V7 palm, wrist and elbow skin."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;ROOT=P.parents[1];OUT=P/'Review'
case=P;version='after';script=P/'author_palm.py'
ns={'__file__':str(script)}
exec(compile(script.read_text().split('\\nbpy.ops.wm.open_mainfile')[0],str(script),'exec'),ns)
w=ns['pose'](.32)
'''+source[start:]
source=source.replace("Vector((-.04,0,.278))", "Vector((-.08,0,.308))")
source=source.replace("('side',Vector((.3,-.3,.1))),('palm',Vector((-.3,.2,.07))),('top',Vector((.1,.1,.4)))",
                      "('side',Vector((.05,.32,.08))),('palm',Vector((.32,-.14,.08))),('back',Vector((-.32,-.10,.08)))")
(P/'inspect_closeup.py').write_text(source)
