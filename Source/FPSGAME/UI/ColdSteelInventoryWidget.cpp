#include "ColdSteelInventoryWidget.h"
#include "ColdSteelDragVisual.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelStaffIcon.h"
#include "../Weapons/GunsmithSystem.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/SizeBox.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Components/ScaleBox.h"
#include "ColdSteelInventoryPopup.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Rendering/DrawElements.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
using namespace ColdSteelInventory;
bool UColdSteelItemDrag::IsCurrent(const UColdSteelStatusModel* Model)const
{
    const auto* I=Model?Model->FindItem(ItemId):nullptr;
    if(!I||I->Place!=SourcePlace||I->Cell!=SourceCell)return false;
    if(!bHasSourceSnapshot)return true;
    auto Current=*I;Current.Cooldown=SourceSnapshot.Cooldown; // Natural cooldown ticking does not change the held stack.
    return FColdSteelItem::StaticStruct()->CompareScriptStruct(&Current,&SourceSnapshot,0);
}
void UColdSteelInventoryWidget::ConfigureWarehouse(UColdSteelHUDWidget* Owner){bWarehouse=true;StorageHUD=Owner;FocusPlace=4;FocusCell=StorageStart();LoadIcons();}
int32 UColdSteelInventoryWidget::StorageStart()const{return bWarehouse&&Model?Model->WarehousePage*ColdSteelWarehouse::CellsPerPage:0;}
int32 UColdSteelInventoryWidget::StorageRows()const{return bWarehouse?ColdSteelWarehouse::Rows:(Model?ColdSteelInventory::BagRows(Model->Items()):4);}
void UColdSteelInventoryWidget::ResetStoragePage(){CancelInteraction();FocusPlace=StoragePlace();FocusCell=StorageStart();HoverPlace=-1;PointerCell=-1;LoadIcons();}
void UColdSteelItemDrag::ReleaseVisual(){if(PointerVisual)PointerVisual->RemoveFromParent();PointerVisual=nullptr;}
void UColdSteelItemDrag::Drop_Implementation(const FPointerEvent& E){ReleaseVisual();if(SourceHUD.IsValid())SourceHUD->EndInventoryDrag();if(SourceBoard.IsValid())SourceBoard->FinishDrag();Super::Drop_Implementation(E);}
void UColdSteelItemDrag::DragCancelled_Implementation(const FPointerEvent& E){ReleaseVisual();if(SourceHUD.IsValid())SourceHUD->EndInventoryDrag();if(SourceBoard.IsValid())SourceBoard->FinishDrag();Super::DragCancelled_Implementation(E);}
void UColdSteelItemDrag::Dragged_Implementation(const FPointerEvent& E){if(PointerVisual)PointerVisual->MoveTo(E.GetScreenSpacePosition());if(SourceHUD.IsValid())SourceHUD->UpdateInventoryDrag(this,E.GetScreenSpacePosition());Super::Dragged_Implementation(E);}
void UColdSteelInventoryWidget::FinishDrag(){if(auto Drag=ActivePointerDrag.Get())Drag->ReleaseVisual();ActivePointerDrag.Reset();if(auto* HUD=TooltipHUD())HUD->EndInventoryDrag();DraggedItem.Empty();bPendingClick=false;ClearDragPreview();}
void UColdSteelInventoryWidget::ClearDragPreview(){bPreviewValid=false;PreviewReason.Empty();SwapDestinations.Empty();PreviewPlace=-1;PreviewCell=-1;PreviewCells=FIntPoint(1,1);bPreviewRotatable=false;}
void UColdSteelInventoryWidget::CancelInteraction(){PendingTooltip.Empty();FinishDrag();Selected.Empty();KeyboardCarry.Empty();bConfirmDrop=false;InteractionMessage.Empty();if(ItemMenu)ItemMenu->Close(false);ItemMenu=nullptr;}
void UColdSteelInventoryWidget::OpenItemMenu(FVector2D Anchor,bool SplitOnly){if(ItemMenu)ItemMenu->Close(false);if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);ItemMenu=CreateWidget<UColdSteelInventoryPopup>(GetOwningPlayer());ItemMenu->Open(this,Model,Selected,Anchor,SplitOnly);}

void UColdSteelInventoryWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);Scale=ColdSteelUI::PixelScale(this);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    WeaponIcons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    if(!WidgetTree->RootWidget){auto* Size=WidgetTree->ConstructWidget<USizeBox>();WidgetTree->RootWidget=Size;}
    SetVisibility(ESlateVisibility::Visible);LoadIcons();
}
void UColdSteelInventoryWidget::NativeConstruct(){Super::NativeConstruct();if(Model&&!ModelHandle.IsValid())ModelHandle=Model->OnChanged.AddUObject(this,&ThisClass::LoadIcons);if(WeaponIcons&&!IconHandle.IsValid())IconHandle=WeaponIcons->OnReady.AddUObject(this,&ThisClass::OnWeaponIconReady);LoadIcons();}
void UColdSteelInventoryWidget::NativeTick(const FGeometry& G,float Delta)
{
    Super::NativeTick(G,Delta);
    Scale=ColdSteelUI::PixelScale(this);
    if(IsVisible()&&IsHovered()&&!PendingTooltip.IsEmpty()&&!bHoverTooltipShown&&!bPendingClick&&KeyboardCarry.IsEmpty()&&!FSlateApplication::Get().IsDragDropping())
    {
        TooltipHoverTime+=Delta;
        if(TooltipHoverTime>=.2f)if(auto* HUD=TooltipHUD()){HUD->ShowItemTooltip(PendingTooltip,TooltipAnchor,false,this);bHoverTooltipShown=true;}
    }
    if(IsVisible()&&bProcessingAnimated){GlintSeconds+=Delta;if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);}
    if(auto* Size=Cast<USizeBox>(WidgetTree->RootWidget)){
        const float Height=Layout(G).Height/Scale;
        if(!FMath::IsNearlyEqual(Size->GetMinDesiredHeight(),Height,.5f))Size->SetMinDesiredHeight(Height);
    }
}
void UColdSteelInventoryWidget::NativeDestruct(){if(Model)Model->OnChanged.Remove(ModelHandle);ModelHandle.Reset();if(WeaponIcons)WeaponIcons->OnReady.Remove(IconHandle);IconHandle.Reset();CancelInteraction();Super::NativeDestruct();}
void UColdSteelInventoryWidget::OnWeaponIconReady(const FString& Recipe)
{
    if (!Model || !WeaponIcons || !IsVisible()) return;
    for (const auto& Item : Model->Items())
    {
        const bool InView = bWarehouse ? Model->InOpenStorage(Item) && Item.Cell >= StorageStart() && Item.Cell < StorageStart() + ColdSteelWarehouse::CellsPerPage : Item.Place == 0 || Item.Place == 1;
        if (InView && WeaponIcons->Supports(Item) && WeaponIcons->Key(Item) == Recipe)
        {
            if (auto Slate = GetCachedWidget(); Slate.IsValid()) Slate->Invalidate(EInvalidateWidgetReason::Paint);
            return;
        }
    }
}
void UColdSteelInventoryWidget::LoadIcons()
{
    RefreshPresentation();
    if(!Model)return;for(const auto& I:Model->Items()) {
        if(WeaponIcons&&WeaponIcons->Supports(I)){if(bWarehouse?(Model->InOpenStorage(I)&&I.Cell>=StorageStart()&&I.Cell<StorageStart()+ColdSteelWarehouse::CellsPerPage):(I.Place==0||I.Place==1))WeaponIcons->Request(I);}
        // Keep the catalog image available while a live weapon preview is pending or failed.
        if(Icons.Contains(I.Definition)||FailedIcons.Contains(I.Definition))continue;
        // Weapon artwork follows the current catalog even when an older saved item has no icon field.
        const FString File=WeaponIcons&&WeaponIcons->Supports(I)?TEXT("Icons/")+I.Definition+TEXT(".png"):Text(I,TEXT("ue_icon"));if(File.IsEmpty())continue;
        auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);
        // A failed import must be remembered: the source file is missing, so
        // retrying it on every refresh only repeats the disk probe, the engine
        // warning and a transient UTexture2D allocation that GC then has to reap.
        if(!Texture){FailedIcons.Add(I.Definition);continue;}
        Icons.Add(I.Definition,Texture);FSlateBrush Brush;Brush.SetResourceObject(Texture);Brush.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush.DrawAs=ESlateBrushDrawType::Image;
        if(const auto* P=Presentation.Find(I.InstanceId);P&&P->StaffArt)ColdSteelStaffIcon::FrameImportedTexture(Brush,Texture);
        IconBrushes.Add(I.Definition,Brush);
    }
    // Item data and asynchronous images are painted directly, outside child-widget bindings.
    if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
const FSlateBrush* UColdSteelInventoryWidget::ItemBrush(const FColdSteelItem& I) const
{
    if(WeaponIcons&&WeaponIcons->Supports(I))if(const auto* Preview=WeaponIcons->Find(I))return Preview;
    return IconBrushes.Find(I.Definition);
}
FIntPoint UColdSteelInventoryWidget::PendingFootprint(const FColdSteelItem& Item,const UColdSteelItemDrag& Drag)const
{
    const FIntPoint Stored(Item.Width,Item.Height);
    return Drag.bRotated==Item.bRotated?Stored:FIntPoint(Stored.Y,Stored.X);
}
void UColdSteelInventoryWidget::UpdateDragGhost(UColdSteelItemDrag& Drag,const FGeometry& G,FVector2D CursorPos)const
{
    auto* Visual=Drag.PointerVisual.Get();const auto* I=Model?Model->FindItem(Drag.ItemId):nullptr;
    if(!Visual||!I)return;
    const auto L=Layout(G);
    const FIntPoint Cells=PendingFootprint(*I,Drag);
    const FVector2D Rect(Cells.X*L.Cell,Cells.Y*L.Cell),CursorLocal=G.AbsoluteToLocal(CursorPos)*Scale;
    const FVector2D RectOrigin=CursorLocal-FVector2D(Drag.GrabNorm.X*Rect.X,Drag.GrabNorm.Y*Rect.Y);
    const auto* Brush=ItemBrush(*I);FVector2D ImageSize=Rect;
    const auto* P=Presentation.Find(I->InstanceId);const bool Staff=P&&P->StaffArt;
    if(Brush){
        // A turned ghost is drawn upright and rotated a quarter turn, so its box is transposed.
        const FVector2D Image=Brush->ImageSize;
        const double Fit=Drag.bRotated?FMath::Min((Rect.X-8)/FMath::Max(1.0,Image.Y),(Rect.Y-8)/FMath::Max(1.0,Image.X))
                                      :FMath::Min((Rect.X-8)/FMath::Max(1.0,Image.X),(Rect.Y-8)/FMath::Max(1.0,Image.Y));
        ImageSize=Image*Fit;
        if(Staff)ImageSize=ColdSteelStaffIcon::InventorySize(Image,Rect,Drag.bRotated);
    }
    const FVector2D ImageOrigin=RectOrigin+(Rect-ImageSize)*.5+FVector2D(0,Staff?6:(Drag.SourcePlace==0||Drag.SourcePlace==4)?2:0);
    const FVector2D ScreenOrigin=G.LocalToAbsolute(ImageOrigin/Scale);
    const FVector2D ScreenSize=G.LocalToAbsolute((ImageOrigin+ImageSize)/Scale)-ScreenOrigin;
    Visual->Configure(Brush,ScreenSize,CursorPos-ScreenOrigin,CursorPos,Drag.bRotated);
    if(auto Slate=Visual->GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
bool UColdSteelInventoryWidget::RotateDraggedItem(const FGeometry& G)
{
    auto Drag=ActivePointerDrag.Get();
    if(!Drag||!Model)return false;
    const auto* I=Model->FindItem(Drag->ItemId);
    // Backpack, warehouse, gear, and compartment may turn while carried; hotbar binds keep the authored shape.
    // Gear drops still ignore orientation — Move/Transfer only apply it into place 0 or 4.
    const bool bAllowed=I&&(Drag->SourcePlace==0||Drag->SourcePlace==1||Drag->SourcePlace==4||Drag->SourcePlace==ColdSteelCompartment::Place)&&CanRotate(*I)&&Drag->PointerVisual!=nullptr;
    if(!bAllowed)return false;
    Drag->bRotated=!Drag->bRotated;
    // Both grabs derive from the values captured at drag start, so turning back restores the anchor exactly
    // instead of accumulating a transpose/clamp each time.
    const bool bFlipped=Drag->bRotated!=I->bRotated;
    Drag->GrabNorm=bFlipped?FVector2D(Drag->BaseGrabNorm.Y,Drag->BaseGrabNorm.X):Drag->BaseGrabNorm;
    Drag->GrabOffset=bFlipped?FIntPoint(Drag->BaseGrabOffset.Y,Drag->BaseGrabOffset.X):Drag->BaseGrabOffset;
    const FVector2D CursorPos=FSlateApplication::Get().GetCursorPos();
    UpdateDragGhost(*Drag,G,CursorPos);
    // The board that owns the highlight may not be this one, and it may be hidden by the drag-out mode.
    if(auto Board=Drag->PreviewBoard.Get())Board->RefreshDragPreview(*Drag);
    if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
    return true;
}
void UColdSteelInventoryWidget::RefreshDragPreview(UColdSteelItemDrag& Drag)
{
    if(!Model)return;
    const FVector2D CursorPos=FSlateApplication::Get().GetCursorPos();
    const auto& G=GetCachedGeometry();
    // A board hidden by the drag-out mode still has valid cached geometry; keeping it evaluated means
    // a turn never leaves a stale rejection highlight behind.
    if(!G.IsUnderLocation(CursorPos)||G.GetLocalSize().IsNearlyZero()){ClearDragPreview();return;}
    PreviewItemDrag(Drag,CursorPos);
    if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
UColdSteelInventoryWidget::FBoardLayout UColdSteelInventoryWidget::Layout(const FGeometry& G)const
{
    FBoardLayout L;
    L.Width=FMath::Max(240.f,float(G.GetLocalSize().X*Scale));
    L.Cell=(L.Width-24)/18;
    if(bWarehouse){L.GearY=L.GearWidth=L.GearHeight=L.GearPitch=0;L.BagY=40;L.HotY=L.BagY+StorageRows()*L.Cell;L.Height=L.HotY+60;return L;}
    L.GearWidth=(L.Width-36)/3;
    int32 ViewWidth=0,ViewHeight=0;GetOwningPlayer()->GetViewportSize(ViewWidth,ViewHeight);
    L.GearHeight=ViewHeight<650?52.f:ViewHeight<850?60.f:76.f;
    L.GearY=32;L.GearPitch=L.GearHeight+6;
    L.BagY=L.GearY+5*L.GearPitch-6+48;
    L.HotY=L.BagY+StorageRows()*L.Cell;
    // 背包装备撑出夹层时，在反馈行下方追加"夹层"区块（标题行 36px + 网格）。
    // 网格尺寸（长×宽＝列×行）由装备的背包定义，区块高度随行数伸缩。
    const FIntPoint CompGrid=(!bWarehouse&&Model)?ColdSteelInventory::CompartmentGrid(Model->Items()):FIntPoint::ZeroValue;
    if(CompGrid.X>0&&CompGrid.Y>0)
    {
        L.CompGrid=CompGrid;
        L.CompY=L.HotY+70;
        L.Height=L.CompY+CompGrid.Y*L.Cell+8;
    }
    else L.Height=L.HotY+34;
    return L;
}
bool UColdSteelInventoryWidget::Hit(const FGeometry& G,FVector2D Screen,int32& Place,int32& Cell)const
{
    const auto L=Layout(G);const FVector2D P=G.AbsoluteToLocal(Screen)*Scale;Place=-1;Cell=-1;
    if(P.X<12||P.X>L.Width-12)return false;
    if(!bWarehouse&&P.Y>=L.GearY&&P.Y<L.GearY+5*L.GearPitch-6){
        const int32 Row=int32((P.Y-L.GearY)/L.GearPitch),Col=int32((P.X-12)/(L.GearWidth+6));
        if(Col>2||P.Y-L.GearY-Row*L.GearPitch>=L.GearHeight||P.X-12-Col*(L.GearWidth+6)>=L.GearWidth)return false;
        Place=1;Cell=Row*3+Col;return true;
    }
    if(P.Y>=L.BagY&&P.Y<L.BagY+StorageRows()*L.Cell){Place=StoragePlace();Cell=StorageStart()+int32((P.Y-L.BagY)/L.Cell)*18+FMath::Clamp(int32((P.X-12)/L.Cell),0,17);return true;}
    if(L.CompY>0&&P.Y>=L.CompY&&P.Y<L.CompY+L.CompGrid.Y*L.Cell&&P.X<12+L.CompGrid.X*L.Cell)
    {Place=ColdSteelCompartment::Place;Cell=int32((P.Y-L.CompY)/L.Cell)*L.CompGrid.X+FMath::Clamp(int32((P.X-12)/L.Cell),0,L.CompGrid.X-1);return true;}
    return false;
}
FString UColdSteelInventoryWidget::IdAt(int32 Place,int32 Cell)const
{
    if(!Model)return TEXT("");
    int32 N=Owner(Model->Items(),Place,Cell,Model->ActiveContainer);return N>=0?Model->Items()[N].InstanceId:TEXT("");
}
FReply UColdSteelInventoryWidget::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    PendingTooltip.Empty();bPendingClick=false;SetKeyboardFocus();LoadIcons();const auto L=Layout(G);FVector2D P=G.AbsoluteToLocal(E.GetScreenSpacePosition())*Scale;
    if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);
    if(Hit(G,E.GetScreenSpacePosition(),PressPlace,PressCell)){
        FocusPlace=PressPlace;FocusCell=PressCell;Selected=IdAt(PressPlace,PressCell);bConfirmDrop=false;InteractionMessage.Empty();
        if(E.GetEffectingButton()==EKeys::RightMouseButton){
            if(E.IsShiftDown()&&!Selected.IsEmpty())OpenItemMenu(E.GetScreenSpacePosition());
            else if(!Selected.IsEmpty())Model->DefaultAction(Selected);
            InteractionMessage=Model->ResultMessage();return FReply::Handled();
        }
        if(!Selected.IsEmpty()&&E.GetEffectingButton()==EKeys::LeftMouseButton){PressedItem=Selected;PressPosition=E.GetScreenSpacePosition();bPendingClick=true;return FReply::Handled().DetectDrag(TakeWidget(),EKeys::LeftMouseButton);}
        return FReply::Handled();
    }
    // 整理按钮共用迁移自原项目 gamedev 的 uiCues.buttonClick 确认音。
    auto PlaySortClick=[this](){if(auto* S=LoadObject<USoundBase>(nullptr,TEXT("/Game/Audio/GamedevUI20261002/S_Button_Click.S_Button_Click")))UGameplayStatics::PlaySound2D(this,S,1.f,1.f);};
    if(E.GetEffectingButton()==EKeys::LeftMouseButton&&P.X>=L.Width-60&&P.X<L.Width-12&&P.Y>=L.BagY-30&&P.Y<L.BagY-6){PlaySortClick();PerformAction(3);}
    if(E.GetEffectingButton()==EKeys::LeftMouseButton&&bCompSortHovered){PlaySortClick();PerformAction(8);}
    return FReply::Handled();
}
FReply UColdSteelInventoryWidget::NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E)
{
    const bool Click=bPendingClick&&E.GetEffectingButton()==EKeys::LeftMouseButton&&FVector2D::Distance(PressPosition,E.GetScreenSpacePosition())<6;
    bPendingClick=false;int32 Place=-1,Cell=-1;
    if(Click&&Hit(G,E.GetScreenSpacePosition(),Place,Cell)&&IdAt(Place,Cell)==PressedItem){
        if(E.IsShiftDown()&&(Place==0||Place==4||Place==ColdSteelCompartment::Place))OpenItemMenu(E.GetScreenSpacePosition(),true);
        else if(auto* HUD=TooltipHUD())HUD->ShowItemTooltip(PressedItem,E.GetScreenSpacePosition(),true,this);
    }
    return FReply::Handled();
}
FReply UColdSteelInventoryWidget::NativeOnMouseButtonDoubleClick(const FGeometry& G,const FPointerEvent& E){bPendingClick=false;if(E.GetEffectingButton()!=EKeys::LeftMouseButton)return FReply::Unhandled();if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);int32 P,C;if(Hit(G,E.GetScreenSpacePosition(),P,C)){Selected=IdAt(P,C);if(!Selected.IsEmpty())Model->DefaultAction(Selected);InteractionMessage=Model->ResultMessage();}return FReply::Handled();}
void UColdSteelInventoryWidget::PerformAction(int32 Action)
{
    if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);
    if(!Model)return;
    const auto L=Layout(GetCachedGeometry());
    if(Action==7)if(const auto* I=Model->FindItem(Selected))if(GetGameInstance()->GetSubsystem<UGunsmithSystem>()->ModifiableWeapon(I->Definition))
    {if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->OpenGunsmith(Selected);return;}
    switch(Action){case 0:Model->DefaultAction(Selected);break;case 1:OpenItemMenu(GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale),true);break;case 2:if(bConfirmDrop){Model->Drop(Selected);bConfirmDrop=false;}else bConfirmDrop=true;break;case 3:if(bWarehouse)Model->SortWarehouse(TEXT("category"));else Model->Sort();break;case 4:if(auto* HUD=TooltipHUD()){HUD->ShowItemTooltip(Selected,GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale),true,this);HUD->FocusItemTooltip();}break;case 5:OpenItemMenu(GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale));break;case 6:Model->SaveNow();break;case 7:Selected.Empty();bConfirmDrop=false;break;case 8:Model->SortCompartment();break;}
    InteractionMessage=bConfirmDrop?TEXT("再次按 Delete 确认丢下，Esc 取消"):Model->ResultMessage();LoadIcons();
}
FReply UColdSteelInventoryWidget::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape&&bConfirmDrop){bConfirmDrop=false;InteractionMessage.Empty();return FReply::Handled();}
    if(E.GetKey()==EKeys::Escape&&!KeyboardCarry.IsEmpty()){KeyboardCarry.Empty();PreviewPlace=-1;return FReply::Handled();}
    if(E.GetKey()==EKeys::J||E.GetKey()==EKeys::K){
        if(const auto* I=Model->FindItem(Selected)){
            if(E.GetKey()==EKeys::J&&!GetGameInstance()->GetSubsystem<UGunsmithSystem>()->ModifiableWeapon(I->Definition))return FReply::Handled();
            const FString Id=I->InstanceId;
            if(I->Place==4&&!Model->TransferWarehouse(Id,0)){InteractionMessage=Model->ResultMessage();return FReply::Handled();}
            if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer())){if(E.GetKey()==EKeys::J)PC->OpenGunsmith(Id);else PC->OpenEnhancement(Id);}
        }return FReply::Handled();
    }
    if(E.GetKey()==EKeys::F1){if(auto* HUD=TooltipHUD()){HUD->ShowItemTooltip(Selected,G.LocalToAbsolute(FVector2D(12,28)/Scale),true,this);HUD->FocusItemTooltip();}return FReply::Handled();}
    const FKey K=E.GetKey();
    // While a pointer drag is in flight F turns the carried item a quarter turn.
    if(K==EKeys::F&&!E.IsRepeat()&&ActivePointerDrag.IsValid())
    {
        if(RotateDraggedItem(G))return FReply::Handled();
    }
    if(K==EKeys::Enter){PerformAction(0);return FReply::Handled();}if(K==EKeys::X){PerformAction(1);return FReply::Handled();}if(K==EKeys::Delete){PerformAction(2);return FReply::Handled();}
    // G 已从键盘轮换武器改为符文长剑飞剑专用（面板内也不再消费它）。
    if(K==EKeys::SpaceBar){if(KeyboardCarry.IsEmpty())KeyboardCarry=IdAt(FocusPlace,FocusCell);else {const bool OK=DropAt(KeyboardCarry,FocusPlace,FocusCell);InteractionMessage=Model->ResultMessage();if(OK){KeyboardCarry.Empty();PreviewPlace=-1;}}return FReply::Handled();}
    if(K==EKeys::F){FocusPlace=bWarehouse?4:(FocusPlace==0?1:FocusPlace==1?(Model&&ColdSteelInventory::CompartmentCells(Model->Items())>0?ColdSteelCompartment::Place:0):0);FocusCell=StorageStart();}
    else if(K==EKeys::Left||K==EKeys::Right||K==EKeys::Up||K==EKeys::Down){const FIntPoint CompGrid=Model?CompartmentGrid(Model->Items()):FIntPoint::ZeroValue;int32 Columns=(FocusPlace==0||FocusPlace==4)?18:FocusPlace==1?3:CompGrid.X;FocusCell+=K==EKeys::Left?-1:K==EKeys::Right?1:K==EKeys::Up?-Columns:Columns;FocusCell=FMath::Clamp(FocusCell,StorageStart(),bWarehouse?StorageStart()+ColdSteelWarehouse::CellsPerPage-1:FocusPlace==0?StorageRows()*18-1:FocusPlace==1?14:FMath::Max(0,CompGrid.X*CompGrid.Y-1));}
    else return Super::NativeOnKeyDown(G,E);
    Selected=IdAt(FocusPlace,FocusCell);bConfirmDrop=false;bKeyboardTooltip=true;
    if(bWarehouse)if(auto* Scroll=Cast<UScrollBox>(GetParent())){
        const auto View=Scroll->GetCachedGeometry();const auto L=Layout(G);
        const auto Point=View.AbsoluteToLocal(G.LocalToAbsolute(FVector2D(12,L.BagY+(FocusCell-StorageStart())/18*L.Cell)/Scale));
        const float Bottom=Point.Y+L.Cell/Scale,Margin=12/Scale;
        if(Point.Y<Margin)Scroll->SetScrollOffset(Scroll->GetScrollOffset()+Point.Y-Margin);
        else if(Bottom>View.GetLocalSize().Y-Margin)Scroll->SetScrollOffset(Scroll->GetScrollOffset()+Bottom-View.GetLocalSize().Y+Margin);
    }
    if(auto* HUD=TooltipHUD()){if(KeyboardCarry.IsEmpty()&&!Selected.IsEmpty())HUD->ShowItemTooltip(Selected,G.LocalToAbsolute(FVector2D(12,28)/Scale),false,this);else HUD->HideItemTooltip(true);}
    HoverPreview=KeyboardCarry;PreviewPlace=FocusPlace;PreviewCell=FocusCell;SwapDestinations.Empty();PreviewReason.Empty();
    if(const auto* Carried=Model->FindItem(KeyboardCarry))PreviewCells=FIntPoint(Carried->Width,Carried->Height);else PreviewCells=FIntPoint(1,1);
    if(KeyboardCarry.IsEmpty())bPreviewValid=true;
    else bPreviewValid=Model->ProposeMove(KeyboardCarry,FocusPlace,FocusCell).bValid;
    return FReply::Handled();
}
void UColdSteelInventoryWidget::NativeOnDragDetected(const FGeometry& G,const FPointerEvent& E,UDragDropOperation*& Out)
{
    bPendingClick=false;if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);
    const auto* I=Model->FindItem(Selected);if(!I||IdAt(PressPlace,PressCell)!=Selected)return;
    auto* Drag=NewObject<UColdSteelItemDrag>(this);Drag->ItemId=Selected;Drag->SourceBoard=this;
    Drag->SourcePlace=I->Place;Drag->SourceCell=I->Cell;Drag->SourceSnapshot=*I;Drag->bHasSourceSnapshot=true;
    const auto L=Layout(G);const FVector2D Press=G.AbsoluteToLocal(PressPosition)*Scale;
    // 夹层折行按装备定义的列数：抓取偏移数值仍是"物品占用矩形内的格偏移"，与转向转置兼容。
    if(PressPlace==0||PressPlace==4)Drag->GrabOffset=FIntPoint(PressCell%18-I->Cell%18,PressCell/18-I->Cell/18);
    else if(PressPlace==ColdSteelCompartment::Place)Drag->GrabOffset=FIntPoint(PressCell%L.CompGrid.X-I->Cell%L.CompGrid.X,PressCell/L.CompGrid.X-I->Cell/L.CompGrid.X);
    FVector2D Origin(12+I->Cell%18*L.Cell,L.BagY+(I->Cell-StorageStart())/18*L.Cell),Size(I->Width*L.Cell,I->Height*L.Cell);
    if(PressPlace==ColdSteelCompartment::Place)Origin=FVector2D(12+I->Cell%L.CompGrid.X*L.Cell,L.CompY+I->Cell/L.CompGrid.X*L.Cell);
    if(PressPlace==1){Origin=FVector2D(12+PressCell%3*(L.GearWidth+6),L.GearY+PressCell/3*L.GearPitch);Size=FVector2D(L.GearWidth,L.GearHeight);}
    const FVector2D Grab(FMath::Clamp((Press.X-Origin.X)/Size.X,0.0,1.0),FMath::Clamp((Press.Y-Origin.Y)/Size.Y,0.0,1.0));
    if(PressPlace==1)Drag->GrabOffset=FIntPoint(FMath::Min(I->Width-1,int32(Grab.X*I->Width)),FMath::Min(I->Height-1,int32(Grab.Y*I->Height)));
    Drag->PointerVisual=CreateWidget<UColdSteelDragVisual>(GetOwningPlayer());
    Drag->PointerVisual->AddToViewport(1000);
    Drag->GrabNorm=Grab;Drag->BaseGrabNorm=Grab;Drag->BaseGrabOffset=Drag->GrabOffset;Drag->bRotated=I->bRotated;
    UpdateDragGhost(*Drag,G,E.GetScreenSpacePosition());
    ActivePointerDrag=Drag;
    // Suppress UMG's 150ms source-widget-origin interpolation; only the overlay is visible.
    auto* Empty=NewObject<USizeBox>(this);Empty->SetVisibility(ESlateVisibility::HitTestInvisible);
    Drag->DefaultDragVisual=Empty;Drag->Pivot=EDragPivot::TopLeft;Drag->Offset=FVector2D::ZeroVector;
    DraggedItem=Selected;Out=Drag;
    if(auto* HUD=TooltipHUD()){Drag->SourceHUD=HUD;HUD->BeginInventoryDrag(Drag);}
}
bool UColdSteelInventoryWidget::NativeOnDragOver(const FGeometry& G,const FDragDropEvent& E,UDragDropOperation* O)
{
    auto* D=Cast<UColdSteelItemDrag>(O);
    if(!D){bPreviewValid=false;PreviewReason.Empty();SwapDestinations.Empty();PreviewPlace=-1;return false;}
    D->PreviewBoard=this;
    return PreviewItemDrag(*D,E.GetScreenSpacePosition());
}
bool UColdSteelInventoryWidget::PreviewItemDrag(UColdSteelItemDrag& D,FVector2D Screen)
{
    const auto G=GetCachedGeometry();
    bPreviewValid=false;PreviewReason.Empty();SwapDestinations.Empty();
    if(!Hit(G,Screen,PreviewPlace,PreviewCell)){PreviewPlace=-1;return false;}
    HoverPreview=D.ItemId;const auto* Source=Model->FindItem(D.ItemId);
    if(!Source)return false;
    if(!D.IsCurrent(Model)){PreviewReason=TEXT("物品已变化，请重新拖动");return true;}
    const int32 Orientation=D.bRotated?1:0;
    PreviewCells=PendingFootprint(*Source,D);
    // Hint only over bag/warehouse grids. Gear targets keep authored shape on drop.
    bPreviewRotatable=(PreviewPlace==0||PreviewPlace==4||PreviewPlace==ColdSteelCompartment::Place)&&(D.SourcePlace==0||D.SourcePlace==1||D.SourcePlace==4||D.SourcePlace==ColdSteelCompartment::Place)&&CanRotate(*Source);
    if(PreviewPlace==0||PreviewPlace==4){
        const int32 TargetPlace=PreviewPlace,Start=StorageStart();
        // Firearms become 2x5 when turned, which no backpack row set can hold; say that plainly rather
        // than reporting an anchor/overlap rejection for every hovered cell.
        const int32 Rows=StorageRows();
        if(PreviewCells.Y>Rows||PreviewCells.X>18)
        {
            bPreviewValid=false;
            PreviewReason=FString::Printf(TEXT("这个方向需要 %d 行，%s只有 %d 行"),PreviewCells.Y,TargetPlace==4?TEXT("仓库"):TEXT("背包"),Rows);
            return true;
        }
        const int32 HoverCell=PreviewCell;
        // Clamp the grab anchor so the whole footprint stays inside this container. Hovering the outer
        // cells then places the item as far out as it fits instead of rejecting every edge hover with
        // "物品超出背包边界，请向内移动" (which reads as a broken drop even though the rules are unchanged).
        const int32 MaxColumn=FMath::Max(0,18-PreviewCells.X),MaxRow=FMath::Max(0,Rows-PreviewCells.Y);
        const int32 X=FMath::Clamp(HoverCell%18-D.GrabOffset.X,0,MaxColumn);
        const int32 Y=FMath::Clamp((HoverCell-Start)/18-D.GrabOffset.Y,0,MaxRow);
        PreviewCell=Start+Y*18+X;
        auto Proposal=Model->ProposeMove(D.ItemId,TargetPlace,PreviewCell,Orientation);
        // Keep normal grab-offset placement; retry at an occupied target's anchor only
        // if the original proposal fails and the same inventory rules accept the swap.
        if(!Proposal.bValid){const int32 N=Owner(Model->Items(),TargetPlace,HoverCell,Model->ActiveContainer);if(N>=0&&Model->Items()[N].InstanceId!=D.ItemId){
            const int32 Target=Model->Items()[N].Cell;const auto Swap=Model->ProposeMove(D.ItemId,TargetPlace,Target,Orientation);
            if(Swap.bValid){PreviewCell=Target;Proposal=Swap;}else Proposal.Reason=Swap.Reason;
        }}
        bPreviewValid=Proposal.bValid;PreviewReason=Proposal.bValid?TEXT("松开放置 / 交换物品"):Proposal.Reason;
        if(Proposal.bValid)for(const auto& I:Proposal.Items)if(I.Place==TargetPlace&&I.Cell>=Start&&I.Cell<Start+StorageRows()*18&&I.InstanceId!=D.ItemId){
            const auto* Before=Model->FindItem(I.InstanceId);
            if(Before&&(Before->Place!=I.Place||Before->Cell!=I.Cell))SwapDestinations.Add(FIntRect(I.Cell%18,(I.Cell-Start)/18,I.Cell%18+I.Width,(I.Cell-Start)/18+I.Height));
        }
        if(!SwapDestinations.IsEmpty())PreviewReason=FString::Printf(TEXT("松开交换 %d 件物品 · 高亮框为回填位置"),SwapDestinations.Num());
        if(D.SourcePlace==1&&TargetPlace==4)for(const auto& Worn:Proposal.Items)if(Worn.Place==1&&Worn.Cell==D.SourceCell&&Worn.InstanceId!=D.ItemId){PreviewReason=TEXT("松开替换装备");break;}
    }
    else if(PreviewPlace==ColdSteelCompartment::Place){
        const FIntPoint CompGrid=CompartmentGrid(Model->Items());
        if(PreviewCells.X>CompGrid.X||PreviewCells.Y>CompGrid.Y)
        {
            bPreviewValid=false;
            PreviewReason=FString::Printf(TEXT("这个朝向需要 %d×%d 格，夹层只有 %d×%d"),PreviewCells.X,PreviewCells.Y,CompGrid.X,CompGrid.Y);
            return true;
        }
        const int32 HoverCell=PreviewCell;
        // 与背包同口径：高亮框按抓取锚对齐拖动贴图（贴图左上角=夹取后的落点），
        // 光标停在外层格时整件物品贴边；悬停在被占格上则换到该物品锚点预览交换。
        const int32 MaxColumn=FMath::Max(0,CompGrid.X-PreviewCells.X),MaxRow=FMath::Max(0,CompGrid.Y-PreviewCells.Y);
        const int32 X=FMath::Clamp(HoverCell%CompGrid.X-D.GrabOffset.X,0,MaxColumn);
        const int32 Y=FMath::Clamp(HoverCell/CompGrid.X-D.GrabOffset.Y,0,MaxRow);
        PreviewCell=Y*CompGrid.X+X;
        auto Proposal=Model->ProposeMove(D.ItemId,PreviewPlace,PreviewCell,Orientation);
        if(!Proposal.bValid){const int32 N=Owner(Model->Items(),PreviewPlace,HoverCell);if(N>=0&&Model->Items()[N].InstanceId!=D.ItemId){
            const int32 Target=Model->Items()[N].Cell;const auto Swap=Model->ProposeMove(D.ItemId,PreviewPlace,Target,Orientation);
            if(Swap.bValid){PreviewCell=Target;Proposal=Swap;}else Proposal.Reason=Swap.Reason;
        }}
        bPreviewValid=Proposal.bValid;PreviewReason=Proposal.bValid?TEXT("松开放入夹层"):Proposal.Reason;
    }
    else
    {
        const auto Proposal=Model->ProposeMove(D.ItemId,PreviewPlace,PreviewCell,Orientation);
        bPreviewValid=Proposal.bValid;PreviewReason=Proposal.bValid?TEXT("松开放置 / 交换物品"):Proposal.Reason;
        bool Turned=false;
        if(Proposal.bValid&&PreviewPlace==1&&D.SourcePlace==0)for(const auto& I:Proposal.Items)if(I.Place==0)
        {
            const auto* Before=Model->FindItem(I.InstanceId);
            if(Before&&Before->Place==1)
            {
                SwapDestinations.Add(FIntRect(I.Cell%18,I.Cell/18,I.Cell%18+I.Width,I.Cell/18+I.Height));
                Turned|=Before->bRotated!=I.bRotated;
            }
        }
        if(!SwapDestinations.IsEmpty())PreviewReason=Turned?TEXT("松开替换装备 · 自动转向并放入高亮位置"):TEXT("松开替换装备 · 高亮框为旧装备回填位置");
    }
    return true;
}
bool UColdSteelInventoryWidget::DropAt(const FString& Id,int32 Place,int32 Cell,int32 Orientation){return Model->MoveItem(Id,Place,Cell,Orientation);}
bool UColdSteelInventoryWidget::NativeOnDrop(const FGeometry& G,const FDragDropEvent& E,UDragDropOperation* O)
{
    auto* D=Cast<UColdSteelItemDrag>(O);if(!D||!NativeOnDragOver(G,E,O))return false;bool Result=false;
    if(bPreviewValid)Result=DropAt(D->ItemId,PreviewPlace,PreviewCell,D->bRotated?1:0);
    InteractionMessage=Result?TEXT("物品操作已保存"):bPreviewValid?Model->ResultMessage():PreviewReason;
    PreviewPlace=-1;LoadIcons();return true;
}
void UColdSteelInventoryWidget::NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*){ClearDragPreview();}

UColdSteelHUDWidget* UColdSteelInventoryWidget::TooltipHUD()const{return StorageHUD.IsValid()?StorageHUD.Get():GetParent()?GetParent()->GetTypedOuter<UColdSteelHUDWidget>():nullptr;}
FReply UColdSteelInventoryWidget::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E)
{
    if(E.GetCursorDelta().IsNearlyZero())return Super::NativeOnMouseMove(G,E);
    bKeyboardTooltip=false;int32 Place,Cell;
    Hit(G,E.GetScreenSpacePosition(),HoverPlace,PointerCell);const auto L=Layout(G);const auto Local=G.AbsoluteToLocal(E.GetScreenSpacePosition())*Scale;
    bSortHovered=Local.X>=L.Width-60&&Local.X<L.Width-12&&Local.Y>=L.BagY-30&&Local.Y<L.BagY-6;
    bCompSortHovered=L.CompY>0&&Local.X>=L.Width-60&&Local.X<L.Width-12&&Local.Y>=L.CompY-30&&Local.Y<L.CompY-6;
    if(auto* HUD=TooltipHUD()){
        if(bPendingClick||FSlateApplication::Get().IsDragDropping()||!KeyboardCarry.IsEmpty()){PendingTooltip.Empty();HUD->HideItemTooltip(true);return FReply::Handled();}
        const FString Id=Hit(G,E.GetScreenSpacePosition(),Place,Cell)?IdAt(Place,Cell):TEXT("");
        if(Id!=PendingTooltip){PendingTooltip=Id;TooltipAnchor=E.GetScreenSpacePosition();TooltipHoverTime=0;bHoverTooltipShown=false;HUD->HideItemTooltip();}
        if(Id.IsEmpty())HUD->HideItemTooltip();
    }
    return FReply::Handled();
}
void UColdSteelInventoryWidget::NativeOnMouseLeave(const FPointerEvent& E){Super::NativeOnMouseLeave(E);PendingTooltip.Empty();HoverPlace=-1;PointerCell=-1;bSortHovered=false;bCompSortHovered=false;if(!bKeyboardTooltip)if(auto* HUD=TooltipHUD())HUD->HideItemTooltip();}
void UColdSteelInventoryWidget::NativeOnFocusLost(const FFocusEvent& E){Super::NativeOnFocusLost(E);bKeyboardTooltip=false;if(!IsHovered())if(auto* HUD=TooltipHUD())HUD->HideItemTooltip();}
