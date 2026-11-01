from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np,json,hashlib
P=Path(__file__).resolve().parent;manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'));rows=manifest['parts']
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
sheet=Image.new('RGB',(1560,1120),(32,34,37));draw=ImageDraw.Draw(sheet)
for i,r in enumerate(rows):
 x=(i%3)*520;y=(i//3)*560;draw.text((x+18,y+14),r['name'],font=font,fill='white')
 im=Image.open(P/'Preview'/(r['id']+'_front.png')).convert('RGBA').resize((510,510),Image.Resampling.LANCZOS);sheet.paste(im,(x+5,y+45),im)
x=1040;y=560;draw.text((x+18,y+14),'曲线、倒角与独立法线细节',font=font,fill='white')
im=Image.open(P/'Preview/reinforced_block_detail.png').convert('RGBA').resize((510,510),Image.Resampling.LANCZOS);sheet.paste(im,(x+5,y+45),im);sheet.save(P/'PrecisionSeatsV4.png')
assembly=Image.new('RGB',(1500,2100),(32,34,37));dr=ImageDraw.Draw(assembly)
for i,r in enumerate(rows):
 y=i*420;dr.text((15,y+8),r['name']+' / 原厂锤头与颈部装配',font=small,fill='white')
 for j,v in enumerate(['assembled','detail']):
  im=Image.open(P/'Preview'/(r['id']+'_'+v+'.png')).convert('RGBA');im.thumbnail((720,385),Image.Resampling.LANCZOS);assembly.paste(im,(j*750+(750-im.width)//2,y+33),im)
assembly.save(P/'AssemblyDetailReview.png')
normals=[]
for row in rows:
 n=np.array(Image.open(P/row['textures']['Normal']).convert('RGB')).astype(float)/255*2-1;orm=np.array(Image.open(P/row['textures']['ORM']).convert('RGB'));mask=orm[:,:,0]>245
 normals.append(dict(id=row['id'],file=row['textures']['Normal'],size=[2048,2048],normal_z_mean=float(n[:,:,2][mask].mean()),normal_xy_std=[float(n[:,:,k][mask].std()) for k in [0,1]],normal_length_mean=float(np.linalg.norm(n[mask],axis=1).mean())))
(P/'normal_map_inspection.json').write_text(json.dumps(normals,indent=2),encoding='utf-8')
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8')) if (P/'import_receipt.json').exists() else {}
receipt_matches=bool(receipt.get('complete')) and len(receipt.get('models',[]))==5 and all(hashlib.sha256((P/'Export'/(r['mesh'].rsplit('.',1)[-1]+'.fbx')).read_bytes()).hexdigest()==r['fbx_sha256'] for r in receipt.get('models',[])) and all(hashlib.sha256(Path(r['file']).read_bytes()).hexdigest()==r['sha256'] for r in receipt.get('textures',[]))
published=(P/'publication_receipt.json').exists()
lines=['# 雷神之锤锤座精修 V4','',
'范围：继续精修 V3 的五款锤座，保留原厂圆徽、北欧编纹、左右锤头接口与下方颈部接口。贯雷专属锤座、战斗数值、动作与图标不属于本次修改。','',
'## 发现与修改','',
'- 原有支肋由少量直线段拼接，改为连续采样曲线，圆角截面具有 24 个顶点；端头使用独立倒角，曲线纵向 UV 连续。',
'- 外框沿源表面逐点起伏会产生高光折痕。现先求局部支撑高度的平滑包络，再生成规则截面；曲线背部保留实际厚度，通过紧固脚落到宿主表面，不以深厚平板填满间隙。',
'- 原厂圆徽的正面外沿约为 105×82 mm，旧饰圈按正圆制作导致上下悬空。新饰圈采用与原厂纵横比例对应的椭圆路径。',
'- 紧固件改为 60 段圆周的沉头螺钉，制作真实六角内孔、孔壁、底面和锥形紧固脚；摆放高度读取实际支肋前表面，底部读取原厂承力面。',
'- 缓冲座保留三片曲面叠层及两层内缩垫片；轻型座分叉末端衔接已有主肋。古印闭合环使用周期曲线，避免起止点形成尖折。',
'',
'## 法线与材质','',
'每款新增硬件均独立展开并烘焙 2048×2048 BaseColor、ORM、Normal，共 15 张贴图。法线来自沿部件曲线排列的浅刻线和细加工纹理，采用 Cycles 材质凹凸烘焙；不是高模雕刻投射，也不再套用通用钢材法线。主要轮廓、厚度、倒角与螺孔由真实几何承担。',
'',
'原厂主表面继续使用原有 PBR 和法线。新增贴图在 UV0 上独立占区；FlowUV 保留为作者的纵向细节参数域。Blender 法线为 OpenGL 切线空间；UE 导入使用 TC_NORMALMAP、sRGB=false、flip_green_channel=true，保留 mip 与流送。',
'',
'## 模型与保存','',
'| 型号 | 原厂三角面 | 新版总三角面 | 原厂法线最大差 |','|---|---:|---:|---:|']
for r in rows:lines.append(f"| {r['name']} | {r['native_triangles']} | {r['triangles']} | {r['native_normal_error']} |")
lines += ['',
'所有原厂顶点、UV 和法线均保留。新增网格未跨越左右安装切面和下方颈部切面；新增密度用于曲线、圆角和内孔。沿用既有 Nanite 与完整 fallback；没有进行性能采样，不宣称帧率提升。',
'',
'## 局部切线处理与边界','',
'初次导入出现近零切线提示。已减少小紧固件的倒角宽度，并在加权法线前清理重复点和退化边。原厂接口自身的微细长三角形保留原形、原 UV 和原法线。最终导入保留法线，由 UE 重新生成 Mikk 切线，启用完整精度 UV、高精度切线基和 Nanite explicit tangents。',
'',
'离线 Blender 检查仍能在原厂接口的 5 个面角及部分新增微小倒角上得到零切线；叠片座有 1 个面积小于 1e-14 平方米的微小面。详细计数见 tangent_inspection.json。本轮没有把这些报告为完全清零；它们的 Blender 导出切线不用于最终 UE 构建。',
'',
'最终后台导入已完成；import-engine.log 中未再出现近零切线或退化切线警告，进程以 0 退出。该结果只覆盖资产导入和保存，不代替游戏内的光照、动作和性能验收。',
'',f"当前最终源文件对应的 UE 导入保存完成：{receipt_matches}；回执中模型 {len(receipt.get('models',[]))}/5、贴图 {len(receipt.get('textures',[]))}/15；模块引用已切换：{published}。",
'',
'本轮按用户要求查看了五款正面、斜侧近景及与原厂锤头/颈部的装配渲染，修正了检查中暴露的折痕、深厚补片和饰圈离体问题。图像均为实际 Blender 源模型；未启动 UE 图形编辑器或游戏，未进行实战验收。',
'',
'- 作者源：ThorSeatsPrecisionV4.blend、author_precision.py（保留隐藏的 AUTHOR_* 硬件和程序材质）。',
'- 导出：Export/；贴图：Textures/。',
'- 预览：PrecisionSeatsV4.png、AssemblyDetailReview.png。',
'- 引擎保存：import_receipt.json；配方切换和旧值：publication_receipt.json、Backups/。',
'']
(P/'README.md').write_text('\n'.join(lines),encoding='utf-8')
print('PRECISION_REPORT_SAVED')
