// Source/FPSGAME/UI/DevelopmentPanelWidget.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 497-497 | void UDevelopmentPanelWidget::RefreshFeatures()
    if (ResetVillageButton) ResetVillageButton->SetIsEnabled(Player && Player->IsLocalController() && Player->HasAuthority());

// Lines 501-522 | void UDevelopmentPanelWidget::ResetVillageUpgradesClicked()
void UDevelopmentPanelWidget::ResetVillageUpgradesClicked()
{
    const auto* Player = GetOwningPlayer();
    FText Message;
    bool bReset = false;
    if (!Player || !Player->IsLocalController() || !Player->HasAuthority())
        Message = FText::FromString(TEXT("联机村庄升级由房主重置。"));
    else
    {
        TActorIterator<ATemperateHillsWorld> Hills(Player->GetWorld());
        if (!Hills)
            Message = FText::FromString(TEXT("请进入丘陵世界后重置村庄升级。"));
        else
        {
            bReset = Hills->ResetVillageUpgrades(Message);
            if (bReset)
                Message = FText::FromString(TEXT("村庄升级已重置。围墙和已修复的建筑均已恢复为破败形态。"));
        }
    }
    VillageResetHelp->SetText(Message);
    VillageResetHelp->SetColorAndOpacity(bReset ? ColdSteelUI::Success : ColdSteelUI::Warning);
}
