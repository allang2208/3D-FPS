#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickSlot.h"
#include "../Weapons/RuneSwordComponent.h"
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
    // G 槽只在装备符文长剑时占位显示；卸下后连同分隔线收起，其余槽位自动补位。
    if(RuneBladesSlotSurface&&RuneBladesDivider)
    {
        const auto* Sword=GetOwningPlayerPawn()?GetOwningPlayerPawn()->FindComponentByClass<URuneSwordComponent>():nullptr;
        const bool bShow=Sword&&Sword->IsEquipped();
        const auto Visible=bShow?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
        if(RuneBladesSlotSurface->GetVisibility()!=Visible)
        {RuneBladesSlotSurface->SetVisibility(Visible);RuneBladesDivider->SetVisibility(Visible);}
    }
}
