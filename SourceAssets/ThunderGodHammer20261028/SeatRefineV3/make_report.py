"""Write the requested scoped audit and actual-model comparison, without gameplay testing."""
from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
import json
P=Path(__file__).resolve().parent
models=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))['parts']
rows=[dict(mesh='SM_ThunderGodHammer_head_mount_factory',name='原厂锤座')]+models
out=Image.new('RGB',(1650,1130),(33,35,38));draw=ImageDraw.Draw(out);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
for i,r in enumerate(rows):
 x=i%3*550;y=i//3*565;draw.text((x+20,y+15),r['name'],font=font,fill=(225,228,230))
 im=Image.open(P/'Preview'/(r['mesh']+'.png')).convert('RGBA');im.thumbnail((530,510),Image.Resampling.LANCZOS);out.paste(im,(x+(550-im.width)//2,y+50),im)
out.save(P/'SeatComparisonV3.png')
icons=json.loads((P/'icon_audit.json').read_text(encoding='utf-8'))
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
publication=json.loads((P/'publication_receipt.json').read_text(encoding='utf-8')) if (P/'publication_receipt.json').exists() else {}
lines=['# 雷神之锤：改造图标排查与原厂衍生锤座 V3','',
'## 范围与结论','',
'本轮仅覆盖雷神之锤工作台。按运行代码合并私有与公共选项，核对 5 个分类、5 个原装/无符文项、22 个改造/拆除项，共 32 个 PNG 键、26 张独立母图。战锤属于近战工作台，不属于采集工具工作台，因此没有额外的工具强化分类。', '',
'32 个入口均能解析到实际 PNG，没有缺图回退。图像采用厚倒角金属方框、四角铆钉、银色内环和深灰底板；分类与原装实体、符文主标记、拆除减号均对应正确。已查看全部图标总览和 48/64 像素版本。长握把缩小时较细，但保留真实比例，未人为加粗。','',
'严格灰阶并非全部达标：现成母图的金属边框仍有轻微青灰反光，少量图像主体也存在低幅色差；框内 alpha 存在 248–255 的轻微波动。它们沿用现有获认可母图，本轮没有重新生成 PNG，也不将视觉近灰等同于逐像素纯灰、不透明。各图的色差和 alpha 数据见 icon_audit.json。','',
'补齐缺失的 UE 纹理副本：head_mount_ancient_breaking_seal_seat、head_mount_storm_drive_seat。另外修正了符文分类与“无附加符文”两张既有纹理的 UI 组和 NeverStream。所有 32 张纹理逐一读取 UI 组、EditorIcon 压缩、sRGB、NeverStream 和无 mipmap 设置。最终保存状态见 import_receipt.json。','',
'通用改造依照共享图标规则继续引用公共母图。本轮只是雷神宿主造型适配，不改变其他武器的共享母图或模型。原厂与贯雷专属图保持原有解析键。','',
'## 五款锤座','',
'从 ModulesV1/ThunderGodHammer_Modular_Editable.blend 的原厂锤座直接复制完整网格。每款保留原来的 132666 个三角面、全部原生 UV 与自定义法线；新结构添加在两面外围，不用平板替换圆徽和北欧编纹。左右锤头接口与下端颈部切面未改。','',
'| 改造 | 造型变化 | 三角面 |','|---|---|---|']
for r in models:lines.append(f"| {r['name']} | {r['appearance']} | {r['triangles']} |")
lines += ['',
'新增金属件使用独立材质引用现有钢材 PBR 贴图，并减弱法线起伏；原厂主材质不变。各款启用 Nanite 和显式切线，保留完整 fallback。新件使用 SteelUV 通道，原厂使用原来的 UVMap；导出前将新增面显式三角化。未修改攻击、投掷、召回、伤害、属性数值或贯雷锤座。', '',
'鸣雷疾驱仍保留原网格叶名称 SM_ThunderGodHammer_head_mount_storm_drive_seat，新版本只改变目录，兼容现有按名称查找的电弧挂点逻辑。','',
'## 落盘状态','',
f"- UE 导入保存完成：{receipt['complete']}；模型 {len(receipt['models'])}/5；图标纹理设置读取 {len(receipt['icons'])}/32。",
f"- 模块配方切换完成：{bool(publication)}。仅更改 head_mount 中五个普通/特殊改造条目的 mesh、appearance、model_revision、source_mesh。",
'- 实际模型对比：SeatComparisonV3.png；可编辑场景：ThorFactoryDerivedSeatsV3.blend；FBX：Export/。',
'- 完成用户要求范围内的图标审查、模型制作与离线对比；没有启动 UE 图形编辑器、游戏或 PIE，没有进行实战验收。',
'- 本轮无 C++ 修改，无需重编 DLL。',
'']
(P/'README.md').write_text('\n'.join(lines),encoding='utf-8')
print('REPORT_AND_COMPARISON_SAVED')
