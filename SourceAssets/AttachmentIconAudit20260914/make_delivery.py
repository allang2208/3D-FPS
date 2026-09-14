import json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;R=P.parents[1];O=P/'Icons';report=json.loads((P/'audit_report.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21)
def sheet(entries,path,cols=5):
 width=cols*300;height=math.ceil(len(entries)/cols)*305;out=Image.new('RGB',(width,height),(29,35,41));draw=ImageDraw.Draw(out)
 for i,(label,file) in enumerate(entries):
  im=Image.open(file).convert('RGBA');im.thumbnail((274,248));x=i%cols*300;y=i//cols*305
  out.paste(im,(x+(300-im.width)//2,y+8+(248-im.height)//2),im)
  draw.text((x+150,y+267),label,font=font,fill=(226,232,236),anchor='mt')
 out.save(path)
irons=[('M4A1','optic_false'),('AKM','ue_akm_optic_false'),('QBZ-191','ue_qbz191_optic_false'),('M1911','ue_m1911_optic_false'),('Dan-Wesson 715','ue_dan_wesson715_optic_false')]
sheet([(label,O/(key+'.png')) for label,key in irons],P/'iron_sights.png')
keys=['optic_false','optic_holographic','optic_panoramic_red_dot','optic_prism_scope_2x','optic_lpvo_1_6x','muzzle_false','muzzle_true','muzzle_tactical_suppressor','muzzle_brake','muzzle_titanium_brake','reargrip_false','reargrip_phantom_reargrip','reargrip_stable_antislip_reargrip','reargrip_balanced_reargrip','tactical_flashlight','underbarrel_canted_foregrip','underbarrel_vertical_foregrip','underbarrel_prism_handstop','underbarrel_angled_foregrip','tactical_laser']
names={r['slot']+'_'+r['id']:r['name'] for r in report['options'] if r['weapon']=='ue_m4a1'}
sheet([(names[k],O/(k+'.png')) for k in keys],P/'attachment_overview.png')
labels={'optic':'瞄具','muzzle':'枪口','magazine':'弹匣','underbarrel':'下挂','barrel':'枪管','reargrip':'后握把','stock':'枪托','trigger':'扳机','tactical':'战术挂件','reload_device':'装填器'}
sheet([(label,O/('category_'+key+'.png')) for key,label in labels.items()],P/'category_overview.png')
counts={}
for row in report['options']:counts[row['weapon_name']]=counts.get(row['weapon_name'],0)+1
readme='''# 改造配件图标全面审计与更新 — 2026-09-14

用户已接受的枪托规则推广至所有改造配件图：当前实际模型、枪械前方朝左、相机水平、单件展示、1024 × 1024 RGBA 透明背景。机械瞄具改成每把枪的一个完整后照门，保留属于该照门的固定底座；游戏内前后机瞄不变。

## 覆盖范围

按 `GunsmithSystem.cpp` 合并武器选项和 `common_options`，覆盖 5 把枪、124 个改造选项，最终解析到 74 个选项图文件。分类入口另行覆盖 10 类，以及不同枪型的原厂分类图。

| 武器 | 可见改造选项 |
|---|---:|
'''+''.join(f'| {name} | {count} |\n' for name,count in counts.items())+'''
原目录 31 张 PNG：5 张已接受的枪托图逐字节保留，26 张替换；新增 73 张配件、默认状态、枪型覆盖及分类图，共 104 张 PNG。实际重新渲染 55 个物理配件视图和 1 个中性空槽符号；43 个文件为明确登记的分类／数值改造复用，不计作新的模型。

## 发现与处理

| 发现 | 处理 |
|---|---|
| 机瞄同时出现前后两件 | 每枪一个后照门；M4、QBZ 的活动头与固定底座合成同一个机瞄图 |
| 大量旧图为倾斜概念图、带实心黑底，和现有造型不对应 | 由当前实际源模型重新水平左向渲染，孔洞保留透明 |
| 不同枪型的原厂配件误用 M4 图 | 新增武器专属图，UI 优先读取专属文件；缓存按实际图标键保存 |
| M1911、715 快扳机使用完全相同的旧图片 | 分别使用对应手枪的真实扳机 |
| 6 类共享图标缺失，影响 25 个选项 | 补齐标准枪管、原厂扳机、均衡后握把及无挂件／激光／手电图，不再靠分类图代替 |
| 分类图仍为旧概念造型和黑底材质处理 | 改成相同规则的透明实物图；旧资源保留作为兼容回退 |
| 中间 FBX 丢失材质常量，连接座或聚合物变白 | 图标源场景按当前材质导入规则补回涂层贴图及聚合物设置；不修改游戏材质 |
| 拆件后索引变化、源场景混有旧参考件 | 按当前几何重建选择；排除枪体、手臂和参考模型，补齐目标自身的底座 |
| 手枪局部瞄具骨骼 Z 轴与枪械上方不一致 | 使用作者确定的根坐标、枪口方向与上向，修正枪管等图标的横竖方向 |

## 有意复用与呈现限制

- 短／长枪管和轻量快扳机目前只改变数值，未在运行代码中替换为独立网格。图标使用该枪实际零件，名称和属性区分数值；没有虚构新的枪管或扳机模型。
- 共享步枪附件图采用当前 M4 版本作为代表；细小的枪型安装座和涂层差异沿用代表图。原厂件轮廓差异与手枪紧凑适配件已有专属覆盖。
- 水平是枪械基准轴，握把、弹匣保持安装时的竖向；侧视下圆形部件可能呈窄轮廓。这是当前模型的投影，不把零件翻倒或镜像来改变形状。
- Blender 棚拍照明与游戏光照不同。M4 的 UE Phong 着色转换采用同一涂层源贴图近似呈现；未宣称与游戏逐像素一致。

## 交付与接入

公开源码的资产恢复与脚本使用边界见 [发布说明](../../Docs/Weapons/attachment-icons-publication-20260914.md)。以下审计与构建是 2026-09-14 制作阶段的记录，本次整理没有重新运行游戏或渲染。

- 本机预览（未公开入库）：`iron_sights.png`（机瞄）、`attachment_overview.png`（主要配件）、`category_overview.png`（分类图）。所有物理视图与 64 像素缩略图的人工复核联系图保存在 `after_icons_1.png` 至 `after_icons_5.png`。
- `source_paths.json` 与 `frame_reference.json` 保留重建所需的源路径及 M4 安装朝向；`render_manifest.json` 记录每张图的源场景、对象／面选择、坐标转换及复用关系；`Icons/*.json`：渲染来源及相机记录；`Icons/*.blend`：可编辑场景。
- `audit_report.json`：124 个选项的实际解析路径、104 张图的尺寸／透明／边距／哈希、替换清单和复用依据。
- 改动前副本及诊断中间件已归档到本机 `trash/AttachmentIconAudit20260914/`，逐文件路径及 SHA-256 见 `Docs/AssetArchives/attachment-icons-20260914.json`。
- 实际资源目录：`Content/ColdSteelData/AttachmentIcons20260913`。PNG 同步后再批量导入同名 UE Texture；回执为 `import_receipt.json`。
- 加载代码：`Source/FPSGAME/UI/M4GunsmithLayout.cpp`，包含武器覆盖解析及透明分类图加载；使用已存在的 UFS 打包目录。
- 标准同步至个人技能和工程镜像：`ue5-weapon-workflow/references/attachment-icons.md`，并从枪械 SKILL、配件标准和通用模型 SKILL 链接。

本轮完成用户指定的图标来源、覆盖、画面和缩略图审计。没有运行 PIE、枪械数值或存档回归；由用户在游戏中测试。原生构建状态另见 `completion.json`，不能用贴图导入成功替代代码构建或游戏验收。
'''
(P/'README.md').write_text(readme,encoding='utf-8')
print('DELIVERY_REPORT_READY',counts)
