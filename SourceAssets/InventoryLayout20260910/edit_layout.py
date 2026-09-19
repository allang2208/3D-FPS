from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/Source/FPSGAME/UI/ColdSteelInventoryWidget.cpp')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('L.GearWidth+2','L.GearWidth+6').replace('Y=28+(N/3)*40','Y=L.GearY+(N/3)*L.GearPitch').replace('L.GearWidth,38','L.GearWidth,L.GearHeight').replace('X+8,Y+10,14','X+8,Y+(L.GearHeight-16)/2,16')
s=s.replace('Label(TEXT("G 切换已装备武器"),FMath::Max(110.f,L.Width-142),6,12,ColdSteelUI::TextSecondary);','')
s=s.replace('12,240,16','12,L.BagY-28,16').replace('FMath::Max(100.f,L.Width-145),242,12','FMath::Max(100.f,L.Width-212),L.BagY-26,12')
s=s.replace('    for(int32 N=0;N<72;', '    Box(L.Width-60,L.BagY-30,48,24,ColdSteelUI::ButtonNormal,ColdSteelUI::Border);Label(TEXT("整理"),L.Width-50,L.BagY-25,12,ColdSteelUI::TextPrimary);\n    for(int32 N=0;N<72;')
s=s.replace('264','L.BagY').replace('float X=12,Y=0,W=48,H=38','float X=12,Y=0,W=48,H=L.GearHeight').replace('Y=28+PreviewCell/3*40','Y=L.GearY+PreviewCell/3*L.GearPitch')
s=s.replace('Label(PreviewReason,12,L.HotY-24','Label(PreviewReason,12,L.HotY+54').replace('Label(InteractionMessage,12,L.HotY-24','Label(InteractionMessage,12,L.HotY+54')
s=s.replace('TEXT("快捷物品 · 拖回背包解绑 / 右键解绑"),12,L.HotY-11,10','TEXT("快捷物品"),12,L.HotY-20,12')
a=s.index('    const auto* SelectedItem=Model->FindItem(Selected);')
b=s.index('    return Layer+3;',a)
s=s[:a]+s[b:]
a=s.index('    if(P.Y>=L.ActionY')
b=s.index('\n',a)
s=s[:a]+'    if(E.GetEffectingButton()==EKeys::LeftMouseButton&&P.X>=L.Width-60&&P.X<L.Width-12&&P.Y>=L.BagY-30&&P.Y<L.BagY-6)PerformAction(3);'+s[b:]
s=s.replace('    if(!Model)return;\n    if(Action==7)', '    if(!Model)return;\n    const auto L=Layout(GetCachedGeometry());\n    if(Action==7)')
p.write_text(s,encoding='utf-8')
# Existing runtime pointer audits must follow the relocated board, not the old hard-coded Y.
root=p.parent
for name in ['ColdSteelInventoryDragAudit.cpp','ColdSteelInventoryAudit.cpp','ColdSteelWarehouseAudit.cpp','ColdSteelItemTooltipAudit.cpp']:
 p=root/name;s=p.read_text(encoding='utf-8-sig')
 if name=='ColdSteelInventoryDragAudit.cpp':
  s=s.replace('264+', 'L.BagY+').replace('FVector2D(20,118)','FVector2D(20,L.GearY+2*L.GearPitch+L.GearHeight*.5f)')
 elif name=='ColdSteelItemTooltipAudit.cpp': s=s.replace('266+','L.BagY+2+')
 else: s=s.replace('266+','Layout.BagY+2+').replace('30+2*40','Layout.GearY+2*Layout.GearPitch+2')
 p.write_text(s,encoding='utf-8')
