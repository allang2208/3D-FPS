"""Freeze narrowly scoped authoring revisions; keep prior productions intact."""
from pathlib import Path
import shutil

P=Path(__file__).resolve().parent
S=P.parent
model=S/'GuanLeiReturnC8'; model.mkdir(exist_ok=True)
motion=S/'JiLeiMotionV5'; motion.mkdir(exist_ok=True)
audio=S/'JiLeiChargeAudioV1'; audio.mkdir(exist_ok=True)
for name in ['author_geometry.py','author_textures.py','finish_source.py','import_assets.py','import.ps1',
             'render_icon_source.py','import_icon.py','import_icon.ps1','publish.py']:
    text=(S/'GuanLeiInlaidC7'/name).read_text(encoding='utf-8-sig')
    for old,new in [('GuanLeiInlaidC7','GuanLeiReturnC8'),('GuanLei_InlaidC7','GuanLei_ReturnC8'),
                    ('GuanLeiC7','GuanLeiC8'),('GUANLEI_C7','GUANLEI_C8'),('guanlei-c7','guanlei-c8')]:
        text=text.replace(old,new)
    if name=='publish.py':
        text=text.replace('双向银纹嵌入一体锻肩，沿原厂雷纹圆徽回折收束',
                          '宽厚的回环锻肩环抱原厂雷纹圆徽，闭合银纹象征飞锤往复')
    (model/name).write_text(text,encoding='utf-8')
for name in ['import_assets.py']:
    text=(S/'JiLeiMotionV4'/name).read_text(encoding='utf-8-sig')
    text=text.replace('V4 supported elbow-out lift; arm-driven grip; native hinge and continuous recovery',
                      'V5 full-charge progressive right-hand lift; supported elbow; arm-driven grip and continuous recovery')
    text=text.replace('JI_LEI_V4','JI_LEI_V5')
    (motion/name).write_text(text,encoding='utf-8')
for dst in [motion,audio]:shutil.copy2(model/'import.ps1',dst/'import.ps1')

# Retain V4's solved shoulder/elbow/wrist and exact grip while replacing the
# early-finished trajectory. The last 8 cm of lift are shared by shoulder and
# wrist; the head also advances to stay inside the existing projection budget.
text=(S/'JiLeiMotionV4/author_motion.py').read_text(encoding='utf-8-sig')
text=text.replace('JiLeiMotionV3/JiLeiMotionV3_Editable.blend','JiLeiMotionV4/JiLeiMotionV4_Editable.blend')
start=text.index('best=None;design_options=[]')
end=text.index('e,ua0,fa0,n,qu0,qf0=support',start)
text=text[:start]+'''s1=old['Charge'][-1][U].translation.copy()
h1=old['Charge'][-1][H].translation.copy()
e1=old['Charge'][-1][F].translation.copy()
qh1=old['Charge'][-1][H].to_quaternion()
pole1=project(e1-s1,(h1-s1).normalized())
shaft=old['Charge'][-1]['WPN_root'].to_quaternion()@Vector((0,0,1))
roll=120; bend=30
''' + text[end:]
text=text.replace('lift=smooth((t-.14)/1.20)',
'''# C1-continuous lift across the full two-second authored charge. A first
 # phase establishes the one-hand hold, then the supported arm keeps rising.
 lift=smooth((t-.10)/1.90)
 rise=smooth((t-.42)/1.58)''')
text=text.replace('shoulder=s0.lerp(s1,lift);hand=h0.lerp(h1,lift)',
'''shoulder=s0.lerp(s1,lift);hand=h0.lerp(h1,lift)
 # Move the whole support chain, not the wrist alone. Forward travel keeps
 # the long head in frame while the hand visibly climbs by another 8 cm.
 raise_offset=Vector((.012,.105,.080))*rise
 shoulder+=raise_offset;hand+=raise_offset''')
text=text.replace('author(1.60*reverse,','author(2.0*reverse,')
text=text.replace('JiLeiMotionV4_Editable.blend','JiLeiMotionV5_Editable.blend')
# Replacement above must not change the input source to the not-yet-made file.
text=text.replace("P.parent/'JiLeiMotionV4/JiLeiMotionV5_Editable.blend'","P.parent/'JiLeiMotionV4/JiLeiMotionV4_Editable.blend'")
text=text.replace("'shoulder':list(s1),'elbow':list(e1),'wrist':list(h1)",
                  "'shoulder':list(charge[-1][U].translation),'elbow':list(charge[-1][F].translation),'wrist':list(charge[-1][H].translation)")
text=text.replace("'gameplay_run':False}","'extra_lift_cm':8,'extra_forward_cm':10.5,'lift_completion_seconds':2,'gameplay_run':False}")
text=text.replace('JI_LEI_V4_AUTHORED','JI_LEI_V5_AUTHORED')
(motion/'author_motion.py').write_text(text,encoding='utf-8')
print('Author sources prepared:',model,motion,audio)
