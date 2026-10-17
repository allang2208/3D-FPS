"""Install this new, isolated art namespace. Leave inventory and loot runtime data untouched."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
def read(p):return json.loads(p.read_text('utf-8-sig'))
models=read(ROOT/'model_manifest.json');assets=read(ROOT/'Receipts/ue-import.json');icons=read(ROOT/'presentation.json')
if assets['stage']!='staged_assets_saved' or icons['stage']!='inventory_icons_saved':raise RuntimeError('Finish authoring/import/icon production before installation')
source=ROOT/'UEImportHost/Content/Items/StaffLivingCollectibles20261016'
targetroot=PROJECT/'Content/Items/StaffLivingCollectibles20261016'
if targetroot.exists():raise RuntimeError('Preserve existing target namespace; do not overwrite')
iconroot=PROJECT/'Content/ColdSteelData/Icons/StaffLivingCollectibles20261016'
if iconroot.exists():raise RuntimeError('Preserve existing production icons')
packages=[]
for p in sorted(source.rglob('*')):
 if p.suffix not in ('.uasset','.ubulk','.uexp'):continue
 target=targetroot/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 packages.append({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
iconroot.mkdir(parents=True)
for row in icons['icons']:
 target=iconroot/Path(row['file']).name;shutil.copy2(row['file'],target);row['installed_file']=str(target)
desc={
 'Perfume':'员工私柜中保存的珍藏香水。厚底玻璃瓶内封存着琥珀色香液，金属泵头藏在烟色瓶盖下，纸质标签保留私人收藏编号。可作为生活区贵重收集物带回出售。',
 'Laptop':'员工私人使用的商务笔记本电脑，阳极氧化外壳上保留完整键盘、触控板及多种接口。屏幕通过双转轴折合，底部仍有设备编号与检修螺钉。可作为电子收集物回收出售。',
 'MusicPlayer':'生活区员工留下的便携音乐播放器，金属外壳内保存着私人曲库。独立音量滚轮、耳机插口和存储卡盖仍保持完整，适合作为个人电子收集物带回出售。',
 'Camera':'员工用于记录日常生活的袖珍数码相机。伸缩镜筒、光学镜片与机械拨轮保存完整，背面留有显示屏和操作按键。可作为贵重摄影设备收集并出售。'}
definitions={}
for key,row in models['assets'].items():
 mesh=next(x['path'] for x in assets['meshes'] if x['item_id']==row['id'])
 icon=next(x['ue_icon'] for x in icons['icons'] if x['id']==row['id'])
 definitions[row['id']]={'id':row['id'],'name':row['name'],'category':'material','type':'生活区收集物','loot_group':'daily_supplies','rarity':row['rarity'],'price':row['value'],'sell_souls':row['value'],'desc':desc[key],'grid_w':row['grid'][0],'grid_h':row['grid'][1],'stack':1,'stack_max':1,'maxStack':1,'inventory_unit':'件','icon':icon,'ue_icon':icon,'world_mesh':mesh,'icon_fallback':row['name']}
(ROOT/'item_definitions.proposed.json').write_text(json.dumps(definitions,ensure_ascii=False,indent=2),encoding='utf-8')
plan={'stage':'proposal_not_installed','equipment_allowed':False,'new_collectibles':list(definitions),'existing_reuse':['mineral_water','soda_can','bread','baguette_bread','raw_sausage','raw_chicken_leg','raw_lamb_ribs','raw_large_lamb','search_usb_drive','search_archive_tape','search_certified_admin_archive','search_encrypted_archive_case','search_hard_disk','search_ssd'],
 'container_groups':[
  {'group':'个人衣柜与更衣柜','entries':36,'content':'饮水、少量食物、香水、播放器、相机；笔记本为稀少贵重物','exclude':'现成服装、鞋、手套、背包及其他可装备物品'},
  {'group':'床头柜','entries':12,'content':'U盘、香水、播放器、相机和饮水'},
  {'group':'书柜与书架','entries':12,'content':'资料载体、档案、个人硬盘和笔记本电脑'},
  {'group':'茶水台储物柜','entries':5,'content':'矿泉水、汽水、普通面包、法棍'},
  {'group':'冰箱冷藏与冷冻室','entries':2,'content':'饮水、汽水、现有肉类食材'}],
 'scope':'Four original non-equipment collectible art assets made first, as requested. Pool probabilities and gameplay registration are not applied in this art stage.'}
(ROOT/'loot_plan.proposed.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
report={'stage':'art_assets_installed','completed_utc':datetime.now(timezone.utc).isoformat(),'packages':packages,'models':models['assets'],'alternate_exports':models['alternate_exports'],'ue_assets':assets['meshes'],'icons':icons['icons'],'source_files_saved':True,'fbx_glb_exported':True,'ue_import_saved':True,'runtime_items_registered':False,'runtime_loot_changed':False,'native_code_changed':False,'native_build_required':False,'interactive_editor_launched':False,'game_run':False,'visual_acceptance':False,'scope':'Precision modeling/material production stage; proposed definitions and revised non-equipment pool plan supplied separately.'}
(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts/installation.json').write_text(json.dumps({'stage':'art_assets_installed','packages':packages,'icons':[r['installed_file'] for r in icons['icons']]},ensure_ascii=False,indent=2),encoding='utf-8')
lines=['生活区私人收集物｜精细模型阶段交付','',
 '本批：珍藏香水、商务笔记本电脑、便携音乐播放器、袖珍数码相机。均为非装备收藏/回收物，生活区方案已去掉服装、鞋、手套、背包等装备。',
 '制作：后台 Blender 精确建模、分件可编辑母版、FBX/GLB、4K BaseColor/ORM/Normal、独立玻璃和液体材质、原创 CS 标识、透明背包图标、UCX 碰撞。',
 '保存：UE 5.8 后台内容宿主导入并保存，已复制到正式 Content/Items/StaffLivingCollectibles20261016/V1。未启动交互编辑器或游戏。',
 '没有运行视觉、性能或主客机测试；模型细节与游戏观感由用户确认。','',
 '模型清单：']
for k,r in models['assets'].items():
 lines.extend([r['name']+'：'+str(r['triangles_lod0'])+' 三角面，'+str(r['source_components'])+' 个可编辑组成对象。','  Blender：'+r['source'],'  FBX：'+r['fbx'],'  GLB：'+r['glb']])
lines.extend(['','笔记本另外交付闭合模型；打开版母版中 EDITABLE_LID_HINGE 控制屏幕，局部 X 旋转 +108 度闭合。','材质：设备主体共用 4K 图集；香水另有瓶壁、香液和烟色瓶盖三个透光材质。UE 采用 Thin Translucent 近似，Blender 源模型用厚度和折射；两者视觉不宣称一致。','不透明设备按导入配方生成 Nanite 数据；香水因含透明材质使用常规静态网格。','',
 '阶段边界：本轮优先完成模型与材质。正式 items.json、scene_search_loot.json、拾取源码和地图没有修改。item_definitions.proposed.json 与 loot_plan.proposed.json 是待接入数据，不是已启用投放。','后续正式投放需完成物品登记、拾取模型分派、Cook 引用及 67 个生活区容器绑定；价格、占格和稀有度在 proposed 文件中属于本批建议。','制作回执：model_manifest.json、presentation.json、Receipts/ue-import.json、Receipts/installation.json、delivery.json。'])
(ROOT/'DELIVERY.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'stage':report['stage'],'packages':len(packages),'models':len(models['assets']),'alternate_meshes':len(models['alternate_exports']),'icons':len(icons['icons']),'report':str(ROOT/'DELIVERY.txt')},ensure_ascii=False))
