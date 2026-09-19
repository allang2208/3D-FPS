"""Editable observations from all native frames of the requested two seconds.

Screen coordinates are hand-authored observations, not recovered 3D ground truth.
Occluded joints and offscreen hilt endpoints are explicitly marked as inferred.
"""
import json
from pathlib import Path

import cv2
import numpy as np

P = Path(__file__).parent
# frame, wrist, index MCP, little MCP, guard center, pommel center,
# palm long direction depth, palm normal facing, sword shaft depth
# The spinning section is separately authored at EVERY native source frame.
CORE = [
 [0, [858,338], [759,245], [730,343], [739,212], [698,527], -.20, [.10,-1,.08], .12],
 [1, [830,410], [742,267], [754,337], [809,235], [557,507], -.20, [.10,-1,.05], .08],
 [2, [770,422], [799,257], [714,326], [889,277], [532,283], -.20, [.10,-1,.08], .05],
 [3, [737,420], [798,293], [708,314], [885,339], [558,162], -.15, [.10,-.9,.38], -.10],
 [4, [785,430], [817,308], [713,335], [821,333], [594,64], -.15, [.08,-.72,.70], -.12],
 [5, [841,432], [816,345], [715,357], [796,352], [726,-8], .02, [.06,-.5,.86], -.08],
 [6, [853,442], [788,350], [704,365], [780,367], [855,88], .10, [.02,-.35,.94], -.55],
 [7, [850,421], [751,305], [710,367], [708,285], [879,366], .12, [.08,-.65,.72], -.82],
 [8, [861,370], [746,282], [699,339], [750,253], [732,538], -.03, [.18,-.95,.22], .20],
 [9, [851,357], [747,257], [690,324], [774,228], [641,503], -.08, [.15,-.98,.12], .23],
 [10,[847,350], [746,240], [686,318], [797,223], [583,493], -.10, [.16,-.97,.18], .20],
 [11,[837,372], [735,220], [682,315], [820,206], [520,445], -.10, [.18,-.95,.25], .20],
 [12,[831,420], [733,245], [683,327], [848,274], [543,384], -.04, [.15,-.98,.16], .15],
 [13,[825,429], [731,247], [683,323], [870,324], [572,322], -.04, [.15,-.98,.10], .20],
 [14,[811,421], [719,249], [680,310], [870,339], [580,292], -.03, [.14,-.98,.10], .25],
]
# Direct pose authoring per digit and source frame, in degrees.
# Each tuple is MCP/PIP/DIP flexion, followed by independent splay.
# Frames 0 and 9+ use the accepted full-wrap pose. Intermediate tuples are
# independent authored poses, not one shared open/closed factor or fan template.
DIGITS = {
 'index': [[60,75,35,0],[46,60,30,3],[20,42,25,9],[6,25,14,12],[1,15,8,14],[-3,9,5,13],[-4,7,4,12],[10,21,9,8],[38,55,28,3],[60,75,35,0]],
 'middle':[[65,78,38,0],[49,59,30,0],[21,38,21,0],[8,24,13,1],[2,14,8,2],[-2,9,5,2],[-3,8,5,2],[21,39,18,1],[49,67,32,0],[65,78,38,0]],
 'ring':  [[68,80,40,0],[51,60,30,-2],[25,45,26,-4],[10,28,17,-8],[4,19,9,-11],[0,10,5,-13],[-2,8,4,-16],[15,31,15,-10],[45,63,31,-3],[68,80,40,0]],
 'pinky': [[70,81,41,0],[57,65,34,-4],[33,49,27,-10],[18,34,19,-16],[7,23,12,-23],[1,14,7,-29],[-1,10,6,-32],[9,25,13,-21],[35,56,30,-6],[70,81,41,0]],
}
# Observed tip silhouettes at full native resolution. Hidden tips are omitted.
# Each entry supplies MCP-independent targets; fitting keeps lengths and local
# flexion axes intact. Ambiguous depth is supplied by the authored pose above.
TIPS = {
 1:{'thumb':[636,295]},
 2:{'thumb':[692,275],'index':[818,203]},
 3:{'thumb':[691,280],'index':[837,228]},
 4:{'thumb':[640,264],'index':[812,259]},
 5:{'thumb':[632,275],'index':[813,288]},
 6:{'thumb':[622,306],'index':[753,274],'middle':[696,269],'ring':[651,285],'pinky':[625,312]},
 7:{'thumb':[656,319],'index':[714,294],'middle':[689,284],'ring':[660,301],'pinky':[647,328]},
}
NOTES = [
 '闭握，剑尖向上；腕部从画面右侧支撑。',
 '剑柄向左下通过；拇指和四指开始分开，腕部转向下方。',
 '剑柄横过，柄尾朝左；手腕下沉，掌部追随，指尖抬起。',
 '柄尾向左上；拇指独立让位，四指仍有不同程度弯曲。',
 '柄尾继续上行；掌面上翻，四指进一步展开。',
 '柄尾近竖直向上、剑身向下；拇指向左张开，掌面托近握柄。',
 '最大可见张掌；四指呈不等扇开，剑柄向右上近镜头通过。',
 '剑柄向右前方经过；手掌开始回卷，中指接回早于小指。',
 '剑刃回到上方，柄尾下行；四指快速回握，拇指尚在合拢。',
 '完整回握；剑继续倾转进入右侧持握。',
 '保持包握；柄尾继续向左下摆，手臂随姿态改变。',
 '闭握侧摆继续；掌部和剑作为整体运动。',
 '闭握抬柄尾，剑由斜立转为侧持。',
 '柄尾接近水平向左，腕部向右下承接。',
 '侧持形成，开始随移动轻微上下摆动。',
]

def track_patch(prev, curr, pts):
    nxt, status, error = cv2.calcOpticalFlowPyrLK(prev, curr, np.asarray(pts,np.float32).reshape(-1,1,2), None,
        winSize=(25,25), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
    out = []
    for old, new, ok in zip(pts,nxt.reshape(-1,2),status.reshape(-1)):
        out.append(new.tolist() if ok and np.linalg.norm(new-old)<65 else list(old))
    return out

records = []
for row in CORE:
    f, wrist, index, pinky, guard, pommel, long_depth, normal, shaft_depth = row
    records.append({'frame':f,'video_seconds':76+f/30,'file':f'source_{f+7:03d}.png',
        'observation':NOTES[f], 'wrist':wrist,'index_mcp':index,'pinky_mcp':pinky,
        'guard':guard,'pommel':pommel,'palm_long_depth':long_depth,'palm_normal_prior':normal,
        'shaft_depth_prior':shaft_depth,'tips':TIPS.get(f,{}),
        'digits':{n: values[min(f,9)] for n,values in DIGITS.items()},
        'digit_source':'independent native-frame pose authoring' if f<10 else 'closed grasp retained',
        'confidence':{'wrist':'inferred through glove/cuff','mcp':'inferred joint under visible glove',
                      'hilt':'visible centerline; offscreen ends extrapolated','depth':'3D reconstruction'},
        'landmark_method':'manual native-frame observation'})

# After the fast change, grip stays closed. Track visible hilt / glove features
# frame by frame instead of substituting an invented idle sine wave.
seed_frame=14
seeds=[[580,292],[702,250],[696,300]] # pommel, upper knuckle ridge, front thumb seam
tracked=np.array(seeds,float)
previous=cv2.imread(str(P/'Reference'/records[-1]['file']),cv2.IMREAD_GRAYSCALE)
seed=records[-1]
for f in range(15,61):
    path=P/'Reference'/f'source_{f+7:03d}.png'
    current=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
    nxt=np.array(track_patch(previous,current,tracked))
    # Median translation uses three specific hand/weapon features, not scenery.
    offset=np.median(nxt-tracked,axis=0)
    row=json.loads(json.dumps(records[-1]))
    row.update(frame=f,video_seconds=76+f/30,file=path.name,
               observation=('闭握侧持；保留本帧画面中的随动。' if f<39 else
                            '仍闭握，左手短暂进入柄尾附近，武器向下收势。' if f<49 else
                            '右手闭握于下方，保留收势后的持握及轻微随动。'),
               landmark_method='optical flow from three manually identified glove/hilt features',
               tracked_features=nxt.tolist(),tips={})
    for key in ['wrist','index_mcp','pinky_mcp','guard','pommel']:
        row[key]=(np.array(row[key])+offset).tolist()
    # The hilt is rigid in this part. Track its pommel explicitly while allowing
    # the pose solver to derive depth and orientation from the remaining inputs.
    row['pommel']=nxt[0].tolist()
    row['digits']={n:values[9] for n,values in DIGITS.items()}
    records.append(row)
    previous,tracked=current,nxt

data={'reference':'https://www.bilibili.com/video/BV1hCJFzQEyR/', 'range_seconds':[76,78],
      'fps':30,'image_size':[852,480],'camera_vertical_fov_degrees':75,
      'camera_note':'Project vertical FOV used for authoring; original FOV is not known.',
      'frame_count':61,'source_observation':'All 61 native frames, inclusive endpoints, reviewed in the reference sheets.',
      'replica_scope':'Motion reconstruction on existing Manny hands and rune sword; hidden depth is inferred.',
      'records':records}
(P/'reference_annotations.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 原视频 76–78 秒逐帧拆解','',
       '主参考只有 BV1hCJFzQEyR。30 fps，含两端共 61 帧。以下是画面观察；关节中心和深度不是实测三维数据。',
       '','| 帧 | 视频秒 | 观察 |','| --- | --- | --- |']
lines += [f'| {r["frame"]:02d} | {r["video_seconds"]:.4f} | {r["observation"]} |' for r in records]
lines += ['','快速段逐帧独立设姿；闭握段跟踪已标定的柄尾、拳部纹理，不加入额外转圈或重新设计速度。',
          '手模、剑体比例与视频不同；未把模糊/遮挡的关节中心写成精确测量。']
(P/'frame_breakdown.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('REFERENCE_ANNOTATION_READY',len(records),flush=True)
