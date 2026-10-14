from pathlib import Path

root = Path('D:/FPS3D/FPSGAME')
path = root / 'Source/FPSGAME/UI/ColdSteelEnhancementLayout.cpp'
source = path.read_text(encoding='utf-8-sig')
start = source.index('    auto Stage=SNew(SOverlay)')
end = source.index('    PreviewSurface=SNew(SM4PreviewSurface)', start)
stage = '''    auto StageHeader=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SAssignNew(OperationBadge,STextBlock)
            .Font(GunsmithUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::Enhanced)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)[SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SAssignNew(ItemTitle,STextBlock).Font(GunsmithUI::TextFont(20,true))
                    .ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)[SAssignNew(ItemLevel,STextBlock).Font(GunsmithUI::TextFont(12))
                    .ColorAndOpacity(ColdSteelUI::TextSecondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SAssignNew(LevelBadge,STextBlock).Font(GunsmithUI::NumberFont(28,true))
                    .ColorAndOpacity(ColdSteelUI::Enhanced)]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SAssignNew(LevelMax,STextBlock)
                    .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextTertiary)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SAssignNew(LevelTrack,SHorizontalBox)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SAssignNew(AffixRow,SHorizontalBox)];
    auto Stage=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&Background)]]
        +SOverlay::Slot()[SNew(SSimpleGradient).StartColor(ColdSteelUI::Gray(8,210)).EndColor(ColdSteelUI::Gray(8,15)).Orientation(Orient_Vertical)]
        +SOverlay::Slot().Padding(12,94,12,48)[SAssignNew(RitualSeal,SColdSteelArcaneSeal)]
        +SOverlay::Slot().Padding(16,130,16,74)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(WorkbenchPreview->StandaloneBrush())
            .Visibility_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture()?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]
        +SOverlay::Slot().Padding(42,138,42,82)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage)
            .Image_Lambda([this](){return &WeaponBrush;})
            .Visibility_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})]]
        +SOverlay::Slot().VAlign(VAlign_Top).Padding(18)[StageHeader]
        +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(14)[SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SAssignNew(OutcomeText,STextBlock)
                .Font(GunsmithUI::TextFont(14,true)).ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
            +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,8,0)
                    [Label(TEXT("拖动旋转 · 滚轮缩放"),12,ColdSteelUI::TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,4,0)[SNew(SBox).WidthOverride(80)[ResetViewControl.ToSharedRef()]]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(80)[AimViewControl.ToSharedRef()]]]]
        +SOverlay::Slot()[SAssignNew(FlashOverlay,SBorder).BorderImage(&FlashBrush)
            .Visibility(EVisibility::Collapsed)];
'''
source = source[:start] + stage + source[end:]
path.write_text(source,encoding='utf-8')
