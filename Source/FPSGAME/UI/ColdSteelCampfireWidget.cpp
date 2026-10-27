#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelCampfirePanel.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Components/Border.h"
#include "Components/WidgetSwitcher.h"
#include "GameFramework/PlayerController.h"

void UColdSteelSmeltingWidget::SetCampfire(AColdSteelCampfire* Fire)
{
    SetFurnace(nullptr,FIntVector::ZeroValue);Campfire=Fire;bCampfire=true;
    if(!CampfirePanel)
    {
        CampfirePanel=CreateWidget<UColdSteelCampfirePanel>(GetOwningPlayer());
        StationPanels->AddChild(CampfirePanel);
    }
    CampfirePanel->Configure(HUD,Fire);StationPanels->SetActiveWidget(CampfirePanel);
    UpgradeTab->SetVisibility(ESlateVisibility::Collapsed);
    UpgradeFlyout->SetVisibility(ESlateVisibility::Collapsed);
}
void UColdSteelSmeltingWidget::SubmitCampfire(uint8 Action)
{
    // Kept for the existing widget's public automation entry points.
    if(auto* PC=GetOwningPlayer())if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())if(Campfire.IsValid())
        PS->RequestCampfire(Campfire.Get(),Action,Action==1?SelectedRecipe:NAME_None,Action==1?Batch:1);
    RefreshCampfireJob();
}
void UColdSteelSmeltingWidget::RefreshCampfireJob(){if(CampfirePanel)CampfirePanel->Refresh();}
