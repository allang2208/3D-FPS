#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"

// The former fixed Q fireball presentation now follows every mixed shortcut binding.
void UColdSteelHUDWidget::BuildQuickSlot(UOverlay* Overlay,int32 Index)
{
    auto* QuickSlotWidget=CreateWidget<UColdSteelQuickSlot>(GetOwningPlayer());QuickSlotWidget->Configure(this,Index);
    auto* QuickSlotLayout=Overlay->AddChildToOverlay(QuickSlotWidget);
    QuickSlotLayout->SetHorizontalAlignment(HAlign_Fill);QuickSlotLayout->SetVerticalAlignment(VAlign_Fill);
    QuickSlots.Add(QuickSlotWidget);
}
void UColdSteelHUDWidget::RefreshQuickBar()
{for(const auto& QuickSlotWidget:QuickSlots)if(QuickSlotWidget)QuickSlotWidget->Refresh();}
