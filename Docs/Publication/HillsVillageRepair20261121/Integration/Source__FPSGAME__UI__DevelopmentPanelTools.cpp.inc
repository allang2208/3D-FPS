// Source/FPSGAME/UI/DevelopmentPanelTools.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 149-155 | void UDevelopmentPanelWidget::BuildFeatureRows(UVerticalBox* Page)
            ? TEXT("当前丘陵世界的村庄升级由房主重置。")
            : TEXT("将当前丘陵世界的围墙和所有已修复的建筑恢复为破败形态，并保存建设进度。"));
        VillageResetHelp = Parts.Help;
        ResetVillageButton = MakeButton(TEXT("重置村庄升级"), TEXT("DevelopmentResetVillageUpgrades"));
        ResetVillageButton->OnClicked.AddDynamic(this, &ThisClass::ResetVillageUpgradesClicked);
        AddFixed(Parts, ResetVillageButton, 150.f);
        FeatureRows.Add(Parts.Row);
