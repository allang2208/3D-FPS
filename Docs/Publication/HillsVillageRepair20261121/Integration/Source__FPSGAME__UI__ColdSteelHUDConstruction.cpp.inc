// Source/FPSGAME/UI/ColdSteelHUDConstruction.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 103-119 | void UColdSteelHUDWidget::BuildInteractHint(UCanvasPanel* Root)
    auto* Content=WidgetTree->ConstructWidget<UVerticalBox>();
    Surface->SetContent(Content);
    InteractHintTitle=MakeReferenceText(FString(),15,ColdSteelUI::NoticeGold,false,true);
    InteractHintTitle->SetAutoWrapText(false);
    InteractHintTitle->SetVisibility(ESlateVisibility::Collapsed);
    auto* TitleSlot=Content->AddChildToVerticalBox(InteractHintTitle);
    TitleSlot->SetPadding(FMargin(0,0,0,ReferenceUnits(2)));
    auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();
    Content->AddChildToVerticalBox(Row);
    InteractHintKey=MakeReferenceText(TEXT("E"),16,FLinearColor::White,true,true);
    auto* KeySlot=Row->AddChildToHorizontalBox(InteractHintKey);
    KeySlot->SetPadding(FMargin(0,0,ReferenceUnits(9),0));
    KeySlot->SetVerticalAlignment(VAlign_Center);
    InteractHintText=MakeReferenceText(FString(),15,FLinearColor::White);
    InteractHintText->SetAutoWrapText(false);
    auto* TextSlot=Row->AddChildToHorizontalBox(InteractHintText);
    TextSlot->SetVerticalAlignment(VAlign_Center);

// Lines 149-157 | void UColdSteelHUDWidget::UpdateInteractHint()
    const bool bWorldInteraction=Character&&!IsWorldForging()&&!IsGunAssembly()&&!bInventoryOpen&&!bWarehouseOpen&&!PC->bShowMouseCursor&&!Character->IsAmmoWheelOpen();
    const bool bOrdinaryUse=bWorldInteraction && !PC->IsInBuildMode();
    const auto* PlayerHealth=Character?Character->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const bool bDefenseFocus=bWorldInteraction && (!PlayerHealth || !PlayerHealth->IsDead()) && !AFPSGAMEPlayerController::BlocksOngoingActions(PC);
    const auto Focus=bWorldInteraction ? ColdSteelWorldInteraction::TraceUseTargets(PC,250.f,bDefenseFocus) : ColdSteelWorldInteraction::FUseTargets{};
    auto* Defense=bDefenseFocus ? Cast<AVillageDefenseSection>(Focus.Target) : nullptr;
    const bool bRepair=Defense && Defense->GetHealth()<=0.f;
    if(auto* Visual=Character?Character->FindComponentByClass<UVillageDefenseFocusVisual>():nullptr)
        Visual->SetFocus(Defense,bDefenseFocus ? Focus.NearbyBreach : nullptr);

// Lines 216-225 | void UColdSteelHUDWidget::UpdateInteractHint()
    if(Text.IsEmpty()){InteractHintBlur->SetVisibility(ESlateVisibility::Collapsed);LastInteractHintText.Reset();return;}
    InteractHintBlur->SetVisibility(ESlateVisibility::HitTestInvisible);
    if(Title!=LastInteractHintTitle)
    {
        InteractHintTitle->SetText(FText::FromString(Title));
        InteractHintTitle->SetVisibility(Title.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
        LastInteractHintTitle=MoveTemp(Title);
    }
    if(Text!=LastInteractHintText){InteractHintText->SetText(FText::FromString(Text));LastInteractHintText=Text;}
    if(bAction!=bLastInteractHintAction){InteractHintKey->SetVisibility(bAction?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);bLastInteractHintAction=bAction;}
