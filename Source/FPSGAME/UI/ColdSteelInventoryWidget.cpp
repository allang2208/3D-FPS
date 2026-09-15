#include "ColdSteelInventoryWidget.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelDragVisual.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/SizeBox.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
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
int32 UColdSteelInventoryWidget::StorageRows()const{return bWarehouse?ColdSteelWarehouse::Rows:4;}
void UColdSteelInventoryWidget::ResetStoragePage(){CancelInteraction();FocusPlace=StoragePlace();FocusCell=StorageStart();HoverPlace=-1;PointerCell=-1;LoadIcons();}
void UColdSteelItemDrag::ReleaseVisual(){if(PointerVisual)PointerVisual->RemoveFromParent();PointerVisual=nullptr;}
void UColdSteelItemDrag::Drop_Implementation(const FPointerEvent& E){ReleaseVisual();if(SourceHUD.IsValid())SourceHUD->EndInventoryDrag();if(SourceBoard.IsValid())SourceBoard->FinishDrag();Super::Drop_Implementation(E);}
void UColdSteelItemDrag::DragCancelled_Implementation(const FPointerEvent& E){ReleaseVisual();if(SourceHUD.IsValid())SourceHUD->EndInventoryDrag();if(SourceBoard.IsValid())SourceBoard->FinishDrag();Super::DragCancelled_Implementation(E);}
void UColdSteelItemDrag::Dragged_Implementation(const FPointerEvent& E){if(PointerVisual)PointerVisual->MoveTo(E.GetScreenSpacePosition());if(SourceHUD.IsValid())SourceHUD->UpdateInventoryDrag(this,E.GetScreenSpacePosition());Super::Dragged_Implementation(E);}
void UColdSteelInventoryWidget::FinishDrag(){if(auto Drag=ActivePointerDrag.Get())Drag->ReleaseVisual();ActivePointerDrag.Reset();if(auto* HUD=TooltipHUD())HUD->EndInventoryDrag();DraggedItem.Empty();bPendingClick=false;PreviewPlace=-1;}
void UColdSteelInventoryWidget::CancelInteraction(){PendingTooltip.Empty();FinishDrag();Selected.Empty();KeyboardCarry.Empty();KeyboardHotbar=-1;bConfirmDrop=false;InteractionMessage.Empty();if(ItemMenu)ItemMenu->Close(false);ItemMenu=nullptr;}
void UColdSteelInventoryWidget::OpenItemMenu(FVector2D Anchor,bool SplitOnly){if(ItemMenu)ItemMenu->Close(false);if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);ItemMenu=CreateWidget<UColdSteelInventoryPopup>(GetOwningPlayer());ItemMenu->Open(this,Model,Selected,Anchor,SplitOnly);}

void UColdSteelInventoryWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);Scale=ColdSteelUI::PixelScale(this);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    WeaponIcons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    if(!WidgetTree->RootWidget){auto* Size=WidgetTree->ConstructWidget<USizeBox>();WidgetTree->RootWidget=Size;}
    SetVisibility(ESlateVisibility::Visible);LoadIcons();
}
void UColdSteelInventoryWidget::NativeConstruct(){Super::NativeConstruct();if(Model&&!ModelHandle.IsValid())ModelHandle=Model->OnChanged.AddUObject(this,&ThisClass::LoadIcons);if(WeaponIcons&&!IconHandle.IsValid())IconHandle=WeaponIcons->OnReady.AddUObject(this,&ThisClass::LoadIcons);LoadIcons();}
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
void UColdSteelInventoryWidget::LoadIcons()
{
    RefreshPresentation();
    if(!Model)return;for(const auto& I:Model->Items()) {
        if(WeaponIcons&&WeaponIcons->Supports(I)){if(bWarehouse?(I.Place==4&&I.Cell>=StorageStart()&&I.Cell<StorageStart()+ColdSteelWarehouse::CellsPerPage):(I.Place==0||I.Place==1))WeaponIcons->Request(I);}
        // Keep the catalog image available while a live weapon preview is pending or failed.
        if(Icons.Contains(I.Definition))continue;
        // Weapon artwork follows the current catalog even when an older saved item has no icon field.
        const FString File=WeaponIcons&&WeaponIcons->Supports(I)?TEXT("Icons/")+I.Definition+TEXT(".png"):Text(I,TEXT("ue_icon"));if(File.IsEmpty())continue;
        auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);if(!Texture)continue;
        Icons.Add(I.Definition,Texture);FSlateBrush Brush;Brush.SetResourceObject(Texture);Brush.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush.DrawAs=ESlateBrushDrawType::Image;IconBrushes.Add(I.Definition,Brush);
    }
    for(const auto& B:Model->QuickBindings())
    {
        const auto* Skill=Model->QuickSkillDefinition(B.Skill);
        const FString Key=Skill?TEXT("@skill:")+B.Skill.ToString():B.ItemDefinition;
        if(Key.IsEmpty()||Icons.Contains(Key))continue;
        const FString File=Skill?Skill->Icon:Text(Model->CreateItem(B.ItemDefinition),TEXT("ue_icon"));
        if(File.IsEmpty())continue;
        auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);if(!Texture)continue;
        Icons.Add(Key,Texture);FSlateBrush Brush;Brush.SetResourceObject(Texture);Brush.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush.DrawAs=ESlateBrushDrawType::Image;IconBrushes.Add(Key,Brush);
    }
    // Item data and asynchronous images are painted directly, outside child-widget bindings.
    if(auto Slate=GetCachedWidget();Slate.IsValid())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
const FSlateBrush* UColdSteelInventoryWidget::ItemBrush(const FColdSteelItem& I) const
{
    if(WeaponIcons&&WeaponIcons->Supports(I))if(const auto* Preview=WeaponIcons->Find(I))return Preview;
    return IconBrushes.Find(I.Definition);
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
    L.HotY=L.BagY+4*L.Cell+32;
    L.Height=L.HotY+46+48;
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
    if(!bWarehouse&&P.Y>=L.HotY&&P.Y<L.HotY+46&&P.X<12+4*54){Place=3;Cell=int32((P.X-12)/54);return true;}
    return false;
}
FString UColdSteelInventoryWidget::IdAt(int32 Place,int32 Cell)const
{
    if(!Model)return TEXT("");if(Place==3){auto* I=Model->ResolveHotbar(Cell);return I?I->InstanceId:Model->QuickBinding(Cell+ColdSteelQuickBar::ItemOffset).IsEmpty()?TEXT(""):FString::Printf(TEXT("@quick:%d"),Cell);}
    int32 N=Owner(Model->Items(),Place,Cell);return N>=0?Model->Items()[N].InstanceId:TEXT("");
}
FReply UColdSteelInventoryWidget::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    PendingTooltip.Empty();bPendingClick=false;SetKeyboardFocus();LoadIcons();const auto L=Layout(G);FVector2D P=G.AbsoluteToLocal(E.GetScreenSpacePosition())*Scale;
    if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);
    if(Hit(G,E.GetScreenSpacePosition(),PressPlace,PressCell)){
        FocusPlace=PressPlace;FocusCell=PressCell;Selected=IdAt(PressPlace,PressCell);bConfirmDrop=false;InteractionMessage.Empty();
        if(E.GetEffectingButton()==EKeys::RightMouseButton){
            if(PressPlace==3)Model->BindHotbar(PressCell,TEXT(""));
            else if(E.IsShiftDown()&&!Selected.IsEmpty())OpenItemMenu(E.GetScreenSpacePosition());
            else if(!Selected.IsEmpty())Model->DefaultAction(Selected);
            InteractionMessage=Model->ResultMessage();return FReply::Handled();
        }
        if(!Selected.IsEmpty()&&E.GetEffectingButton()==EKeys::LeftMouseButton){PressedItem=Selected;PressPosition=E.GetScreenSpacePosition();bPendingClick=true;return FReply::Handled().DetectDrag(TakeWidget(),EKeys::LeftMouseButton);}
        return FReply::Handled();
    }
    if(E.GetEffectingButton()==EKeys::LeftMouseButton&&P.X>=L.Width-60&&P.X<L.Width-12&&P.Y>=L.BagY-30&&P.Y<L.BagY-6)PerformAction(3);
    return FReply::Handled();
}
FReply UColdSteelInventoryWidget::NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E)
{
    const bool Click=bPendingClick&&E.GetEffectingButton()==EKeys::LeftMouseButton&&FVector2D::Distance(PressPosition,E.GetScreenSpacePosition())<6;
    bPendingClick=false;int32 Place=-1,Cell=-1;
    if(Click&&Hit(G,E.GetScreenSpacePosition(),Place,Cell)&&IdAt(Place,Cell)==PressedItem){
        if(E.IsShiftDown()&&(Place==0||Place==4))OpenItemMenu(E.GetScreenSpacePosition(),true);
        else if(auto* HUD=TooltipHUD())HUD->ShowItemTooltip(PressedItem,E.GetScreenSpacePosition(),true,this);
    }
    return FReply::Handled();
}
FReply UColdSteelInventoryWidget::NativeOnMouseButtonDoubleClick(const FGeometry& G,const FPointerEvent& E){bPendingClick=false;if(E.GetEffectingButton()!=EKeys::LeftMouseButton)return FReply::Unhandled();if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);int32 P,C;if(Hit(G,E.GetScreenSpacePosition(),P,C)){Selected=IdAt(P,C);if(P==3)Model->UseHotbar(C);else Model->DefaultAction(Selected);InteractionMessage=Model->ResultMessage();}return FReply::Handled();}
void UColdSteelInventoryWidget::PerformAction(int32 Action)
{
    if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);
    if(!Model)return;
    const auto L=Layout(GetCachedGeometry());
    if(Action==7)if(const auto* I=Model->FindItem(Selected))if((I->Definition==TEXT("ue_m4a1")||I->Definition==TEXT("ue_akm")||I->Definition==TEXT("ue_qbz191")||(I->Definition==TEXT("ue_m1911")||I->Definition==TEXT("ue_dan_wesson715"))))
    {if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->OpenGunsmith(Selected);return;}
    switch(Action){case 0:Model->DefaultAction(Selected);break;case 1:OpenItemMenu(GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale),true);break;case 2:if(bConfirmDrop){Model->Drop(Selected);bConfirmDrop=false;}else bConfirmDrop=true;break;case 3:if(bWarehouse)Model->SortWarehouse(TEXT("category"));else Model->Sort();break;case 4:if(auto* HUD=TooltipHUD()){HUD->ShowItemTooltip(Selected,GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale),true,this);HUD->FocusItemTooltip();}break;case 5:OpenItemMenu(GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale));break;case 6:Model->SaveNow();break;case 7:Selected.Empty();bConfirmDrop=false;break;}
    InteractionMessage=bConfirmDrop?TEXT("再次按 Delete 确认丢下，Esc 取消"):Model->ResultMessage();LoadIcons();
}
FReply UColdSteelInventoryWidget::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape&&bConfirmDrop){bConfirmDrop=false;InteractionMessage.Empty();return FReply::Handled();}
    if(E.GetKey()==EKeys::Escape&&!KeyboardCarry.IsEmpty()){KeyboardCarry.Empty();KeyboardHotbar=-1;PreviewPlace=-1;return FReply::Handled();}
    if(E.GetKey()==EKeys::J||E.GetKey()==EKeys::K){
        if(const auto* I=Model->FindItem(Selected)){
            if(E.GetKey()==EKeys::J&&I->Definition!=TEXT("ue_m4a1")&&I->Definition!=TEXT("ue_akm")&&I->Definition!=TEXT("ue_qbz191")&&I->Definition!=TEXT("ue_m1911")&&I->Definition!=TEXT("ue_dan_wesson715"))return FReply::Handled();
            const FString Id=I->InstanceId;
            if(I->Place==4&&!Model->TransferWarehouse(Id,0)){InteractionMessage=Model->ResultMessage();return FReply::Handled();}
            if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer())){if(E.GetKey()==EKeys::J)PC->OpenGunsmith(Id);else PC->OpenEnhancement(Id);}
        }return FReply::Handled();
    }
    if(E.GetKey()==EKeys::F1){if(auto* HUD=TooltipHUD()){HUD->ShowItemTooltip(Selected,G.LocalToAbsolute(FVector2D(12,28)/Scale),true,this);HUD->FocusItemTooltip();}return FReply::Handled();}
    const FKey K=E.GetKey();if(K==EKeys::Enter){PerformAction(0);return FReply::Handled();}if(K==EKeys::X){PerformAction(1);return FReply::Handled();}if(K==EKeys::Delete){PerformAction(2);return FReply::Handled();}
    if(K==EKeys::G){Model->CycleWeapon();return FReply::Handled();}
    if(K==EKeys::SpaceBar){if(KeyboardCarry.IsEmpty()){KeyboardCarry=IdAt(FocusPlace,FocusCell);KeyboardHotbar=FocusPlace==3?FocusCell:-1;}else {const bool OK=KeyboardHotbar>=0?(FocusPlace==3?Model->SwapHotbar(KeyboardHotbar,FocusCell):FocusPlace==0&&Model->BindHotbar(KeyboardHotbar,TEXT(""))):DropAt(KeyboardCarry,FocusPlace,FocusCell);InteractionMessage=Model->ResultMessage();if(OK){KeyboardCarry.Empty();KeyboardHotbar=-1;PreviewPlace=-1;}}return FReply::Handled();}
    if(K==EKeys::F){FocusPlace=bWarehouse?4:(FocusPlace==0?1:FocusPlace==1?3:0);FocusCell=StorageStart();}
    else if(K==EKeys::Left||K==EKeys::Right||K==EKeys::Up||K==EKeys::Down){int32 Columns=(FocusPlace==0||FocusPlace==4)?18:FocusPlace==1?3:4;FocusCell+=K==EKeys::Left?-1:K==EKeys::Right?1:K==EKeys::Up?-Columns:Columns;FocusCell=FMath::Clamp(FocusCell,StorageStart(),bWarehouse?StorageStart()+ColdSteelWarehouse::CellsPerPage-1:FocusPlace==0?71:FocusPlace==1?14:3);}
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
    if(KeyboardCarry.IsEmpty())bPreviewValid=true;
    else if(KeyboardHotbar>=0)bPreviewValid=FocusPlace==0||FocusPlace==3;
    else if(FocusPlace==3){const auto* I=Model->FindItem(KeyboardCarry);bPreviewValid=I&&I->Place==0&&Text(*I,TEXT("category"))==TEXT("consumable");}
    else bPreviewValid=Model->ProposeMove(KeyboardCarry,FocusPlace,FocusCell).bValid;
    return FReply::Handled();
}
void UColdSteelInventoryWidget::NativeOnDragDetected(const FGeometry& G,const FPointerEvent& E,UDragDropOperation*& Out)
{
    bPendingClick=false;if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);
    if(PressPlace==3)
    {
        const auto B=Model->QuickBinding(PressCell+ColdSteelQuickBar::ItemOffset);
        const FString Key=B.Skill.IsNone()?B.ItemDefinition:TEXT("@skill:")+B.Skill.ToString();
        if(auto* HUD=TooltipHUD())Out=HUD->StartQuickDrag(NAME_None,PressCell+ColdSteelQuickBar::ItemOffset,IconBrushes.Find(Key),E.GetScreenSpacePosition());
        return;
    }
    const auto* I=Model->FindItem(Selected);if(!I||IdAt(PressPlace,PressCell)!=Selected)return;
    auto* Drag=NewObject<UColdSteelItemDrag>(this);Drag->ItemId=Selected;Drag->HotbarIndex=PressPlace==3?PressCell:-1;Drag->SourceBoard=this;
    Drag->SourcePlace=I->Place;Drag->SourceCell=I->Cell;Drag->SourceSnapshot=*I;Drag->bHasSourceSnapshot=true;if(PressPlace==0||PressPlace==4)Drag->GrabOffset=FIntPoint(PressCell%18-I->Cell%18,PressCell/18-I->Cell/18);
    const auto L=Layout(G);const FVector2D Press=G.AbsoluteToLocal(PressPosition)*Scale;
    FVector2D Origin(12+I->Cell%18*L.Cell,L.BagY+(I->Cell-StorageStart())/18*L.Cell),Size(I->Width*L.Cell,I->Height*L.Cell);
    if(PressPlace==1){Origin=FVector2D(12+PressCell%3*(L.GearWidth+6),L.GearY+PressCell/3*L.GearPitch);Size=FVector2D(L.GearWidth,L.GearHeight);}
    else if(PressPlace==3){Origin=FVector2D(12+PressCell*54,L.HotY);Size=FVector2D(48,46);}
    const FVector2D Grab(FMath::Clamp((Press.X-Origin.X)/Size.X,0.0,1.0),FMath::Clamp((Press.Y-Origin.Y)/Size.Y,0.0,1.0));
    if(PressPlace==1)Drag->GrabOffset=FIntPoint(FMath::Min(I->Width-1,int32(Grab.X*I->Width)),FMath::Min(I->Height-1,int32(Grab.Y*I->Height)));
    const auto* Brush=ItemBrush(*I);
    FVector2D ImageSize=Size;
    if(Brush){ImageSize=Brush->ImageSize;ImageSize*=FMath::Min((Size.X-8)/FMath::Max(1.0,ImageSize.X),(Size.Y-8)/FMath::Max(1.0,ImageSize.Y));}
    const FVector2D ImageOrigin=Origin+(Size-ImageSize)*.5+FVector2D(0,(PressPlace==0||PressPlace==4)?2:0);
    const FVector2D ScreenOrigin=G.LocalToAbsolute(ImageOrigin/Scale);
    const FVector2D ScreenSize=G.LocalToAbsolute((ImageOrigin+ImageSize)/Scale)-ScreenOrigin;
    Drag->PointerVisual=CreateWidget<UColdSteelDragVisual>(GetOwningPlayer());
    Drag->PointerVisual->Configure(Brush,ScreenSize,PressPosition-ScreenOrigin,E.GetScreenSpacePosition());
    Drag->PointerVisual->AddToViewport(1000);ActivePointerDrag=Drag;
    // Suppress UMG's 150ms source-widget-origin interpolation; only the overlay is visible.
    auto* Empty=NewObject<USizeBox>(this);Empty->SetVisibility(ESlateVisibility::HitTestInvisible);
    Drag->DefaultDragVisual=Empty;Drag->Pivot=EDragPivot::TopLeft;Drag->Offset=FVector2D::ZeroVector;
    DraggedItem=Selected;Out=Drag;
    if(auto* HUD=TooltipHUD()){Drag->SourceHUD=HUD;HUD->BeginInventoryDrag(Drag);}
}
bool UColdSteelInventoryWidget::NativeOnDragOver(const FGeometry& G,const FDragDropEvent& E,UDragDropOperation* O)
{
    if(auto* Quick=Cast<UColdSteelQuickDrag>(O))
    {
        SwapDestinations.Empty();HoverPreview.Reset();
        if(!Hit(G,E.GetScreenSpacePosition(),PreviewPlace,PreviewCell))PreviewPlace=-1;
        bPreviewValid=Quick->IsCurrent()&&PreviewPlace==3;
        PreviewReason=bPreviewValid?TEXT("松开移动或交换快捷绑定"):TEXT("松开仅解绑，不丢弃背包物品");return true;
    }
    bPreviewValid=false;PreviewReason.Empty();SwapDestinations.Empty();auto* D=Cast<UColdSteelItemDrag>(O);
    if(!D||!Hit(G,E.GetScreenSpacePosition(),PreviewPlace,PreviewCell)){PreviewPlace=-1;return false;}
    HoverPreview=D->ItemId;const auto* Source=Model->FindItem(D->ItemId);
    if(!D->IsCurrent(Model)){PreviewReason=TEXT("物品已变化，请重新拖动");return true;}
    if(D->HotbarIndex>=0){const auto* Bound=Model->ResolveHotbar(D->HotbarIndex);bPreviewValid=Bound&&Bound->InstanceId==D->ItemId&&(PreviewPlace==0||PreviewPlace==3);PreviewReason=bPreviewValid?(PreviewPlace==0?TEXT("松开解绑，物品保留在背包"):TEXT("松开交换快捷栏")):TEXT("快捷物品只能放回背包或快捷栏");return true;}
    if(PreviewPlace==0||PreviewPlace==4){
        const int32 TargetPlace=PreviewPlace,Start=StorageStart();
        const int32 HoverCell=PreviewCell;const int32 X=HoverCell%18-D->GrabOffset.X,Y=(HoverCell-Start)/18-D->GrabOffset.Y;
        FColdSteelProposal Proposal;Proposal.Reason=TEXT("物品超出背包边界，请向内移动");
        if(X>=0&&Y>=0){PreviewCell=Start+Y*18+X;Proposal=Model->ProposeMove(D->ItemId,TargetPlace,PreviewCell);}
        // Keep normal grab-offset placement; retry at an occupied target's anchor only
        // if the original proposal fails and the same inventory rules accept the swap.
        if(!Proposal.bValid){const int32 N=Owner(Model->Items(),TargetPlace,HoverCell);if(N>=0&&Model->Items()[N].InstanceId!=D->ItemId){
            const int32 Target=Model->Items()[N].Cell;const auto Swap=Model->ProposeMove(D->ItemId,TargetPlace,Target);
            if(Swap.bValid){PreviewCell=Target;Proposal=Swap;}else Proposal.Reason=Swap.Reason;
        }}
        bPreviewValid=Proposal.bValid;PreviewReason=Proposal.bValid?TEXT("松开放置 / 交换物品"):Proposal.Reason;
        if(Proposal.bValid)for(const auto& I:Proposal.Items)if(I.Place==TargetPlace&&I.Cell>=Start&&I.Cell<Start+StorageRows()*18&&I.InstanceId!=D->ItemId){
            const auto* Before=Model->FindItem(I.InstanceId);
            if(Before&&(Before->Place!=I.Place||Before->Cell!=I.Cell))SwapDestinations.Add(FIntRect(I.Cell%18,(I.Cell-Start)/18,I.Cell%18+I.Width,(I.Cell-Start)/18+I.Height));
        }
        if(!SwapDestinations.IsEmpty())PreviewReason=FString::Printf(TEXT("松开交换 %d 件物品 · 高亮框为回填位置"),SwapDestinations.Num());
    }
    else if(PreviewPlace==3){bPreviewValid=Source->Place==0&&Text(*Source,TEXT("category"))==TEXT("consumable");PreviewReason=bPreviewValid?TEXT("松开绑定快捷物品"):TEXT("快捷栏仅接受背包中的消耗品");}
    else {const auto Proposal=Model->ProposeMove(D->ItemId,PreviewPlace,PreviewCell);bPreviewValid=Proposal.bValid;PreviewReason=Proposal.bValid?TEXT("松开放置 / 交换物品"):Proposal.Reason;}

    return true;
}
bool UColdSteelInventoryWidget::DropAt(const FString& Id,int32 Place,int32 Cell){return Place==3?Model->BindHotbar(Cell,Id):Model->MoveItem(Id,Place,Cell);}
bool UColdSteelInventoryWidget::NativeOnDrop(const FGeometry& G,const FDragDropEvent& E,UDragDropOperation* O)
{
    if(auto* Quick=Cast<UColdSteelQuickDrag>(O))
    {
        int32 Place=-1,Cell=-1;Hit(G,E.GetScreenSpacePosition(),Place,Cell);PreviewPlace=-1;
        if(auto* HUD=TooltipHUD())return HUD->DropQuickDrag(Quick,Place==3?Cell+ColdSteelQuickBar::ItemOffset:INDEX_NONE);
        return false;
    }
    auto* D=Cast<UColdSteelItemDrag>(O);if(!D||!NativeOnDragOver(G,E,O))return false;bool Result=false;
    if(bPreviewValid)Result=D->HotbarIndex>=0?(PreviewPlace==3?Model->SwapHotbar(D->HotbarIndex,PreviewCell):Model->BindHotbar(D->HotbarIndex,TEXT(""))):DropAt(D->ItemId,PreviewPlace,PreviewCell);
    InteractionMessage=Result?TEXT("物品操作已保存"):bPreviewValid?Model->ResultMessage():PreviewReason;
    PreviewPlace=-1;LoadIcons();return true;
}
void UColdSteelInventoryWidget::NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*){PreviewPlace=-1;}

UColdSteelHUDWidget* UColdSteelInventoryWidget::TooltipHUD()const{return StorageHUD.IsValid()?StorageHUD.Get():GetParent()?GetParent()->GetTypedOuter<UColdSteelHUDWidget>():nullptr;}
FReply UColdSteelInventoryWidget::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E)
{
    if(E.GetCursorDelta().IsNearlyZero())return Super::NativeOnMouseMove(G,E);
    bKeyboardTooltip=false;int32 Place,Cell;
    Hit(G,E.GetScreenSpacePosition(),HoverPlace,PointerCell);const auto L=Layout(G);const auto Local=G.AbsoluteToLocal(E.GetScreenSpacePosition())*Scale;
    bSortHovered=Local.X>=L.Width-60&&Local.X<L.Width-12&&Local.Y>=L.BagY-30&&Local.Y<L.BagY-6;
    if(auto* HUD=TooltipHUD()){
        if(bPendingClick||FSlateApplication::Get().IsDragDropping()||!KeyboardCarry.IsEmpty()){PendingTooltip.Empty();HUD->HideItemTooltip(true);return FReply::Handled();}
        const FString Id=Hit(G,E.GetScreenSpacePosition(),Place,Cell)?IdAt(Place,Cell):TEXT("");
        if(Id!=PendingTooltip){PendingTooltip=Id;TooltipAnchor=E.GetScreenSpacePosition();TooltipHoverTime=0;bHoverTooltipShown=false;HUD->HideItemTooltip();}
        if(Id.IsEmpty())HUD->HideItemTooltip();
    }
    return FReply::Handled();
}
void UColdSteelInventoryWidget::NativeOnMouseLeave(const FPointerEvent& E){Super::NativeOnMouseLeave(E);PendingTooltip.Empty();HoverPlace=-1;PointerCell=-1;bSortHovered=false;if(!bKeyboardTooltip)if(auto* HUD=TooltipHUD())HUD->HideItemTooltip();}
void UColdSteelInventoryWidget::NativeOnFocusLost(const FFocusEvent& E){Super::NativeOnFocusLost(E);bKeyboardTooltip=false;if(!IsHovered())if(auto* HUD=TooltipHUD())HUD->HideItemTooltip();}
