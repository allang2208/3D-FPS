#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelDragVisual.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelStaffIcon.h"
#include "Engine/GameInstance.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelEnhancementLayoutMetrics.h"
#include "../Building/EnhancementWorldView.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/SlateBlueprintLibrary.h"
#include "Widgets/SWidget.h"
#include "HAL/PlatformTime.h"
#include "Components/TextBlock.h"
#include "Components/Border.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"

namespace
{
    bool EnhancementViewportPixel(const UObject* Context,FVector2D Absolute,FVector2D& Pixel)
    {
        const FVector2D Size=UWidgetLayoutLibrary::GetViewportSize(Context);
        const FVector2D GeometrySize=UWidgetLayoutLibrary::GetViewportWidgetGeometry(Context).GetLocalSize();
        if(Absolute.ContainsNaN()||Size.X<=0||Size.Y<=0||GeometrySize.X<=0||GeometrySize.Y<=0)return false;
        FVector2D WidgetPosition;
        // Use the actual viewport host, including window origin and Slate/DPI
        // scale. Re-evaluating the configured DPI curve can offset hit targets.
        USlateBlueprintLibrary::AbsoluteToViewport(Context,Absolute,Pixel,WidgetPosition);
        return !Pixel.ContainsNaN();
    }
    bool IsEnhancementScenePixel(const UObject* Context,FVector2D Pixel)
    {
        const auto Layout=FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(Context));
        return Pixel.X>=Layout.ScenePosition.X&&Pixel.Y>=Layout.ScenePosition.Y
            &&Pixel.X<=Layout.ScenePosition.X+Layout.SceneSize.X&&Pixel.Y<=Layout.ScenePosition.Y+Layout.SceneSize.Y;
    }
}

void UColdSteelEnhancementWidget::ConfigureWorld(AEnhancementWorldView* View)
{bWorldMode=true;WorldView=View;ItemId.Reset();}
bool UColdSteelEnhancementWidget::ContainsManagement(FVector2D Position) const
{
    if(!ManagementSurface)return false;
    FVector2D Pixel;if(!EnhancementViewportPixel(this,Position,Pixel))return false;
    const auto Layout=FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this));
    return Pixel.X>=Layout.PanelPosition.X&&Pixel.Y>=Layout.PanelPosition.Y
        &&Pixel.X<=Layout.PanelPosition.X+Layout.PanelSize.X&&Pixel.Y<=Layout.PanelPosition.Y+Layout.PanelSize.Y;
}
bool UColdSteelEnhancementWidget::ContainsRitual(FVector2D Position) const
{
    if(!WorldView.IsValid()||!WorldView->IsSessionValid()||ContainsManagement(Position))return false;
    FVector2D Pixel;if(!EnhancementViewportPixel(this,Position,Pixel)||!IsEnhancementScenePixel(this,Pixel))return false;
    auto* Player=GetOwningPlayer();if(!Player)return false;
    FVector2D Center,EdgeX,EdgeY;
    const FVector Point=WorldView->RitualLocation();
    if(!Player->ProjectWorldLocationToScreen(Point,Center,false)
        ||!Player->ProjectWorldLocationToScreen(Point+WorldView->GetActorForwardVector()*48.f,EdgeX,false)
        ||!Player->ProjectWorldLocationToScreen(Point+WorldView->GetActorRightVector()*48.f,EdgeY,false))return false;

    const FVector2D Delta=Pixel-Center,X=EdgeX-Center,Y=EdgeY-Center;
    const double Det=X.X*Y.Y-X.Y*Y.X;
    if(FMath::Abs(Det)<1.)return false;
    const double U=(Delta.X*Y.Y-Delta.Y*Y.X)/Det,V=(X.X*Delta.Y-X.Y*Delta.X)/Det;
    return U*U+V*V<=1.15; // A small hit margin around the projected tabletop circle.

}
bool UColdSteelEnhancementWidget::HandleItemDrop(UColdSteelItemDrag* Drag,FVector2D Position)
{
    if(!Drag||!ContainsRitual(Position))return false;
    if(!Drag->IsCurrent(Profile())){Message=TEXT("物品已变化，请重新拖动");Refresh();return true;}
    const auto* Item=Profile()->FindItem(Drag->ItemId);
    if(!Item||!System()->Supports(*Item)){Message=TEXT("请放入可强化／附魔的装备");Refresh();return true;}
    SelectItem(Drag->ItemId);return true;
}
bool UColdSteelEnhancementWidget::HitWorldItem(FVector2D Position) const
{
    if(!bWorldMode||bClosing||!WorldView.IsValid()||!WorldView->IsOpen()||ContainsManagement(Position))return false;
    FVector2D Pixel;if(!EnhancementViewportPixel(this,Position,Pixel))return false;
    if(!IsEnhancementScenePixel(this,Pixel))return false;
    return WorldView->HitItem(Pixel);
}
bool UColdSteelEnhancementWidget::CanRetrieve(const FColdSteelItem& Snapshot) const
{
    if(bClosing||!bWorldMode||!WorldView.IsValid()||!WorldView->IsSessionValid()||System()->Pending())return false;
    const auto* Stored=System()->BenchItem();
    if(!Stored||Snapshot.InstanceId.IsEmpty()||Stored->InstanceId!=Snapshot.InstanceId)return false;
    auto Current=*Stored;Current.Cooldown=Snapshot.Cooldown;
    return FColdSteelItem::StaticStruct()->CompareScriptStruct(&Current,&Snapshot,0);
}
bool UColdSteelEnhancementWidget::RetrieveItem(const FColdSteelItem& Snapshot)
{
    if(!CanRetrieve(Snapshot)){Message=TEXT("工作台物品已变化或操作正在处理，请重新拖动");Refresh();return false;}
    SelectItem(TEXT(""));return true;
}
bool UColdSteelEnhancementDrag::PreviewReturn(const UColdSteelStatusModel* Model,FColdSteelItem& Placed,FString& Reason) const
{
    if(!Model||!Source.IsValid()||!Source->CanRetrieve(Item))
    {Reason=TEXT("工作台物品已变化或操作正在处理，请重新拖动");return false;}
    auto Items=Model->Items();auto Returned=Item;Returned.Container.Reset();
    bool Fits=ColdSteelInventory::Insert(Items,Returned,Returned.BackpackCell);
    if(!Fits&&ColdSteelInventory::CanRotate(Returned))
    {
        ColdSteelInventory::ApplyOrientation(Returned,Returned.bRotated?0:1);
        Fits=ColdSteelInventory::Insert(Items,Returned,Returned.BackpackCell);
    }
    if(!Fits){Reason=TEXT("背包没有连续空间，装备仍保留在工作台");return false;}
    const auto* Found=Items.FindByPredicate([this](const auto& I){return I.InstanceId==Item.InstanceId;});
    if(!Found)return false;
    Placed=*Found;Reason=TEXT("松开取回背包 · 自动放入高亮空位");return true;
}
bool UColdSteelEnhancementDrag::Retrieve()
{return Source.IsValid()&&Source->RetrieveItem(Item);}

void UColdSteelEnhancementDrag::ReleaseVisual()
{
    if(PointerVisual)PointerVisual->RemoveFromParent();PointerVisual=nullptr;
    if(ActivationHandle.IsValid()&&FSlateApplication::IsInitialized())
        FSlateApplication::Get().OnApplicationActivationStateChanged().Remove(ActivationHandle);
    ActivationHandle.Reset();
}
void UColdSteelEnhancementDrag::Dragged_Implementation(const FPointerEvent& E)
{if(PointerVisual)PointerVisual->MoveTo(E.GetScreenSpacePosition());Super::Dragged_Implementation(E);}
void UColdSteelEnhancementDrag::Drop_Implementation(const FPointerEvent& E)
{ReleaseVisual();Super::Drop_Implementation(E);}
void UColdSteelEnhancementDrag::DragCancelled_Implementation(const FPointerEvent& E)
{ReleaseVisual();Super::DragCancelled_Implementation(E);}
void UColdSteelEnhancementDrag::HandleApplicationActivation(bool Active)
{if(!Active&&PointerVisual){FSlateApplication::Get().CancelDragDrop();ReleaseVisual();}}

void UColdSteelEnhancementWidget::RefreshBenchDragVisual()
{
    auto* Drag=ActiveBenchDrag.Get();if(!Drag||!Drag->PointerVisual)return;
    auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    const auto* Brush=Icons->Find(Drag->Item);
    if(!Brush)Brush=MaterialIcon(Drag->Item.Definition);
    if(!Brush||!Brush->GetResourceObject())return; // Keep the caption until an icon is ready.
    const FVector2D ViewSize=UWidgetLayoutLibrary::GetViewportSize(this);
    const FGeometry View=UWidgetLayoutLibrary::GetViewportWidgetGeometry(this);
    if(ViewSize.X<=0||ViewSize.Y<=0)return;
    // Use the ordinary backpack's responsive grid footprint, not the 3D model bounds.
    const double BagWidth=FMath::Min(ViewSize.X-ColdSteelUI::NavigationDrawerInset-12.,FMath::Clamp(ViewSize.X*.48,720.,1040.));
    const double Cell=FMath::Max(1.,(BagWidth-24.)/18.);
    const FVector2D Rect(Drag->Item.Width*Cell,Drag->Item.Height*Cell),Image=Brush->ImageSize;
    const bool Rotated=Drag->Item.bRotated;
    const bool StablePortrait=ColdSteelInventory::Text(Drag->Item,TEXT("weaponType"))==TEXT("staff")||ColdSteelInventory::IsOneHandedMelee(Drag->Item);
    const double Fit=Rotated?FMath::Min((Rect.X-8)/FMath::Max(1.,Image.Y),(Rect.Y-8)/FMath::Max(1.,Image.X))
                            :FMath::Min((Rect.X-8)/FMath::Max(1.,Image.X),(Rect.Y-8)/FMath::Max(1.,Image.Y));
    const FVector2D DrawSize=StablePortrait?ColdSteelStaffIcon::InventorySize(Image,Rect,Rotated):Image*Fit;
    const FVector2D ScreenSize=View.LocalToAbsolute(DrawSize*View.GetLocalSize()/ViewSize)-View.LocalToAbsolute(FVector2D::ZeroVector);
    const FVector2D CursorPos=FSlateApplication::Get().GetCursorPos();
    Drag->PointerVisual->Configure(Brush,ScreenSize,ScreenSize*.5,CursorPos,Rotated);
    Drag->PointerVisual->MoveTo(CursorPos);
    if(Drag->DefaultDragVisual)Drag->DefaultDragVisual->SetVisibility(ESlateVisibility::Hidden);
}

FReply UColdSteelEnhancementWidget::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E)
{
    if(WorldView.IsValid())WorldView->SetItemHovered(!System()->Pending()&&!FSlateApplication::Get().IsDragDropping()&&HitWorldItem(E.GetScreenSpacePosition()));
    return Super::NativeOnMouseMove(G,E);
}
void UColdSteelEnhancementWidget::NativeOnMouseLeave(const FPointerEvent& E)
{
    if(WorldView.IsValid())WorldView->SetItemHovered(false);
    Super::NativeOnMouseLeave(E);
}
FReply UColdSteelEnhancementWidget::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    PressedBenchItem={};
    if(HitWorldItem(E.GetScreenSpacePosition()))
    {
        const auto* Stored=System()->BenchItem();
        if(Stored&&!System()->Pending())
        {
            if(E.GetEffectingButton()==EKeys::RightMouseButton)
            {const auto Snapshot=*Stored;RetrieveItem(Snapshot);return FReply::Handled();}
            if(E.GetEffectingButton()==EKeys::LeftMouseButton)
            {PressedBenchItem=*Stored;return FReply::Handled().DetectDrag(TakeWidget(),EKeys::LeftMouseButton);}
        }
        return FReply::Handled();
    }
    return Super::NativeOnMouseButtonDown(G,E);
}
FReply UColdSteelEnhancementWidget::NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E)
{
    PressedBenchItem={};return Super::NativeOnMouseButtonUp(G,E);
}
void UColdSteelEnhancementWidget::NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*& Out)
{
    const auto Snapshot=PressedBenchItem;PressedBenchItem={};
    if(!CanRetrieve(Snapshot))return;
    auto* Drag=NewObject<UColdSteelEnhancementDrag>(this);Drag->Source=this;Drag->Item=Snapshot;
    auto* Caption=NewObject<UTextBlock>(Drag);
    const FString Name=ColdSteelInventory::Text(Snapshot,TEXT("name"));
    Caption->SetText(FText::FromString(TEXT("取回背包 · ")+(Name.IsEmpty()?Snapshot.Definition:Name)));
    Caption->SetFont(ColdSteelUI::TextFont(14));Caption->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    auto* Card=NewObject<UBorder>(Drag);Card->SetPadding(FMargin(12,8));Card->SetBrushColor(ColdSteelUI::GlassTint);
    Card->SetContent(Caption);Card->SetVisibility(ESlateVisibility::HitTestInvisible);
    Drag->DefaultDragVisual=Card;Drag->Pivot=EDragPivot::MouseDown;Out=Drag;
    // Match the inventory overlay and avoid UMG's source-origin fly-in animation.
    Drag->PointerVisual=CreateWidget<UColdSteelDragVisual>(GetOwningPlayer());
    Drag->PointerVisual->Configure(nullptr,FVector2D::ZeroVector,FVector2D::ZeroVector,FSlateApplication::Get().GetCursorPos());
    Drag->PointerVisual->AddToViewport(1000);ActiveBenchDrag=Drag;
    Drag->ActivationHandle=FSlateApplication::Get().OnApplicationActivationStateChanged().AddUObject(Drag,&UColdSteelEnhancementDrag::HandleApplicationActivation);
    GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->Request(Snapshot);
    RefreshBenchDragVisual();
    if(WorldView.IsValid())WorldView->SetItemHovered(false);
}
bool UColdSteelEnhancementWidget::NativeOnDragOver(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Operation)
{return Cast<UColdSteelItemDrag>(Operation)&&ContainsRitual(E.GetScreenSpacePosition());}
bool UColdSteelEnhancementWidget::NativeOnDrop(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Operation)
{return HandleItemDrop(Cast<UColdSteelItemDrag>(Operation),E.GetScreenSpacePosition());}

void UColdSteelEnhancementWidget::OnNetworkResult(bool Success,const FString& Result)
{
    const bool Play=Success&&bProcessingRequest;bProcessingRequest=false;
    const FString PlacedId=MoveTemp(PlacementRequestId);PlacementRequestId.Reset();
    bLastApplySucceeded=Success;Message=Result;
    if(Play)FlashUntil=FPlatformTime::Seconds()+.9;
    Refresh();
    if(Success&&!PlacedId.IsEmpty()&&WorldView.IsValid())WorldView->PlayPlacement(PlacedId);
    if(Play&&WorldView.IsValid())WorldView->PlayRitual(bEnchant);
}
