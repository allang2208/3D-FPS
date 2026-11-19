"""Assemble the requested pose evidence and record the review's exact scope."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs')
REVIEW=OUT/'AnatomyReview'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',30)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
canvas=Image.new('RGB',(1920,1630),(25,32,42));draw=ImageDraw.Draw(canvas)
draw.text((30,18),'Jason 关节姿态检查｜每格左：原版　右：R2 修正版',font=font,fill=(235,242,248))
draw.text((30,62),'读取已保存的 UE 网格与蒙皮权重；离线骨骼姿态，不含 UE 动画蓝图及姿态修正驱动。',font=small,fill=(174,190,205))
for index,(file,title) in enumerate([('03_elbows.png','屈肘'),('04_shoulders.png','抬臂'),('05_hip_knee.png','抬腿 / 屈膝'),('06_squat.png','下蹲')]):
    x=(index%2)*960;y=110+(index//2)*760
    draw.text((x+24,y),title,font=font,fill=(202,225,242))
    im=Image.open(REVIEW/file).convert('RGB').resize((960,720),Image.Resampling.LANCZOS)
    canvas.paste(im,(x,y+40))
canvas.save(REVIEW/'joint_review_overview.png')
delivery=json.loads((OUT/'delivery.json').read_text())
delivery['anatomy_review']={
    'saved_candidate_read_back':True,
    'bones_reviewed':342,
    'rest_rotations_scales_hierarchy_unchanged':True,
    'native_weights_unchanged':True,
    'repaired_regions':['armpit / inner upper arm','crotch / medial upper thigh'],
    'folded_faces_before':190,'folded_faces_after':0,
    'posed_review':['elbow flexion','shoulder elevation','hip and knee flexion','squat'],
    'posed_method':'Offline linear blend skinning from actual saved UE LOD0. Native head border follows body bones; facial pose neutral.',
    'limitations':['UE animation blueprint and pose-driver correctives not evaluated','Clothing and physics not tested'],
    'numerical_report':str(REVIEW/'numerical_report.json'),
    'pose_report':str(REVIEW/'pose_review.json'),
    'overview':str(REVIEW/'joint_review_overview.png')}
(OUT/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print('JASON_ANATOMY_DELIVERY_UPDATED')
