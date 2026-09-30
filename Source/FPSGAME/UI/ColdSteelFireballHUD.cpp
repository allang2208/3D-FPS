#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickSlot.h"
#include "../Weapons/RuneOrbBladesComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "Components/Border.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"

// The former fixed Q fireball presentation now follows every mixed shortcut binding.
void UColdSteelHUDWidget::BuildQuickSlot(UOverlay* Overlay,int32 Index,FName FixedSkill)
{
    auto* QuickSlotWidget=CreateWidget<UColdSteelQuickSlot>(GetOwningPlayer());QuickSlotWidget->Configure(this,Index,FixedSkill);
    auto* QuickSlotLayout=Overlay->AddChildToOverlay(QuickSlotWidget);
    QuickSlotLayout->SetHorizontalAlignment(HAlign_Fill);QuickSlotLayout->SetVerticalAlignment(VAlign_Fill);
    QuickSlots.Add(QuickSlotWidget);
}
void UColdSteelHUDWidget::RefreshQuickBar()
{
    for(const auto& QuickSlotWidget:QuickSlots)if(QuickSlotWidget)QuickSlotWidget->Refresh();
    // The fixed G slot follows the equipped weapon; it never consumes a learned-skill binding.
    if(RuneBladesSlotSurface&&RuneBladesDivider)
    {
        const auto* Blades=GetOwningPlayerPawn()?GetOwningPlayerPawn()->FindComponentByClass<URuneOrbBladesComponent>():nullptr;
        const auto* Staff=GetOwningPlayerPawn()?GetOwningPlayerPawn()->FindComponentByClass<UStaffWeaponComponent>():nullptr;
        const bool bShow=(Blades&&Blades->SwordEquipped())||(Staff&&Staff->HasIlluminationSpecial());
        const auto Visible=bShow?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
        if(RuneBladesSlotSurface->GetVisibility()!=Visible)
        {RuneBladesSlotSurface->SetVisibility(Visible);RuneBladesDivider->SetVisibility(Visible);}
    }
}
