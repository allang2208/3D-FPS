"""Original reception print artwork and physically scaled textile/wood maps."""
from pathlib import Path
import json,math,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
BASE='/Game/Dungeons/ReceptionHall20261006/Refine20261007'
for p in ('Authored/Textures','Receipts','Snapshots','Scripts'): (ROOT/p).mkdir(parents=True,exist_ok=True)
for name,source in [('hall_geometry.py',PARENT/'Scripts/geometry.py'),('office_geometry.py',PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Scripts/geometry.py')]:
    shutil.copy2(source,ROOT/'Scripts'/name)
office=ROOT/'Scripts/office_geometry.py'
code=office.read_text('utf8').replace("    for face in obj.data.polygons:\n        wood=", "    src=obj.data.uv_layers['UVMap'];detail=obj.data.uv_layers['DetailLocal']\n    for face in obj.data.polygons:\n        wood=")
office.write_text(code,encoding='utf8')
for source in ('Config/layout.json','manifest.json'):
    dest=ROOT/'Snapshots'/Path(source).name
    if not dest.exists():shutil.copy2(PARENT/source,dest)
cn='C:/Windows/Fonts/msyh.ttc';en='C:/Windows/Fonts/consola.ttf'
def font(n):return ImageFont.truetype(cn,n)
im=Image.new('RGB',(4096,2048),(32,46,43));d=ImageDraw.Draw(im);rects={}
panels=[('roster','值班排班表','DUTY ROSTER  /  RECEPTION OPERATIONS'),('rules','接待工作制度','VISITOR SERVICES  /  STANDARD PROCEDURES'),('handover','交接班与应急联络','HANDOVER & EMERGENCY CONTACTS'),('visitors','访客服务须知','VISITOR INFORMATION')]
for i,(key,title,subtitle) in enumerate(panels):
    x=32+(i%2)*2048;y=32+(i//2)*1024;w=1984;h=944;rects[key]=[x,y,x+w,y+h]
    d.rectangle((x,y,x+w-1,y+h-1),fill=(225,224,208),outline=(133,145,133),width=5)
    d.rectangle((x+8,y+8,x+w-9,y+161),fill=(29,58,51))
    d.text((x+55,y+24),title,font=font(66),fill=(231,222,191));d.text((x+57,y+108),subtitle,font=ImageFont.truetype(en,26),fill=(173,195,178))
    if key=='roster':
        rows=[['班次 / 时间','登记接待','安检岗','调度协调','交接确认'],['早班  06:00—14:00','接待一组','安检 A 组','01 值班席','06:00 签入'],['中班  14:00—22:00','接待二组','安检 B 组','02 值班席','14:00 签入'],['夜班  22:00—06:00','值守接待','安检 C 组','01 值班席','22:00 签入']]
        xs=[50,590,930,1270,1620,1934]
        for row,words in enumerate(rows):
            yy=y+196+row*139
            if row%2==0:d.rectangle((x+50,yy,x+1934,yy+138),fill=(197,205,190))
            for k,word in enumerate(words):d.text((x+xs[k]+16,yy+39),word,font=font(34 if row else 36),fill=(32,55,47))
            d.line((x+50,yy,x+1934,yy),fill=(119,137,121),width=2)
        for xx in xs:d.line((x+xx,y+196,x+xx,y+752),fill=(119,137,121),width=2)
        d.text((x+60,y+807),'当班负责人须核对来访预约、证件归还及设备状态后签字交接。',font=font(34),fill=(54,68,57))
    else:
        lines={
          'rules':['01  核对预约与有效证件，登记访问事由及接待部门。','02  发放访客证，说明安检、等候及陪同路线。','03  随身物品经安检后放行；异常情况上报值班负责人。','04  未经授权不得进入设施作业区；访客全程由接待人陪同。','05  离场时收回访客证，核销登记并确认寄存物品。','06  妥善保存登记资料，不对外展示访客个人信息。'],
          'handover':['交接项目   访客证数量 / 寄存钥匙 / 未结预约 / 设备记录','登记席  1001        安检岗  1002        值班协调  1003','遇设备异常：停止使用，设置提示并通知维护人员。','遇人员滞留：联系接待部门，保留登记与联络记录。','紧急疏散：按现场指示引导，保持楼梯和通道畅通。','交班与接班人员共同确认后，在值班日志中签字。'],
          'visitors':['01  请在前台办理登记并佩戴访客证。','02  请将随身物品置于托盘内，依次通过安检。','03  完成安检后请在指定区域等候接待。','04  请勿拍摄设施内部设备或进入未授权区域。','05  如需无障碍服务，请联系前台工作人员。','06  离开时请归还访客证并取回寄存物品。']}[key]
        for j,line in enumerate(lines):
            yy=y+210+j*103;d.text((x+61,yy),line,font=font(37),fill=(32,55,47));d.line((x+61,yy+79,x+w-61,yy+79),fill=(185,192,175),width=2)
    d.text((x+w-400,y+h-46),'设施运行管理  /  内部张贴',font=font(23),fill=(100,113,98))
im.save(ROOT/'Authored/Textures/T_RH2_Boards.png')
(ROOT/'atlas.json').write_text(json.dumps(dict(size=[4096,2048],rects=rects)),encoding='utf8')
# Preserve the stock screen UV region while replacing freight text with reception content.
im=Image.open(PROJECT/'SourceAssets/StationWorkshop20261003/Authored/T_Workshop_PrintAtlas.png').convert('RGB');d=ImageDraw.Draw(im)
x,y,w,h=1240,16,784,441;d.rectangle((x,y,x+w,y+h),fill=(10,27,28));d.rectangle((x+12,y+12,x+w-12,y+64),fill=(23,64,57))
d.text((x+26,y+21),'FACILITY / VISITOR SERVICES',font=ImageFont.truetype(en,30),fill=(163,213,190))
for i,line in enumerate(['预约登记  08:30    已确认','访客通行  09:00    待接待','安检通道  01 / 02  开放','值班联络  1003     在线','今日登记  024      在场 008']):d.text((x+31,y+88+i*54),line,font=font(28),fill=(136,196,174))
d.rectangle((x+24,y+h-38,x+w-24,y+h-20),fill=(27,98,79));im.save(ROOT/'Authored/Textures/T_RH2_OfficePrint.png')
rng=np.random.default_rng(61007);n=1024;yy,xx=np.mgrid[0:n,0:n];noise=rng.normal(0,1,(n,n))
weave=(np.sin(xx*math.tau/8)*.48+np.sin(yy*math.tau/8)*.40+np.sin((xx+yy)*math.tau/32)*.12)
for key,height,col,variation,rough,strength in [
 ('Fabric',weave*.65+noise*.06,(101,116,105),8,207,1.8),
 ('Wood',np.sin(yy*math.tau*24/1024+np.sin(xx*math.tau/1024)*2)+.45*np.sin(yy*math.tau*114/1024+np.sin(xx*math.tau/512)),(104,74,50),11,159,.45)]:
    rgb=np.stack([np.clip(c+height*variation+noise*.65,0,255) for c in col],axis=-1).astype('uint8');Image.fromarray(rgb).save(ROOT/f'Authored/Textures/T_RH2_{key}_BaseColor.png')
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
    normal=np.stack((-dx,dy,np.ones_like(dx)*4),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8')).save(ROOT/f'Authored/Textures/T_RH2_{key}_NormalDX.png')
    Image.fromarray(np.clip(rough+height*7+noise,0,255).astype('uint8')).save(ROOT/f'Authored/Textures/T_RH2_{key}_Roughness.png')
print('RECEPTION_REFINEMENT_ARTWORK_SAVED')
