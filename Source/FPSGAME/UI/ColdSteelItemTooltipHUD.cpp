#include "ColdSteelHUDWidget.h"
#include "ColdSteelItemTooltip.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
void UColdSteelHUDWidget::ShowItemTooltip(const FString& Id,FVector2D ScreenAnchor,bool Pinned,UWidget* Source)
{
    if(!bInventoryOpen||bStatusTabActive||Id.IsEmpty())return;
    auto* Root=Cast<UCanvasPanel>(WidgetTree->RootWidget);if(!Root)return;
    if(!ItemTooltip){ItemTooltip=CreateWidget<UColdSteelItemTooltip>(GetOwningPlayer());auto* S=Root->AddChildToCanvas(ItemTooltip);S->SetZOrder(200);}
    ItemTooltip->ShowItem(Id,Root->GetCachedGeometry().AbsoluteToLocal(ScreenAnchor),Pinned,Source);
}
void UColdSteelHUDWidget::HideItemTooltip(bool Force){if(ItemTooltip)ItemTooltip->Hide(Force);}
bool UColdSteelHUDWidget::HasPinnedItemTooltip()const{return ItemTooltip&&ItemTooltip->IsPinned();}
void UColdSteelHUDWidget::FocusItemTooltip(){if(ItemTooltip&&ItemTooltip->IsPinned())ItemTooltip->SetKeyboardFocus();}
