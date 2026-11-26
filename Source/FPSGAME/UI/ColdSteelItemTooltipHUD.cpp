#include "ColdSteelHUDWidget.h"
#include "ColdSteelItemTooltip.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
void UColdSteelHUDWidget::ShowItemTooltip(const FString& Id,FVector2D ScreenAnchor,bool Pinned,UWidget* Source,const FColdSteelItemTooltipPreview* Preview)
{
    if(!bInventoryOpen||bStatusTabActive||bQuestTabActive||bMountTabActive||Id.IsEmpty())return;
    auto* Root=Cast<UCanvasPanel>(WidgetTree->RootWidget);if(!Root)return;
    if(!ItemTooltip){ItemTooltip=CreateWidget<UColdSteelItemTooltip>(GetOwningPlayer());auto* S=Root->AddChildToCanvas(ItemTooltip);S->SetZOrder(200);}
    ItemTooltip->ShowItem(Id,Root->GetCachedGeometry().AbsoluteToLocal(ScreenAnchor),Pinned,Source,Preview);
}
void UColdSteelHUDWidget::HideItemTooltip(bool Force,const UWidget* Source)
{
    if(ItemTooltip&&(!Source||ItemTooltip->ReturnFocus.Get()==Source))ItemTooltip->Hide(Force);
}
bool UColdSteelHUDWidget::HasPinnedItemTooltip()const{return ItemTooltip&&ItemTooltip->IsPinned();}
bool UColdSteelHUDWidget::IsItemTooltipPinnedFrom(const UWidget* Source) const
{return HasPinnedItemTooltip()&&ItemTooltip->ReturnFocus.Get()==Source;}
void UColdSteelHUDWidget::FocusItemTooltip(){if(ItemTooltip&&ItemTooltip->IsPinned())ItemTooltip->SetKeyboardFocus();}
