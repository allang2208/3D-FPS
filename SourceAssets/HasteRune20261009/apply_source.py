from pathlib import Path
import json,shutil
P=Path(r'D:\FPS3D\FPSGAME\SourceAssets\HasteRune20261009');root=P.parents[1]
def edit(relative,old,new):
    p=root/relative;raw=p.read_bytes();s=raw.decode('utf-8').replace('\r\n','\n')
    if s.count(old)!=1:raise RuntimeError('Source edit anchor changed: '+relative)
    b=P/'Before'/relative;b.parent.mkdir(parents=True,exist_ok=True)
    if not b.exists():shutil.copy2(p,b)
    p.write_bytes(s.replace(old,new,1).replace('\n','\r\n' if b'\r\n' in raw else '\n').encode('utf-8'));print(relative)
edit('Source/FPSGAME/Weapons/MeleeRuneVisual.cpp',
 'VisualRune==TEXT("conduction_rune")?2:-1;',
 '(VisualRune==TEXT("conduction_rune")||VisualRune==TEXT("haste_rune"))?2:-1;')
edit('Source/FPSGAME/Weapons/MeleeRuneVisual.cpp',
 '            const bool Changed=SurfaceMID->K2_GetScalarParameterValue(TEXT("RuneMode"))!=Mode;\n',
 '')
edit('Source/FPSGAME/Weapons/MeleeRuneVisual.cpp',
 '            if(Mode>=0&&(Changed||!SurfaceMID->K2_GetTextureParameterValue(TEXT("RuneTexture"))))',
 '            // Selection changes can share a palette while using a different mask.\n            // Apply runs on assembly/selection; pose updates never reload textures.\n            if(Mode>=0)')
edit('Source/FPSGAME/Weapons/MeleeRuneVisual.cpp',
 '        if(MID->K2_GetScalarParameterValue(TEXT("RuneMode"))!=Mode||!MID->K2_GetTextureParameterValue(TEXT("RuneTexture")))\n        {',
 '        // Refresh the selected mask even when the previous rune used this palette.\n        {')
edit('Source/FPSGAME/Weapons/ModularSwordVisual.cpp',
 '    if(Slot==TEXT("blade_2"))return Factory?TEXT("保留原有刃面纹样"):TEXT("剑刃表面符文");',
 '    if(Slot==TEXT("blade_2")&&Option==TEXT("haste_rune"))return TEXT("疾风折纹 · 冰蓝流光");\n    if(Slot==TEXT("blade_2"))return Factory?TEXT("保留原有刃面纹样"):TEXT("剑刃表面符文");')
option={'id':'haste_rune','name':'急速符文','tier':'common','description':'疾风折纹沿剑脊收束，冰蓝流光向剑尖掠过。','appearance':'疾风折纹 · 冰蓝流光','effects':[{'text':'攻击速度 +10%','benefit':1}],'stats':{'attack_speed_mult':1.1}}
(P/'option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
