"""Record the requested per-entry icon review, including 48/64 px layouts."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent;D=R/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
baseline=json.loads((O/'baseline.json').read_text(encoding='utf-8'));deployment=json.loads((O/'deployment.json').read_text(encoding='utf-8'))
issues={
 2:('ue_super90_optic_false','原图是其他枪型机械瞄具；改为本枪完整鬼环后照门，保留底座与护耳。'),
 10:('ue_super90_muzzle_false','原图是通用消焰器；改为本枪原厂裸枪管及原生前准星。'),
 15:('category_magazine','原分类带减号状态；复用现有无状态标记的共享弹匣代表图。'),
 16:('ue_super90_magazine_false','管式弹仓误用盒式弹匣加减号；改为原厂管体、封帽与原装连接结构。'),
 19:('ue_super90_reargrip_false','原轮廓对应本枪，但简化边框、平涂表面不合格；按真实纹理与统一框重制。'),
 24:('ue_super90_stock_false','原轮廓对应本枪，但简化边框、平涂表面不合格；按独立固定枪托重制，最终保留五个托底孔。'),
 36:('ue_super90_underbarrel_false','原厂护木误用空槽减号；改为原厂长条护木，保留原生防滑槽。'),
 39:('underbarrel_tactical_vertical_foregrip','缺图导致回退普通前握把分类图；把现有 M4 同款供体图提升为共享键，保留真实战术握把轮廓。'),
 43:('ue_super90_reload_device_false','红色禁止标识与铜色弹药违反灰阶规则且语义不清；无速装器模式复用中性减号。')}
rows=[]
for old in baseline['rows']:
    idx=old['index'];row=dict(old);newkey,note=issues.get(idx,(old['key'],'分类使用统一代表图，保留。' if old['kind']=='category' else '无配件使用中性减号，保留。' if old['slot']=='tactical' and old['id']=='false' else '已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。'))
    path=D/(newkey+'.png') if idx in issues else Path(old['path'])
    row.update(final_key=newkey,final_path=str(path),decision='修正' if idx in issues else '保留',note=note)
    if not path.exists():raise RuntimeError('Visible option still has no icon: '+str(path))
    row['final_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    if idx not in issues and row['final_sha256']!=old['sha256']:raise RuntimeError('Unrelated icon changed during review: '+str(path))
    if idx==39:row['effective_before_fallback']=str(D/'category_underbarrel.png')
    rows.append(row)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
changed=[r for r in rows if r['index'] in issues]
sheet=Image.new('RGB',(1140,1140),(36,39,43));draw=ImageDraw.Draw(sheet)
for n,row in enumerate(changed):
    x=(n%3)*380;y=(n//3)*380;im=Image.open(row['final_path']).convert('RGBA');large=im.copy();large.thumbnail((274,274));sheet.paste(large,(x+53,y+4),large)
    for size,offset in [(48,119),(64,187)]:
        thumb=im.resize((size,size),Image.Resampling.LANCZOS);sheet.paste(thumb,(x+offset,y+283),thumb)
    draw.text((x+38,y+350),str(row['index'])+' '+('弹仓分类' if row['kind']=='category' else row['name']),font=font,fill='white')
sheet.save(O/'audit_changed_final.png')
(O/'review.json').write_text(json.dumps(dict(categories=8,options=36,changed=9,retained=35,rows=rows,scope='Requested static per-entry icon review; no game/PIE/UI runtime acceptance'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# SUPER90 改造图标逐项排查与修正（2026-10-16）','',
'依据当前 `gunsmith.json` 专属选项、`common_options` 合并与 `M4GunsmithLayout.cpp` 实际解析顺序，覆盖 **8 个可见分类、36 个选项，共 44 个显示项**。trigger、tactical_secondary、bipod 当前未开放；本枪没有 pistol_grip_surface 追加项。','',
'处理 **9 项**，保留 **35 项**：重制六张原厂实体图；补上逐发装填专属中性状态图；补齐战术垂直握把共享键；修正弹仓共享分类图的不当减号。所有运行 PNG 与九个 UE Texture2D 的保存情况以 `import_receipt.json` 为准。','',
'原厂模型来源为当前 `SK_Super90_V7` 的已有导出和 `Super90CommonStocks20261013/FactoryStock.blend`。作者脚本保留原始 UV 与 WS1 表面配方，只在独立图标场景转换为灰阶。完整后照门不带前准星；枪口选项以完整原厂枪管及其前准星表示。单发装填表示无速装器模式，采用中性减号。','',
'使用内置 imagegen，一项一图。参考、提示词、迭代和成图位于 `SourceAssets/Super90IconReview20261016` 的 `References`、`generation_manifest.json` 和 `Generated`。逐项看过原图与 48/64 像素缩略图；新图也按同样尺寸查看。此处为静态图标排查，不代表游戏内 UI、装配或动作验收。','',
'共享边界：战术垂直握把使用与 SUPER90 制作记录一致的 M4 供体，原有合格图提升到通用键；弹仓分类继续遵守共享分类优先规则，使用现有无状态弹匣代表图，因此其他枪型也显示此共享修正。其他非原厂共享选项继续使用现有成图，不另做武器专属副本。','',
'已替换文件按精确路径归档在 `trash/super90-icons-replaced-20261016/manifest.json`；原厂枪托与后握把的旧制作入口已改为恢复本轮正式母图，避免重跑时退回简化边框。仅修改图标与制作入口，无 C++ 修改，不需要原生构建。未启动编辑器界面、游戏或 PIE，游戏内效果交由用户测试。','',
'|序号|类别|项目|处理|最终加载键|结论|','|---:|---|---|---|---|---|']
for row in rows:lines.append('|'+ '|'.join([str(row['index']),row['slot'],row['name'],row['decision'],'`'+row['final_key']+'`',row['note']])+'|')
(R/'Docs/UI/super90-icons-review-20261016.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('SUPER90_REVIEW_RECORDED',len(rows),'entries;',len(changed),'changed')
