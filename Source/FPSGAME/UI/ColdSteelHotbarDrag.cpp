#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelWarehouseWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Components/Border.h"
#include "Components/BackgroundBlur.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ScrollBox.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"

using namespace ColdSteelInventory;

void UColdSteelHUDWidget::BeginInventoryDrag(UColdSteelItemDrag* Drag)
{
    if(!Drag||!bInventoryOpen||bStatusTabActive||!InventoryPanel)return;
    InventoryDrag=Drag;
    if(!InventoryDragActivationHandle.IsValid())InventoryDragActivationHandle=FSlateApplication::Get().OnApplicationActivationStateChanged().AddUObject(this,&ThisClass::HandleInventoryDragActivation);
    const auto PanelGeometry=InventoryPanel->GetCachedGeometry();
    InventoryDragBounds=FSlateRect(PanelGeometry.LocalToAbsolute(FVector2D::ZeroVector),PanelGeometry.LocalToAbsolute(PanelGeometry.GetLocalSize()));
    // Keep the interaction session alive while the drawer is visually hidden.
    // The transparent backdrop receives released items outside the drawer.
    InventoryBackdrop->SetVisibility(ESlateVisibility::Visible);
    if(HotbarCanvasSlot)HotbarCanvasSlot->SetZOrder(60);
    HideItemTooltip(true);
}

int32 UColdSteelHUDWidget::HotbarDropIndex(FVector2D Position)const
{
    if(!InventoryDrag.IsValid())return INDEX_NONE;
    return QuickBarDropIndex(Position);
}

bool UColdSteelHUDWidget::CanDropOnHotbar(const UColdSteelItemDrag* Drag)const
{
    if(!Drag||InventoryDrag.Get()!=Drag)return false;
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Drag->IsCurrent(Model))return false;
    const auto* Item=Model?Model->FindItem(Drag->ItemId):nullptr;
    if(!Item||Item->Place!=Drag->SourcePlace||Item->Cell!=Drag->SourceCell||Item->Place!=0||Text(*Item,TEXT("category"))!=TEXT("consumable"))return false;
    if(Drag->HotbarIndex>=0){const auto* Bound=Model->ResolveHotbar(Drag->HotbarIndex);return Bound&&Bound->InstanceId==Drag->ItemId;}
    return true;
}

void UColdSteelHUDWidget::UpdateInventoryDrag(UColdSteelItemDrag* Drag,FVector2D Position)
{
    if(InventoryDrag.Get()!=Drag||!bInventoryOpen)return;
    const bool OverWarehouse=bWarehouseOpen&&WarehouseWidget&&WarehouseWidget->GetCachedGeometry().IsUnderLocation(Position);
    const bool Outside=!InventoryDragBounds.ContainsPoint(Position)&&!OverWarehouse;
    if(Outside!=bInventoryDragOutside){
        bInventoryDragOutside=Outside;
        const bool Hide=Outside&&!bWarehouseOpen;
        InventoryPanel->SetRenderOpacity(Hide?0.f:1.f);
        InventoryPanel->SetVisibility(Hide?ESlateVisibility::Hidden:ESlateVisibility::Visible);
        InventoryBackdrop->SetRenderOpacity(Hide?0.f:DrawerProgress);
        InventoryBlur->SetRenderOpacity(Hide?0.f:DrawerProgress);
    }
    const int32 Target=HotbarDropIndex(Position);
    const bool Valid=CanDropOnHotbar(Drag);
    HighlightQuickBar(Target,Valid);
}

void UColdSteelHUDWidget::EndInventoryDrag()
{
    if(InventoryDragActivationHandle.IsValid()&&FSlateApplication::IsInitialized())FSlateApplication::Get().OnApplicationActivationStateChanged().Remove(InventoryDragActivationHandle);
    InventoryDragActivationHandle.Reset();
    if(!InventoryDrag.IsValid()&&!bInventoryDragOutside)return;
    InventoryDrag.Reset();bInventoryDragOutside=false;
    if(HotbarCanvasSlot)HotbarCanvasSlot->SetZOrder(30);
    if(InventoryPanel){InventoryPanel->SetRenderOpacity(1.f);if(bInventoryOpen)InventoryPanel->SetVisibility(ESlateVisibility::Visible);}
    if(InventoryBackdrop){InventoryBackdrop->SetVisibility(ESlateVisibility::HitTestInvisible);InventoryBackdrop->SetRenderOpacity(DrawerProgress);}
    if(InventoryBlur)InventoryBlur->SetRenderOpacity(DrawerProgress);
    HighlightQuickBar(INDEX_NONE,false);
}

void UColdSteelHUDWidget::HandleInventoryDragActivation(bool Active)
{
    if(!Active){FSlateApplication::Get().CancelDragDrop();EndInventoryDrag();}
}

bool UColdSteelHUDWidget::NativeOnDragOver(const FGeometry& Geometry,const FDragDropEvent& Event,UDragDropOperation* Operation)
{
    if(auto* Quick=Cast<UColdSteelQuickDrag>(Operation)){UpdateQuickDrag(Quick,Event.GetScreenSpacePosition());return QuickDrag.Get()==Quick;}
    auto* Drag=Cast<UColdSteelItemDrag>(Operation);
    if(!Drag||InventoryDrag.Get()!=Drag)return Super::NativeOnDragOver(Geometry,Event,Operation);
    UpdateInventoryDrag(Drag,Event.GetScreenSpacePosition());
    return bInventoryDragOutside||HotbarDropIndex(Event.GetScreenSpacePosition())>=0;
}

bool UColdSteelHUDWidget::NativeOnDrop(const FGeometry& Geometry,const FDragDropEvent& Event,UDragDropOperation* Operation)
{
    if(auto* Quick=Cast<UColdSteelQuickDrag>(Operation))return DropQuickDrag(Quick,QuickBarDropIndex(Event.GetScreenSpacePosition()));
    auto* Drag=Cast<UColdSteelItemDrag>(Operation);
    if(!Drag||InventoryDrag.Get()!=Drag)return Super::NativeOnDrop(Geometry,Event,Operation);
    const auto* CurrentModel=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Drag->IsCurrent(CurrentModel)){
        if(Drag->SourceBoard.IsValid())Drag->SourceBoard->InteractionMessage=TEXT("物品已变化，请重新拖动");
        EndInventoryDrag();return true;
    }
    // Re-evaluate on release: stale instances or a failed save cannot bind a shortcut.
    UpdateInventoryDrag(Drag,Event.GetScreenSpacePosition());
    const int32 Target=HotbarDropIndex(Event.GetScreenSpacePosition());
    if(Target<0&&!bInventoryDragOutside&&Drag->SourceBoard.IsValid()){
        // A rapid return-and-release may still route through last frame's backdrop.
        auto* Scroll=Cast<UScrollBox>(EquipmentPage);
        auto* Board=bWarehouseOpen&&WarehouseWidget->GetCachedGeometry().IsUnderLocation(Event.GetScreenSpacePosition())?WarehouseWidget->Board.Get():Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):Drag->SourceBoard.Get();
        Board->NativeOnDrop(Board->GetCachedGeometry(),Event,Operation);
    }
    if(Target>=0&&CanDropOnHotbar(Drag)){
        auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(Drag->HotbarIndex>=0)Model->SwapQuickBindings(Drag->HotbarIndex+ColdSteelQuickBar::ItemOffset,Target);
        else Model->BindQuickItem(Target,Drag->ItemId);
        if(Drag->SourceBoard.IsValid())Drag->SourceBoard->InteractionMessage=Model->ResultMessage();
        RefreshAmmo();
    }
    const FVector2D Position=Event.GetScreenSpacePosition();
    const bool OverHotbar=HotbarCanvasSlot&&HotbarCanvasSlot->GetContent()&&HotbarCanvasSlot->GetContent()->GetCachedGeometry().IsUnderLocation(Position);
    if(Target<0&&bInventoryDragOutside&&!OverHotbar&&Geometry.IsUnderLocation(Position)&&Drag->HotbarIndex<0){
        auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const auto* Item=Model->FindItem(Drag->ItemId);
        if(Item&&(Item->Place<=1||(Item->Place==4&&bWarehouseOpen))&&Item->Place==Drag->SourcePlace&&Item->Cell==Drag->SourceCell){
            const bool Dropped=Model->Drop(Drag->ItemId);
            if(Drag->SourceBoard.IsValid())Drag->SourceBoard->InteractionMessage=Dropped?TEXT("物品已放到脚边，可重新拾取"):Model->ResultMessage();
            RefreshAmmo();
        }
    }
    EndInventoryDrag();
    return true;
}
