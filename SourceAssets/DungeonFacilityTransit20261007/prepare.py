"""Authoring data and original, aspect-preserved facility wayfinding artwork."""
from pathlib import Path
import json,math,shutil
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
refined=ROOT/'RefineV2'
if __name__=='__main__' and (refined/'Receipts/install.json').exists() and json.loads((refined/'Receipts/install.json').read_text('utf8')).get('stage')=='maps_saved':
 import runpy
 runpy.run_path(str(refined/'prepare.py'),run_name='__main__')
 raise SystemExit(0)
BASE='/Game/Dungeons/FacilityTransit20261007'
for p in ('Authored/Textures','Config','Scripts','Receipts'):(ROOT/p).mkdir(parents=True,exist_ok=True)
def write(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
shutil.copy2(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts/geometry.py',ROOT/'Scripts/geometry.py')
roles=json.loads((PROJECT/'SourceAssets/DungeonReceptionHall20261006/Config/materials.json').read_text('utf8'))
for r in roles.values():r['new_authored']=False
roles['Wood']['existing_ue_path']='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Materials/M_RH2_Wood'
themes=[
 dict(id='freight',cn='货运车站区',en='FREIGHT TRANSIT',code='FR',color=[73,105,123],paint=[.10,.16,.20],detail='货运 / 调度 / 仓储',notice='注意牵引车辆 · 沿人行标线通行',language='blue steel portal, dock bumpers, cargo-scale ribs and roller-shutter cassette'),
 dict(id='medical',cn='医疗隔离区',en='MEDICAL ISOLATION',code='MD',color=[105,160,158],paint=[.24,.42,.40],detail='诊疗 / 隔离 / 检验',notice='保持清洁 · 遵守隔离区域通行规程',language='ivory tiled jambs, stainless kickplates, filtered-air plenum and clean seal trims'),
 dict(id='treatment',cn='焚化通风区',en='THERMAL TREATMENT',code='TR',color=[177,104,49],paint=[.36,.15,.055],detail='焚化 / 排烟 / 净化',notice='高温设备 · 进入前领取防护用品',language='charcoal heat shields, burnt orange ribs, insulated extraction duct and hazard bollards'),
 dict(id='staff_living',cn='员工生活区',en='STAFF QUARTERS',code='ST',color=[151,134,92],paint=[.25,.22,.13],detail='宿舍 / 更衣 / 休憩',notice='请保持安静 · 访客须由工作人员陪同',language='warm timber wall panels, olive frame, staff notice board and gentle wall lighting'),
 dict(id='ecology',cn='生态实验区',en='ECOLOGY LABORATORY',code='EC',color=[92,143,83],paint=[.13,.26,.10],detail='培育 / 循环水 / 生物圈',notice='样本限制带出 · 注意湿滑地面',language='sage frame, twin water risers, gauges, irrigation valve station and washable wall panels'),
 dict(id='power',cn='发电配电区',en='POWER GENERATION',code='PW',color=[198,164,62],paint=[.42,.30,.06],detail='开关设备 / 发电 / 总控',notice='高压危险 · 禁止触碰带电设备',language='graphite frame, ochre safety ribs, overhead cable trays, ceramic insulators and isolator box')]
for t in themes:
 roles[t['code']]=dict(basecolor_linear=t['paint'],roughness=.55,metallic=.13,uv_meters=1,existing_ue_path=BASE+'/Materials/M_FT_'+t['code'],new_authored=True)
roles['Labels']=dict(basecolor_linear=[.2,.3,.25],roughness=.75,metallic=0,uv_meters=1,existing_ue_path=BASE+'/Materials/M_FT_Labels',new_authored=True)
roles['Ceramic']=dict(roles['White']);roles['Copper']=dict(roles['Brass'])
write('Config/materials.json',roles)
# Three card formats, each retains its own printed aspect; no atlas stretching.
cards=[]
for t in themes:
 cards.extend([(t['id'],t['cn'],t['en'],t['detail'],t['color'],t['code']),
               (t['id']+'_notice','区域通行须知',t['en']+' / ACCESS',t['notice'],t['color'],t['code'])])
cards.extend([
 ('welcome','设施内部中转厅','FACILITY TRANSFER CONCOURSE','请按当前通道示牌前往指定区域',[157,157,131],'02'),
 ('return','接待大厅 · 返回','RETURN TO RECEPTION','访客登记 / 安检 / 接待服务',[157,157,131],'←'),
 ('route1','01  主题通道','ROUTE 01','目的地区域以入口主题标识为准',[157,157,131],'01'),
 ('route2','02  主题通道','ROUTE 02','目的地区域以入口主题标识为准',[157,157,131],'02'),
 ('route3','03  主题通道','ROUTE 03','目的地区域以入口主题标识为准',[157,157,131],'03'),
 ('duty','通行调度室','ACCESS COORDINATION','当班值守 / 通道引导 / 应急联络',[157,157,131],'02'),
 ('ppe','防护用品领取','PERSONAL PROTECTIVE EQUIPMENT','按目的区域要求领取用品',[157,157,131],'P'),
 ('brief','设施区域导览','FACILITY AREA GUIDE','货运 · 医疗 · 焚化 · 生活 · 生态 · 发电',[157,157,131],'i'),
 ('service','设备与维护','MAINTENANCE ACCESS','检修工具 / 通信 / 消防设施',[157,157,131],'M'),
 ('balcony','二层观察平台','UPPER OBSERVATION GALLERY','注意台阶 · 扶稳扶手',[157,157,131],'↑'),
 ('rules','内部通行制度','INTERNAL ACCESS PROCEDURE','佩戴证件 / 遵从引导 / 保持通道畅通',[157,157,131],'i'),
 ('closed','通道样板终点','END OF SUBJECT CORRIDOR','主题房间在正式接入阶段连接',[157,157,131],'—')])
im=Image.new('RGB',(4096,4096),(25,33,33));d=ImageDraw.Draw(im);rects={}
def font(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def fitted(s,n,maxw):
 while d.textbbox((0,0),s,font=font(n))[2]>maxw:n-=1
 return font(n)
for i,(key,title,en,sub,color,code) in enumerate(cards):
 x=16+(i%4)*1024;y=16+(i//4)*512;w=992;h=448;rects[key]=[x,y,x+w,y+h]
 d.rectangle((x,y,x+w-1,y+h-1),fill=(25,39,37),outline=(125,137,124),width=3)
 d.rectangle((x+18,y+18,x+162,y+h-18),fill=tuple(color))
 d.text((x+40,y+184),code,font=fitted(code,62,110),fill=(236,233,215))
 d.text((x+188,y+50),title,font=fitted(title,67,w-228),fill=(232,231,211))
 d.text((x+192,y+180),en,font=fitted(en,31,w-228),fill=(178,202,187))
 d.line((x+192,y+258,x+w-40,y+258),fill=tuple(color),width=3)
 d.text((x+192,y+303),sub,font=fitted(sub,34,w-228),fill=(205,213,197))
im.save(ROOT/'Authored/Textures/T_FT_Wayfinding.png');write('Config/atlas.json',dict(size=list(im.size),rects=rects))

parts=[];containers=[];lights=[]
def part(id,mesh,pos,yaw=0,anchor=(0,0,0),collision=True):
 a=math.radians(yaw);x,y,z=anchor
 parts.append(dict(id=id,mesh=mesh,position_m=[pos[0]-x*math.cos(a)+y*math.sin(a),pos[1]-x*math.sin(a)-y*math.cos(a),pos[2]-z],yaw_deg=yaw,scale=[1,1,1],collision=collision,cast_shadow=True))
furniture='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/'
for j,y in enumerate((-7.2,-3.6)):
 for name,file,col in [('Desk','SM_SW_DispatchDesk',True),('PC','SM_SW_DispatchElectronics',False),('Paper','SM_SW_DispatchPaper',False)]:
  part('Duty'+name+str(j),furniture+file,[-23.05 if name!='PC' else -23.12,y,4.2],90,(6.1,-.72,0),col)
 part('DutyChair'+str(j),furniture+'SM_Staff_Chair',[-21.8,y,4.2],-90)
for j,y in enumerate((5.0,9.0)):
 part('UpperSofa'+str(j),furniture+'SM_RH2_Sofa',[-23.0,y,4.2],90)
 part('UpperTable'+str(j),furniture+'SM_Staff_CoffeeTable',[-21.55,y,4.2],90)
for j,y in enumerate((-11,-7,7,11)):
 part('GroundBench'+str(j),furniture+'SM_Staff_ChangingBench',[-22.95,y,0],90)
for j,x in enumerate((-2,1)):
 part('PPEBench'+str(j),furniture+'SM_Staff_ChangingBench',[x,15.7,0])
part('Water','/Game/Dungeons/StaffLiving20261002/RoomDetailsV5/Meshes/SM_Staff_WaterDispenser_V5',[-23.35,12.8,4.2],90)
proto=json.loads((PROJECT/'SourceAssets/IncineratorContainers20261003/Config/assemblies.json').read_text('utf8'))
for j,x in enumerate((-3.5,-2.6,-1.7,-.8,.1,1.0)):
 p=dict(proto['prototypes']['PPELocker']);p.update(id='PPE'+str(j),caption='中转厅 · 防护用品 '+str(j+1),position_m=[x,17.48,0],yaw_deg=0);containers.append(p)
for j,y in enumerate((-9.2,-1.4)):
 pos=[-23.4,y,4.2];part('RecordsBody'+str(j),proto['assemblies']['RecordsCabinet']['static_parts'][0]['mesh'],pos,-90)
 for k,z in enumerate((.11,.45,.79)):
  p=dict(proto['prototypes']['RecordsDrawer']);p.update(id='Records'+str(j)+str(k),caption='区域通行记录',position_m=[pos[0],pos[1],pos[2]+z],yaw_deg=-90);containers.append(p)
for j,x in enumerate((-2,1)):
 p=dict(proto['prototypes']['ToolBox']);p.update(id='Tool'+str(j),caption='中转厅检修工具',position_m=[x,-17.2,.85],yaw_deg=180);containers.append(p)
for x in (-12,0,13):
 for y in (-10,0,10):lights.append(dict(id=f'Atrium_{x}_{y}',position_m=[x,y,6.75],intensity=7800,radius=13,cast_shadows=x==0,type='spot',outer_cone_degrees=76,inner_cone_degrees=55,role='Main'))
for y in (-12,-5,6,13):
 lights.append(dict(id='UnderGallery'+str(y),position_m=[-20,y,3.63],intensity=2200,radius=5,cast_shadows=False,type='point',role='Local'))
 lights.append(dict(id='Gallery'+str(y),position_m=[-21,y,7.45],intensity=2400,radius=5.5,cast_shadows=False,type='point',role='Local'))
for x in (-29,-25.6):lights.append(dict(id='Approach'+str(x),position_m=[x,0,2.72],intensity=1500,radius=4.5,cast_shadows=False,type='point',role='Local'))
doors=[dict(id='DutyDoor',position_m=[-19.2,-.8,4.2],yaw_deg=0,positive_hinge=False,leaf_mesh='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/SM_SW_PersonnelLeaf')]
glass=[dict(id='DutyGlass'+str(j),position_m=[-19.2,y,6.15],yaw_deg=0,width_m=2.60,height_m=1.8,glass_kind='Duty') for j,y in enumerate((-8.4,-5.6,-2.8))]
ports=[dict(id='arrival',position=[-32,0,0],normal=[-1,0,0],width=3,height=3),
 dict(id='Route1',position=[28,0,0],normal=[1,0,0],width=3,height=2.8),dict(id='Route2',position=[8,22,0],normal=[0,1,0],width=3,height=2.8),dict(id='Route3',position=[8,-22,0],normal=[0,-1,0],width=3,height=2.8)]
cfg=dict(id='FacilityTransit',revision='20261007-v1',base=BASE,map='/Game/GameMaps/Design/L_FacilityTransit_Subject',alternate_map='/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject',
 reception_source='/Game/GameMaps/Design/L_ReceptionHall_Subject',offset_m=[59,0,0],dimensions_m=[48,36,8.4],parts=parts,containers=containers,lights=lights,doors=doors,glass=glass,ports=ports,
 gates=[dict(route='Route1',position_m=[24,0,0],yaw_deg=-90),dict(route='Route2',position_m=[8,18,0],yaw_deg=0),dict(route='Route3',position_m=[8,-18,0],yaw_deg=180)],
 preview_sets=[['freight','medical','treatment'],['staff_living','ecology','power']],themes=themes,production_registered=False,tests_run=False,rendered=False)
import runpy
cfg=runpy.run_path(str(PROJECT/'SourceAssets/HallLighting20261007/profile.py'))['revise_layout'](cfg,'Transit')
write('Config/layout.json',cfg)
print('FACILITY_TRANSIT_AUTHORING_DATA_SAVED',len(parts),'reuse placements',len(themes),'portal families')
