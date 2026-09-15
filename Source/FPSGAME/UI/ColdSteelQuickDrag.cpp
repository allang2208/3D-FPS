#include "ColdSteelQuickDrag.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelDragVisual.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/SizeBox.h"
#include "Components/Border.h"
#include "Components/BackgroundBlur.h"
#include "Components/CanvasPanelSlot.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"

bool UColdSteelQuickDrag::IsCurrent() const
{
    const auto* Model=HUD.IsValid()?HUD->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model||Model->QuickBindings()!=Bindings)return false;
    return SourceSlot>=0?Bindings.IsValidIndex(SourceSlot)&&!Bindings[SourceSlot].IsEmpty():Model->CanBindQuickSkill(Skill);
}
void UColdSteelQuickDrag::ReleaseVisual(){if(Visual)Visual->RemoveFromParent();Visual=nullptr;}
void UColdSteelQuickDrag::Dragged_Implementation(const FPointerEvent& E)
{if(Visual)Visual->MoveTo(E.GetScreenSpacePosition());if(HUD.IsValid())HUD->UpdateQuickDrag(this,E.GetScreenSpacePosition());Super::Dragged_Implementation(E);}
void UColdSteelQuickDrag::Drop_Implementation(const FPointerEvent& E)
{ReleaseVisual();if(HUD.IsValid())HUD->EndQuickDrag();Super::Drop_Implementation(E);}
void UColdSteelQuickDrag::DragCancelled_Implementation(const FPointerEvent& E)
{ReleaseVisual();if(HUD.IsValid())HUD->EndQuickDrag();Super::DragCancelled_Implementation(E);}

UColdSteelQuickDrag* UColdSteelHUDWidget::StartQuickDrag(FName Skill,int32 From,const FSlateBrush* Icon,FVector2D Position)
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||QuickDrag.IsValid()||(From<0?!Model->CanBindQuickSkill(Skill):Model->QuickBinding(From).IsEmpty()))return nullptr;
    auto* Drag=NewObject<UColdSteelQuickDrag>(this);Drag->HUD=this;Drag->Skill=Skill;Drag->SourceSlot=From;Drag->Bindings=Model->QuickBindings();
    Drag->Visual=CreateWidget<UColdSteelDragVisual>(GetOwningPlayer());
    const FVector2D Size(48);Drag->Visual->Configure(Icon,Size,Size*.5,Position);Drag->Visual->AddToViewport(1000);
    auto* Empty=NewObject<USizeBox>(this);Empty->SetVisibility(ESlateVisibility::HitTestInvisible);Drag->DefaultDragVisual=Empty;Drag->Pivot=EDragPivot::TopLeft;
    QuickDrag=Drag;bCloseAfterQuickDrag=From<0;
    QuickDragActivationHandle=FSlateApplication::Get().OnApplicationActivationStateChanged().AddUObject(this,&ThisClass::HandleQuickDragActivation);
    HideItemTooltip(true);SetVisibility(ESlateVisibility::Visible);SetIsFocusable(true);
    InventoryBackdrop->SetVisibility(ESlateVisibility::Visible);
    if(bCloseAfterQuickDrag){InventoryPanel->SetVisibility(ESlateVisibility::Hidden);InventoryBackdrop->SetRenderOpacity(0);InventoryBlur->SetRenderOpacity(0);}
    if(HotbarCanvasSlot)HotbarCanvasSlot->SetZOrder(60);
    SetKeyboardFocus();
    UpdateQuickDrag(Drag,Position);return Drag;
}
int32 UColdSteelHUDWidget::QuickBarDropIndex(FVector2D Position) const
{for(int32 I=0;I<QuickSlotSurfaces.Num();++I)if(QuickSlotSurfaces[I]->GetCachedGeometry().IsUnderLocation(Position))return I;return INDEX_NONE;}
void UColdSteelHUDWidget::HighlightQuickBar(int32 Index,bool Valid)
{
    for(int32 I=0;I<QuickSlotSurfaces.Num();++I)
    {
        const bool Hover=I==Index;
        QuickSlotSurfaces[I]->SetBrush(ColdSteelUI::RoundedBrush(Hover?ColdSteelUI::ButtonHover:ColdSteelUI::Content,7.f,
            Hover?(Valid?ColdSteelUI::Success:ColdSteelUI::Danger):ColdSteelUI::Border,Hover?2.f:1.f));
    }
}
void UColdSteelHUDWidget::UpdateQuickDrag(UColdSteelQuickDrag* Drag,FVector2D Position)
{if(QuickDrag.Get()==Drag)HighlightQuickBar(QuickBarDropIndex(Position),Drag->IsCurrent());}
bool UColdSteelHUDWidget::DropQuickDrag(UColdSteelQuickDrag* Drag,int32 Target)
{
    if(!Drag||QuickDrag.Get()!=Drag)return false;
    if(Drag->IsCurrent())
    {
        auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(Target>=0){if(Drag->SourceSlot>=0)Model->SwapQuickBindings(Drag->SourceSlot,Target);else Model->BindQuickSkill(Target,Drag->Skill);}
        else if(Drag->SourceSlot>=0)Model->ClearQuickBinding(Drag->SourceSlot);
    }
    Drag->ReleaseVisual();EndQuickDrag();RefreshQuickBar();return true;
}
bool UColdSteelHUDWidget::DropInventoryOnQuickBar(UColdSteelItemDrag* Drag,int32 Target)
{
    if(!Drag||InventoryDrag.Get()!=Drag)return false;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(CanDropOnHotbar(Drag))
    {
        if(Drag->HotbarIndex>=0)Model->SwapQuickBindings(Drag->HotbarIndex+ColdSteelQuickBar::ItemOffset,Target);
        else Model->BindQuickItem(Target,Drag->ItemId);
        if(Drag->SourceBoard.IsValid())Drag->SourceBoard->InteractionMessage=Model->ResultMessage();
    }
    else if(Drag->SourceBoard.IsValid())Drag->SourceBoard->InteractionMessage=TEXT("仅可绑定背包消耗品；物品变化后请重新拖动");
    EndInventoryDrag();RefreshQuickBar();return true;
}
void UColdSteelHUDWidget::EndQuickDrag()
{
    if(QuickDragActivationHandle.IsValid()&&FSlateApplication::IsInitialized())FSlateApplication::Get().OnApplicationActivationStateChanged().Remove(QuickDragActivationHandle);
    QuickDragActivationHandle.Reset();
    if(!QuickDrag.IsValid()&&!bCloseAfterQuickDrag)return;
    if(auto* Drag=QuickDrag.Get())Drag->ReleaseVisual();
    QuickDrag.Reset();const bool Close=bCloseAfterQuickDrag;bCloseAfterQuickDrag=false;
    HighlightQuickBar(INDEX_NONE,false);if(HotbarCanvasSlot)HotbarCanvasSlot->SetZOrder(30);
    if(Close)SetInventoryOpen(false);
    SetVisibility(bInventoryOpen?ESlateVisibility::Visible:ESlateVisibility::SelfHitTestInvisible);SetIsFocusable(bInventoryOpen);
    InventoryPanel->SetVisibility(bInventoryOpen?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    InventoryBackdrop->SetVisibility(bInventoryOpen?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    InventoryBackdrop->SetRenderOpacity(DrawerProgress);InventoryBlur->SetRenderOpacity(DrawerProgress);
    if(bInventoryOpen)SetKeyboardFocus();
}
void UColdSteelHUDWidget::CancelQuickDrag()
{if(QuickDrag.IsValid()){UWidgetBlueprintLibrary::CancelDragDrop();EndQuickDrag();}}
void UColdSteelHUDWidget::HandleQuickDragActivation(bool Active)
{if(!Active)CancelQuickDrag();}
