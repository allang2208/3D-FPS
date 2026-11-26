from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BEFORE=ROOT/'SourceAssets/WoodCoreMaterials20261026/Before'
def edit(path,changes):
 p=ROOT/path;s=p.read_text(encoding='utf-8-sig')
 for old,new in changes:
  if s.count(old)!=1:raise RuntimeError(f'{path}: {s.count(old)} occurrences of {old[:100]}')
  s=s.replace(old,new,1)
 b=BEFORE/path;b.parent.mkdir(parents=True,exist_ok=True)
 if not b.exists():b.write_bytes(p.read_bytes())
 p.write_text(s,encoding='utf-8')
edit('Source/FPSGAME/UI/ColdSteelWoodworkingManagementWidget.h',[
('    UFUNCTION() void HandleRecipeSelected', '    UFUNCTION() void HandleCoreSelected(FString Option,ESelectInfo::Type SelectionType);\n    UFUNCTION() void HandleRecipeSelected'),
('    FName ObservedPattern;', '    FName ObservedPattern,ObservedCore;'),
('    UPROPERTY(Transient) TObjectPtr<UTextBlock> QualityBonusValue;', '    UPROPERTY(Transient) TObjectPtr<UTextBlock> QualityBonusValue;\n    UPROPERTY(Transient) TObjectPtr<UTextBlock> MaterialBonusValue;\n    UPROPERTY(Transient) TObjectPtr<UTextBlock> ProcessingBonusValue;\n    UPROPERTY(Transient) TObjectPtr<UTextBlock> CoreInfo;\n    UPROPERTY(Transient) TObjectPtr<UWrapBox> BonusMetrics;\n    UPROPERTY(Transient) TObjectPtr<UComboBoxString> CoreChoice;')])
edit('Source/FPSGAME/UI/ColdSteelWoodworkingManagementWidget.cpp',[
('bool UColdSteelWoodworkingManagementWidget::IsRecipeMenuOpen() const {return RecipeChoice&&RecipeChoice->IsOpen();}', 'bool UColdSteelWoodworkingManagementWidget::IsRecipeMenuOpen() const {return (RecipeChoice&&RecipeChoice->IsOpen())||(CoreChoice&&CoreChoice->IsOpen());}'),
('    Materials=Text(TEXT("所需材料"),14,false,true);', '''    auto* CoreCaption=Text(TEXT("木芯 · 材质保底"),12);CoreCaption->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    Space(RecipeCard->AddChildToVerticalBox(CoreCaption),FMargin(0,4,0,4));
    CoreChoice=WidgetTree->ConstructWidget<UComboBoxString>();
    CoreChoice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::GenerateRecipeOption);
    for(const auto& Core:System->Cores())CoreChoice->AddOption(FString::Printf(TEXT("%s · 保底 %+.0f%%"),*Core.Name,Core.Bonus*100));
    CoreChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleCoreSelected);
    CoreChoice->SetToolTipText(FText::FromString(TEXT("每件额外投入木芯 ×1。原木芯可用 2 木材在普通工作台制作；其他木芯来自探索物资。开工后本件材质锁定。")));
    auto* CoreSize=WidgetTree->ConstructWidget<USizeBox>();CoreSize->SetContent(CoreChoice);ButtonSizes.Add(CoreSize);
    Space(RecipeCard->AddChildToVerticalBox(CoreSize),FMargin(0,0,0,4));
    CoreInfo=Text(TEXT(""),12);CoreInfo->SetAutoWrapText(true);CoreInfo->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Space(RecipeCard->AddChildToVerticalBox(CoreInfo),FMargin(0,0,0,8));
    Materials=Text(TEXT("所需材料"),14,false,true);'''),
('    QualityBonusValue=Text(TEXT(""),12);StateCard->AddChildToVerticalBox(QualityBonusValue);', '''    BonusMetrics=WidgetTree->ConstructWidget<UWrapBox>();StateCard->AddChildToVerticalBox(BonusMetrics);
    QualityBonusValue=Text(TEXT(""),14,false,true);MaterialBonusValue=Text(TEXT(""),12);ProcessingBonusValue=Text(TEXT(""),12);
    for(auto* Value:{QualityBonusValue.Get(),MaterialBonusValue.Get(),ProcessingBonusValue.Get()})BonusMetrics->AddChildToWrapBox(Value);'''),
('if(HasJob&&Job.bFinished&&Job.bPassed)ColdSteelWoodQuality::Apply(Item,Job.Quality);', '''if(HasJob&&Job.bFinished&&Job.bPassed)ColdSteelWoodQuality::Apply(Item,Job);
    else if(!HasJob||Job.QualityVersion>=ColdSteelWoodQuality::Version)
        ColdSteelWoodQuality::Apply(Item,0,System->MaterialBonus(),System->Core(),ColdSteelWoodQuality::Version);'''),
('TEXT("配方基础参数 · 尚未计入木工品质")','TEXT("保底参数 · 已计入材质，加工完成后提升")'),
('    ResultMetrics->SetInnerSlotPadding(FVector2D(12/Scale,4/Scale));', '    ResultMetrics->SetInnerSlotPadding(FVector2D(12/Scale,4/Scale));\n    BonusMetrics->SetInnerSlotPadding(FVector2D(12/Scale,4/Scale));'),
('ItemStyle.SetInactiveBrush(ItemStyle.ActiveBrush);RecipeChoice->SetItemStyle(ItemStyle);', '''ItemStyle.SetInactiveBrush(ItemStyle.ActiveBrush);RecipeChoice->SetItemStyle(ItemStyle);
    CoreChoice->SetWidgetStyle(ComboStyle);CoreChoice->SetItemStyle(ItemStyle);
    CoreChoice->SetContentPadding(FMargin(22/Scale,4/Scale,10/Scale,4/Scale));CoreChoice->SetMaxListHeight(240/Scale);'''),
('if(ObservedPattern!=PatternId||ObservedJobId!=Job.Id', 'if(ObservedCore!=System->Core()||ObservedPattern!=PatternId||ObservedJobId!=Job.Id'),
('{ObservedPattern=PatternId;ObservedJobId=Job.Id;', '{ObservedCore=System->Core();ObservedPattern=PatternId;ObservedJobId=Job.Id;'),
('        RefreshProductPreview();', '''        RefreshProductPreview();
        const int32 CoreIndex=System->Cores().IndexOfByPredicate([this](const auto& C){return C.Id==System->Core();});
        if(CoreChoice->GetSelectedIndex()!=CoreIndex)CoreChoice->SetSelectedIndex(CoreIndex);
        SetText(CoreInfo,Pending&&Job.QualityVersion<ColdSteelWoodQuality::Version?TEXT("旧工件 · 保留原工艺规则，无需补投木芯"):
            FString::Printf(TEXT("木芯保底 %+.0f%% · 加工最高 +15%% · 成品最高 %+.0f%%"),System->MaterialBonus()*100,(System->MaterialBonus()+.15)*100));'''),
('        else if(Recipe)DisplayInputs=Recipe->Inputs;', '        else System->InputsFor(DisplayInputs);'),
('评分决定成品修正：50 分不变，100 分 +25%%，最低 -25%%；弓修正物理伤害，法杖修正本件魔法攻击。', '新工件：木芯保底 0～10%%，加工 0～15%%，合计最高 +25%%；旧工件保留原规则。弓修正物理伤害，法杖修正本件魔法攻击。'),
('    QualityBonusValue->SetVisibility(Finished?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);', '''    const bool ShowBonus=!Finished||Job.bPassed;
    const bool Legacy=Pending&&Job.QualityVersion<ColdSteelWoodQuality::Version;
    QualityBonusValue->SetVisibility(ESlateVisibility::HitTestInvisible);
    MaterialBonusValue->SetVisibility(ShowBonus&&!Legacy?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    ProcessingBonusValue->SetVisibility(ShowBonus?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    ColdSteelCraftingResultStyle::SetBonus(MaterialBonusValue,TEXT("材质"),System->MaterialBonus());
    ColdSteelCraftingResultStyle::SetBonus(ProcessingBonusValue,Legacy?TEXT("旧版工艺"):TEXT("加工"),System->ProcessingBonus());
    const auto PreviewItem=Pending?Job.Item:Recipe?Model->CreateItem(Recipe->Output):FColdSteelItem{};
    ColdSteelCraftingResultStyle::SetBonus(QualityBonusValue,*ColdSteelWoodQuality::StatLabel(PreviewItem),System->MaterialBonus()+System->ProcessingBonus());'''),
('ColdSteelWoodQuality::FromScore(Job.Quality)-1','ColdSteelWoodQuality::FromJob(Job)-1'),
('    RecipeChoice->SetIsEnabled(InputReady', '    CoreChoice->SetIsEnabled(InputReady&&!Preparing&&!Busy&&System->CanSelect());\n    RecipeChoice->SetIsEnabled(InputReady'),
('void UColdSteelWoodworkingManagementWidget::HandleRecipeSelected(', '''void UColdSteelWoodworkingManagementWidget::HandleCoreSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(SelectionType==ESelectInfo::Direct||!System)return;
    auto* Owner=OwnerWidget.Get();const int32 Index=CoreChoice->GetSelectedIndex();
    if(Owner&&Owner->ManagementInputReady()&&!Owner->IsPreparingProject()&&System->Cores().IsValidIndex(Index))
        System->SelectCore(System->Cores()[Index].Id);
    bMaterialsDirty=true;Refresh();SetKeyboardFocus();
}
void UColdSteelWoodworkingManagementWidget::HandleRecipeSelected(''')])
edit('Source/FPSGAME/UI/WoodworkingPanel.inl',[
('PrimaryText.Reset();Motor.Reset();', 'PrimaryText.Reset();Motor.Reset();TotalBonus.Reset();MaterialBonus.Reset();ProcessingBonus.Reset();'),
('        const FString Clock=FString::Printf', '''        auto Bonus=[&](TSharedPtr<STextBlock>& Widget,const TCHAR* Caption,double Value)
        {
            const int32 Rounded=FMath::RoundToInt(Value*10000.);
            Set(Widget,FString::Printf(TEXT("%s %+.2f%%"),Caption,Rounded/100.));
            if(Widget)Widget->SetColorAndOpacity(Rounded>0?ColdSteelUI::Success:Rounded<0?ColdSteelUI::Danger:ColdSteelUI::TextTertiary);
        };
        Bonus(TotalBonus,TEXT("当前加成"),S->MaterialBonus()+S->ProcessingBonus());
        Bonus(MaterialBonus,TEXT("材质"),S->MaterialBonus());Bonus(ProcessingBonus,TEXT("加工"),S->ProcessingBonus());
        const FString Clock=FString::Printf'''),
('        auto Bottom=SNew(SVerticalBox);', '''        auto Bottom=SNew(SVerticalBox);
        Bottom->AddSlot().AutoHeight().Padding(0,0,0,8/Scale)[SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(16/Scale,4/Scale))
            +SWrapBox::Slot()[Dynamic(TotalBonus,16)]+SWrapBox::Slot()[Dynamic(MaterialBonus,14)]+SWrapBox::Slot()[Dynamic(ProcessingBonus,14)]];'''),
('Title,Mode,Time,Clearance,Integrity,Message,PrimaryText,Motor;', 'Title,Mode,Time,Clearance,Integrity,Message,PrimaryText,Motor,TotalBonus,MaterialBonus,ProcessingBonus;')])
print('Woodworking material selection and bonus presentation integrated')
