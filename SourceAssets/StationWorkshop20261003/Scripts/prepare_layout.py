"""Bounded author placements, three dressing states and native-aspect print atlas."""
import json,math,copy
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];BASE='/Game/Dungeons/StationWorkshop20261003'
read=lambda p:json.loads(p.read_text('utf8'))
manifest=read(ROOT/'Authored/manifest.json');origin=[-450,850,0]
kitroot=PROJECT/'SourceAssets/DungeonWorkbenchKit20260921'
kit=read(kitroot/'Authored/manifest.json');kc=read(kitroot/'Config/workbench.json');ka=read(kitroot/'Receipts/asset-import.json')
containers=read(PROJECT/'SourceAssets/WarehouseContainers20261002/Authored/manifest.json')['prototypes']
staff=read(PROJECT/'SourceAssets/DungeonStaffLiving20261002/Production20261002/Config/modules.json')

def world(p):return [round(p[i]+origin[i],4) for i in range(3)]
def part(mesh,p=(0,0,0),yaw=0,collision=False,materials=None):
    return dict(mesh=mesh,position=world(p),yaw=yaw,scale=[1,1,1],collision=collision,
        affects_navigation=collision,materials=materials or [],fluid=False,station_workshop_part=True)

fixed=[]
for e in manifest['objects']:
    if e['kind'] in ('DispatchFiles_Body','DispatchFiles_Drawer','DispatchPaper','OperatorMat'):continue
    fixed.append(part(e['asset'],collision=e['collision']))
fixed.append(part(BASE+'/Meshes/SM_SW_OperatorMat',[250,330,0]))

def bench(state):
    cfg=kc['variants'][state];out=[]
    for e in kit['components']:
        if e['id'] in cfg['omit'] or e['id']=='Surface_UtilityDetail':continue
        group=e['group'];local=[0,0,0]
        if group=='Wall':local=kc['anchors']['WallOrigin']
        if group=='Table':local=[0,0,kc['table_height_cm']]
        if group=='Lamp':local=kc['anchors']['LampBase']
        offset=cfg.get('tool_offsets',{}).get(e['id'],{});delta=offset.get('translation',[0,0,0])
        p=[local[i]+e['relative_location'][i]+delta[i] for i in range(3)]
        p=[340-p[1],707+p[0],p[2]]
        paths=[ka['materials'][state][e['material_paths'][m]] for m in e['materials']]
        out.append(part(ka['meshes'][e['id']],p,90+offset.get('yaw',0),e['collision'],paths))
    return out

def container(key,p,yaw,id,fraction=0):
    out=copy.deepcopy(containers[key]);out.pop('dimensions_m',None)
    out.update(type='scene_container',body='/Game/Dungeons/WarehouseContainers20261002/Meshes/'+out['body'],
        door='/Game/Dungeons/WarehouseContainers20261002/Meshes/'+out['door'],position=world(p),yaw=yaw,
        container_id='StationWorkshop.'+id,initial_open_fraction=fraction)
    return out

variants=[]
for index,(identity,state,chair,paper,extra,fraction) in enumerate([
 ('MaintenanceActive','InUse',[585,178,0,-12],[666,88,77.5,-7],True,0),
 ('ShiftHandover','Idle',[604,200,0,18],[679,91,77.5,11],False,.48),
 ('InterruptedRepair','Abandoned',[560,199,0,-24],[668,95,77.5,-17],True,.3)]):
    props=bench(state)
    props.append(part('/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_Chair',chair[:3],chair[3],True))
    props.append(part(BASE+'/Meshes/SM_SW_DispatchPaper',paper[:3],paper[3]))
    boxes=[container('ToolCabinet',[33,350,0],90,'Tools',fraction),
        container('ToolDrawer',[33,350,0],90,'Tools.Drawer',.16 if index==2 else 0),
        container('Tote',[708,647,31.5],0,'Rack.ToteA'),container('Tote',[819,647,31.5],0,'Rack.ToteB'),
        container('MetalCase',[1130,565,0],-6+index*7,'Exterior.EquipmentCase')]
    boxes.append(dict(type='scene_container',body=BASE+'/Meshes/SM_SW_DispatchFiles_Body',
        door=BASE+'/Meshes/SM_SW_DispatchFiles_Drawer',position=world([667,74,0]),yaw=180,
        container_id='StationWorkshop.DispatchFiles',caption='调度文件抽屉',storage_pages=1,
        hinge=[0,-29,47],opening_motion='Drawer',drawer_travel=[0,-34,0],initial_open_fraction=.12 if index==1 else 0))
    if extra:boxes.append(container('WoodCrate',[913,428,0],-4+index*6,'ReservedSpares'))
    variants.append(dict(id=identity,parts=props,containers=boxes))

lamps=[]
for id,p,intensity,radius,shadow,color in [
 ('MaintenanceCeiling',[290,335,295],1500,500,False,[1,.83,.65]),
 ('DispatchCeiling',[780,355,295],1150,480,False,[.73,.84,1]),
 ('BenchTask',[254.6,632.1,142.88],85,180,False,[1,.76,.52])]:
    lamps.append(dict(id='StationWorkshop.'+id,position=world(p),type='point',intensity=intensity,radius=radius,
        optimized_radius_cm=radius,color=color,role='key' if id=='MaintenanceCeiling' else 'fill',cast_shadows=shadow,
        max_draw_distance_cm=2600 if radius>200 else 1500,fade_range_cm=500,station_workshop_light=True))
rules=dict(revision=1,origin_cm=origin,dimensions_cm=[1000,700,320],fixed_parts=fixed,lights=lamps,
    variants=variants,preview_variant='InterruptedRepair',outline=staff['container_outline'],rewards_deferred=True,
    bounds=dict(min=world([-10,-14,0]),max=world([1220,711,344])),
    personnel_door_cm=[60,180,246],service_door_cm=[760,980,276],
    platform_clearance_cm=325,tests_run=False,rendered=False)
refine_receipt=ROOT/'RefineV2/Receipts/install.json'
if refine_receipt.exists() and read(refine_receipt).get('stage')=='maps_saved':
    import runpy
    rules=runpy.run_path(str(ROOT/'RefineV2/Scripts/prepare_refine.py'))['apply'](rules)
refine_v3_receipt=ROOT/'RefineV3/Receipts/install.json'
if refine_v3_receipt.exists() and read(refine_v3_receipt).get('stage')=='maps_saved':
    import runpy
    rules=runpy.run_path(str(ROOT/'RefineV3/Scripts/prepare_refine.py'))['apply'](rules)
(ROOT/'Config/workshop.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2),encoding='utf8')

im=Image.new('RGB',(2048,2048),(198,201,188));draw=ImageDraw.Draw(im)
def font(n):return ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',n)
def mono(n):return ImageFont.truetype('C:/Windows/Fonts/consola.ttf',n)
def panel(key,color=(219,219,197)):
    x,y,w,h=manifest['regions'][key];draw.rectangle((x,y,x+w-1,y+h-1),fill=color)
    draw.rectangle((x+3,y+3,x+w-4,y+h-4),outline=(40,61,58),width=5)
    return x,y,w,h
x,y,w,h=panel('Board');draw.rectangle((x+8,y+8,x+w-9,y+93),fill=(31,58,54))
draw.text((x+28,y+22),'货运设备维护 / 调度安排',font=font(55),fill=(235,233,208))
for i,line in enumerate([
 '当班负责人：陈伟    值班联络：02-317',
 '06:30—07:00  交接、核对运单及封签',
 '07:00—11:30  入站卸货 / 装卸设备巡检',
 '13:00—17:30  出站配载 / 托盘周转',
 '18:00—22:00  夜班调度 / 输送电机检修',
 '维修登记：M-04 电机异响，拆检轴承',
 '维护要求：断电挂牌；工具归位；擦净油污',
 '安全要求：严禁遮挡站台通路及维修门',
 '交班前填写设备编号、故障、处理及签名',
 '未完成工单：M-04 / C-12 / 站台照明 03']):
    draw.text((x+30,y+119+i*59),line,font=font(35),fill=(31,42,39))
    if i in (0,4,8):draw.line((x+24,y+169+i*59,x+w-25,y+169+i*59),fill=(109,128,116),width=2)
x,y,w,h=panel('Door');draw.text((x+32,y+25),'货运设备维修与调度工作间',font=font(65),fill=(29,54,51))
draw.text((x+35,y+127),'MAINTENANCE  /  FREIGHT DISPATCH',font=mono(43),fill=(37,53,47))
x,y,w,h=panel('Monitor',(11,25,33));draw.text((x+24,y+19),'FREIGHT OPERATIONS / TERMINAL 02',font=mono(27),fill=(137,202,191))
for i,line in enumerate(['INBOUND   BAY 02   08:40   RECEIVED','OUTBOUND  BAY 04   13:20   LOADING','M-04      MOTOR SERVICE  ISOLATED','C-12      CONVEYOR       HOLD','SHIFT     NIGHT CREW     18:00']):
    draw.text((x+28,y+95+i*56),line,font=mono(25),fill=(165,193,180))
draw.rectangle((x+25,y+393,x+753,y+414),fill=(33,74,65))
x,y,w,h=panel('Map');draw.text((x+25,y+17),'货运作业流线',font=font(40),fill=(29,54,51))
for i,(label,yy) in enumerate([('中转区',130),('物资仓库',130),('站台作业',130)]):
    xx=x+25+i*250;draw.rectangle((xx,y+yy,xx+205,y+yy+105),outline=(35,75,65),width=5)
    draw.text((xx+12,y+yy+31),label,font=font(29),fill=(31,54,46))
    if i<2:draw.line((xx+209,y+yy+51,xx+242,y+yy+51),fill=(35,75,65),width=5)
draw.text((x+30,y+287),'维修间：站台南侧  /  紧急出口保持畅通',font=font(27),fill=(39,54,49))
x,y,w,h=panel('Paper');draw.text((x+23,y+17),'设备维修交接记录',font=font(35),fill=(22,37,31))
for i,line in enumerate(['设备编号  M-04 / 输送电机','故障描述  轴承异响、振动增大','处理内容  断电拆检，更换密封','待办事项  安装端盖，复核间隙','领用备件  6205 轴承 / 油封','交接班组  日班 → 夜班','负责人签名  陈伟    接班：刘强']):
    draw.text((x+22,y+78+i*48),line,font=font(25),fill=(31,39,32));draw.line((x+18,y+118+i*48,x+w-19,y+118+i*48),fill=(142,149,127),width=1)
for key,title,en in [('Label','维修登记 / M-04','SERVICE RECORD | M-04'),('Tools','备件与轴承 / 领用归还','SPARES | RETURN AFTER USE')]:
    x,y,w,h=panel(key);draw.text((x+24,y+17),title,font=font(36),fill=(22,47,40));draw.text((x+24,y+87),en,font=mono(23),fill=(41,55,47))
x,y,w,h=panel('Safety',(224,205,142));draw.text((x+30,y+20),'维修作业安全要求',font=font(47),fill=(47,40,26))
for i,line in enumerate(['1. 停机、断电并挂牌','2. 放空压力后拆卸管路','3. 使用护目镜与防护手套','4. 零件按工单分类摆放','5. 试运行前安装防护罩','6. 严禁在通路存放货物']):
    draw.text((x+30,y+115+i*67),line,font=font(32),fill=(46,44,30))
im.save(ROOT/'Authored/T_Workshop_PrintAtlas.png')
print('STATION_WORKSHOP_LAYOUT_AUTHORED',len(fixed),[len(v['containers']) for v in variants],flush=True)
