#include "ColdSteelInventoryWidget.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/SizeBox.h"
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
void UColdSteelItemDrag::Drop_Implementation(const FPointerEvent& E){if(SourceBoard.IsValid())SourceBoard->FinishDrag();Super::Drop_Implementation(E);}
void UColdSteelItemDrag::DragCancelled_Implementation(const FPointerEvent& E){if(SourceBoard.IsValid())SourceBoard->FinishDrag();Super::DragCancelled_Implementation(E);}
void UColdSteelInventoryWidget::FinishDrag(){DraggedItem.Empty();bPendingClick=false;PreviewPlace=-1;}
void UColdSteelInventoryWidget::CancelInteraction(){FinishDrag();Selected.Empty();KeyboardCarry.Empty();KeyboardHotbar=-1;bConfirmDrop=false;InteractionMessage.Empty();if(ItemMenu)ItemMenu->Close(false);ItemMenu=nullptr;}
void UColdSteelInventoryWidget::OpenItemMenu(FVector2D Anchor,bool SplitOnly){if(ItemMenu)ItemMenu->Close(false);if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);ItemMenu=CreateWidget<UColdSteelInventoryPopup>(GetOwningPlayer());ItemMenu->Open(this,Model,Selected,Anchor,SplitOnly);}

void UColdSteelInventoryWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);Scale=ColdSteelUI::PixelScale(this);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!WidgetTree->RootWidget){auto* Size=WidgetTree->ConstructWidget<USizeBox>();WidgetTree->RootWidget=Size;}
    SetVisibility(ESlateVisibility::Visible);LoadIcons();
}
void UColdSteelInventoryWidget::NativeConstruct(){Super::NativeConstruct();if(Model&&!ModelHandle.IsValid())ModelHandle=Model->OnChanged.AddUObject(this,&ThisClass::LoadIcons);LoadIcons();}
void UColdSteelInventoryWidget::NativeTick(const FGeometry& G,float Delta)
{
    Super::NativeTick(G,Delta);
    if(auto* Size=Cast<USizeBox>(WidgetTree->RootWidget)){
        const float Height=Layout(G).Height/Scale;
        if(!FMath::IsNearlyEqual(Size->GetMinDesiredHeight(),Height,.5f))Size->SetMinDesiredHeight(Height);
    }
}
void UColdSteelInventoryWidget::NativeDestruct(){if(Model)Model->OnChanged.Remove(ModelHandle);ModelHandle.Reset();CancelInteraction();Super::NativeDestruct();}
void UColdSteelInventoryWidget::LoadIcons()
{
    if(!Model)return;for(const auto& I:Model->Items()) {
        if(Icons.Contains(I.Definition))continue;const FString File=Text(I,TEXT("ue_icon"));if(File.IsEmpty())continue;
        auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);if(!Texture)continue;
        Icons.Add(I.Definition,Texture);FSlateBrush Brush;Brush.SetResourceObject(Texture);Brush.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush.DrawAs=ESlateBrushDrawType::Image;IconBrushes.Add(I.Definition,Brush);
    }
}
UColdSteelInventoryWidget::FBoardLayout UColdSteelInventoryWidget::Layout(const FGeometry& G)const
{
    FBoardLayout L;
    L.Width=FMath::Max(240.f,float(G.GetLocalSize().X*Scale));
    L.Cell=(L.Width-24)/18;
    L.GearWidth=(L.Width-36)/3;
    L.GearHeight=FMath::Clamp(L.Width*.085f,52.f,72.f);
    L.GearY=32;L.GearPitch=L.GearHeight+6;
    L.BagY=L.GearY+5*L.GearPitch-6+48;
    L.HotY=L.BagY+4*L.Cell+32;
    L.Height=L.HotY+46+36;
    return L;
}
bool UColdSteelInventoryWidget::Hit(const FGeometry& G,FVector2D Screen,int32& Place,int32& Cell)const
{
    const auto L=Layout(G);const FVector2D P=G.AbsoluteToLocal(Screen)*Scale;Place=-1;Cell=-1;
    if(P.X<12||P.X>L.Width-12)return false;
    if(P.Y>=L.GearY&&P.Y<L.GearY+5*L.GearPitch-6){
        const int32 Row=int32((P.Y-L.GearY)/L.GearPitch),Col=int32((P.X-12)/(L.GearWidth+6));
        if(Col>2||P.Y-L.GearY-Row*L.GearPitch>=L.GearHeight||P.X-12-Col*(L.GearWidth+6)>=L.GearWidth)return false;
        Place=1;Cell=Row*3+Col;return true;
    }
    if(P.Y>=L.BagY&&P.Y<L.BagY+4*L.Cell){Place=0;Cell=int32((P.Y-L.BagY)/L.Cell)*18+FMath::Clamp(int32((P.X-12)/L.Cell),0,17);return true;}
    if(P.Y>=L.HotY&&P.Y<L.HotY+46&&P.X<12+4*54){Place=3;Cell=int32((P.X-12)/54);return true;}
    return false;
}
FString UColdSteelInventoryWidget::IdAt(int32 Place,int32 Cell)const
{
    if(!Model)return TEXT("");if(Place==3){auto* I=Model->ResolveHotbar(Cell);return I?I->InstanceId:TEXT("");}
    int32 N=Owner(Model->Items(),Place,Cell);return N>=0?Model->Items()[N].InstanceId:TEXT("");
}
int32 UColdSteelInventoryWidget::NativePaint(const FPaintArgs& A,const FGeometry& G,const FSlateRect& C,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& S,bool Enabled)const
{
    Layer=Super::NativePaint(A,G,C,Out,Layer,S,Enabled);if(!Model)return Layer;
    const auto L=Layout(G);
    float ItemOpacity=1;
    auto Box=[&](float X,float Y,float W,float H,FLinearColor Color,FLinearColor Edge=FLinearColor::Transparent){Color.A*=ItemOpacity;Edge.A*=ItemOpacity;auto B=ColdSteelUI::RoundedBrush(Color,2/Scale,Edge,1/Scale);FSlateDrawElement::MakeBox(Out,Layer+1,G.ToPaintGeometry(FVector2D(W,H)/Scale,FSlateLayoutTransform(FVector2D(X,Y)/Scale)),&B,ESlateDrawEffect::None,Color);};
    auto Label=[&](FString T,float X,float Y,float Size,FLinearColor Color,bool Numeric=false){Color.A*=ItemOpacity;FSlateDrawElement::MakeText(Out,Layer+2,G.ToPaintGeometry(FVector2D(L.Width,30)/Scale,FSlateLayoutTransform(FVector2D(X,Y)/Scale)),T,Numeric?ColdSteelUI::NumberFont(Size*.75f/Scale):ColdSteelUI::TextFont(Size*.75f/Scale),ESlateDrawEffect::None,Color);};
    auto Item=[&](const FColdSteelItem& I,float X,float Y,float W,float H,bool Name){
        ItemOpacity=I.InstanceId==DraggedItem?.3f:1.f;
        Box(X+1,Y+1,W-2,H-2,ColdSteelUI::ButtonNormal,I.InstanceId==Selected?ColdSteelUI::Accent:ColdSteelUI::Border);
        if(const auto* Brush=IconBrushes.Find(I.Definition)){FVector2D Size=Brush->ImageSize;float Fit=FMath::Min((W-6)/FMath::Max(1.f,float(Size.X)),(H-6)/FMath::Max(1.f,float(Size.Y)));Size*=Fit;FSlateDrawElement::MakeBox(Out,Layer+2,G.ToPaintGeometry(Size/Scale,FSlateLayoutTransform(FVector2D(X+(W-Size.X)/2,Y+(H-Size.Y)/2)/Scale)),Brush,ESlateDrawEffect::None,FLinearColor(1,1,1,ItemOpacity));}
        else Label(Text(I,TEXT("name")).Left(FMath::Max(1,int32((W-6)/12))),X+4,Y+5,12,ColdSteelUI::TextPrimary);
        if(Name&&W>60)Label(Text(I,TEXT("name")).Left(int32((W-8)/12)),X+4,Y+2,12,ColdSteelUI::TextPrimary);
        if(I.Count>1)Label(FString::Printf(TEXT("%lld"),I.Count),X+FMath::Max(2.f,W-9*FString::Printf(TEXT("%lld"),I.Count).Len()),Y+H-13,11,ColdSteelUI::TextPrimary,true);
        if(I.Cooldown>0)Label(FString::Printf(TEXT("%.1f"),I.Cooldown),X+3,Y+2,11,ColdSteelUI::Warning,true);
        ItemOpacity=1;
    };
    Label(TEXT("装备栏"),12,4,16,ColdSteelUI::TextPrimary);

    for(int32 N=0;N<15;++N){float X=12+(N%3)*(L.GearWidth+6),Y=L.GearY+(N/3)*L.GearPitch;Box(X,Y,L.GearWidth,L.GearHeight,ColdSteelUI::Content,ColdSteelUI::Border);int32 Index=Owner(Model->Items(),1,N);if(Index>=0)Item(Model->Items()[Index],X,Y,L.GearWidth,L.GearHeight,false);else Label(Locked(Model->Items(),N)?TEXT("双手占用"):SlotNames()[N],X+8,Y+(L.GearHeight-16)/2,16,ColdSteelUI::TextSecondary);}
    int32 Cells=0,Items=0;for(const auto& I:Model->Items())if(I.Place==0){Cells+=I.Width*I.Height;++Items;}
    Label(TEXT("背包"),12,L.BagY-28,16,ColdSteelUI::TextPrimary);Label(FString::Printf(TEXT("%d/72 格 · %d 件"),Cells,Items),FMath::Max(100.f,L.Width-212),L.BagY-26,12,ColdSteelUI::TextSecondary,true);
    Box(L.Width-60,L.BagY-30,48,24,ColdSteelUI::ButtonNormal,ColdSteelUI::Border);Label(TEXT("整理"),L.Width-50,L.BagY-25,12,ColdSteelUI::TextPrimary);
    for(int32 N=0;N<72;++N)if(Owner(Model->Items(),0,N)<0)Box(12+N%18*L.Cell,L.BagY+N/18*L.Cell,L.Cell,L.Cell,ColdSteelUI::Content,ColdSteelUI::Border);
    for(const auto& I:Model->Items())if(I.Place==0)Item(I,12+I.Cell%18*L.Cell,L.BagY+I.Cell/18*L.Cell,I.Width*L.Cell,I.Height*L.Cell,true);
    if(PreviewPlace>=0&&PreviewCell>=0){const auto* I=Model->FindItem(HoverPreview);float X=12,Y=0,W=48,H=L.GearHeight;
        if(PreviewPlace==0){X+=PreviewCell%18*L.Cell;Y=L.BagY+PreviewCell/18*L.Cell;W=(I?I->Width:1)*L.Cell;H=(I?I->Height:1)*L.Cell;W=FMath::Min(W,L.Width-X-12);H=FMath::Min(H,L.BagY+4*L.Cell-Y);}
        else if(PreviewPlace==1){X+=PreviewCell%3*(L.GearWidth+6);Y=L.GearY+PreviewCell/3*L.GearPitch;W=L.GearWidth;}
        else{X+=PreviewCell*54;Y=L.HotY;H=46;}
        auto Color=bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger;Color.A=.35f;Box(X,Y,W,H,Color,bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger);
    }
    if(!PreviewReason.IsEmpty()&&PreviewPlace>=0)Label(PreviewReason,12,L.HotY+54,11,bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger);
    else if(!InteractionMessage.IsEmpty())Label(InteractionMessage,12,L.HotY+54,11,ColdSteelUI::Accent);
    Label(TEXT("快捷物品"),12,L.HotY-20,12,ColdSteelUI::TextSecondary);
    for(int32 N=0;N<4;++N){float X=12+N*54;Box(X,L.HotY,48,46,ColdSteelUI::Content,ColdSteelUI::Border);if(const auto* I=Model->ResolveHotbar(N))Item(*I,X,L.HotY,48,46,false);Label(FString::FromInt(N+1),X+3,L.HotY+30,12,ColdSteelUI::TextPrimary,true);}
    return Layer+3;
}
FReply UColdSteelInventoryWidget::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    bPendingClick=false;SetKeyboardFocus();LoadIcons();const auto L=Layout(G);FVector2D P=G.AbsoluteToLocal(E.GetScreenSpacePosition())*Scale;
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
        if(E.IsShiftDown()&&Place==0)OpenItemMenu(E.GetScreenSpacePosition(),true);
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
    if(Action==7)if(const auto* I=Model->FindItem(Selected))if(I->Definition==TEXT("ue_m4a1"))
    {if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->OpenGunsmith(Selected);return;}
    switch(Action){case 0:Model->DefaultAction(Selected);break;case 1:OpenItemMenu(GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale),true);break;case 2:if(bConfirmDrop){Model->Drop(Selected);bConfirmDrop=false;}else bConfirmDrop=true;break;case 3:Model->Sort();break;case 4:if(auto* HUD=TooltipHUD()){HUD->ShowItemTooltip(Selected,GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale),true,this);HUD->FocusItemTooltip();}break;case 5:OpenItemMenu(GetCachedGeometry().LocalToAbsolute(FVector2D(12,L.BagY)/Scale));break;case 6:Model->SaveNow();break;case 7:Selected.Empty();bConfirmDrop=false;break;}
    InteractionMessage=bConfirmDrop?TEXT("再次按 Delete 确认丢下，Esc 取消"):Model->ResultMessage();LoadIcons();
}
FReply UColdSteelInventoryWidget::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape&&bConfirmDrop){bConfirmDrop=false;InteractionMessage.Empty();return FReply::Handled();}
    if(E.GetKey()==EKeys::Escape&&!KeyboardCarry.IsEmpty()){KeyboardCarry.Empty();KeyboardHotbar=-1;PreviewPlace=-1;return FReply::Handled();}
    if(E.GetKey()==EKeys::J){if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->OpenGunsmith(Selected);return FReply::Handled();}
    if(E.GetKey()==EKeys::F1){if(auto* HUD=TooltipHUD()){HUD->ShowItemTooltip(Selected,G.LocalToAbsolute(FVector2D(12,28)/Scale),true,this);HUD->FocusItemTooltip();}return FReply::Handled();}
    const FKey K=E.GetKey();if(K==EKeys::Enter){PerformAction(0);return FReply::Handled();}if(K==EKeys::X){PerformAction(1);return FReply::Handled();}if(K==EKeys::Delete){PerformAction(2);return FReply::Handled();}
    if(K==EKeys::G){Model->CycleWeapon();return FReply::Handled();}
    if(K==EKeys::SpaceBar){if(KeyboardCarry.IsEmpty()){KeyboardCarry=IdAt(FocusPlace,FocusCell);KeyboardHotbar=FocusPlace==3?FocusCell:-1;}else {const bool OK=KeyboardHotbar>=0?(FocusPlace==3?Model->SwapHotbar(KeyboardHotbar,FocusCell):FocusPlace==0&&Model->BindHotbar(KeyboardHotbar,TEXT(""))):DropAt(KeyboardCarry,FocusPlace,FocusCell);InteractionMessage=Model->ResultMessage();if(OK){KeyboardCarry.Empty();KeyboardHotbar=-1;PreviewPlace=-1;}}return FReply::Handled();}
    if(K==EKeys::F){FocusPlace=(FocusPlace==0?1:FocusPlace==1?3:0);FocusCell=0;}
    else if(K==EKeys::Left||K==EKeys::Right||K==EKeys::Up||K==EKeys::Down){int32 Columns=FocusPlace==0?18:FocusPlace==1?3:4;FocusCell+=K==EKeys::Left?-1:K==EKeys::Right?1:K==EKeys::Up?-Columns:Columns;FocusCell=FMath::Clamp(FocusCell,0,FocusPlace==0?71:FocusPlace==1?14:3);}
    else return Super::NativeOnKeyDown(G,E);
    Selected=IdAt(FocusPlace,FocusCell);bConfirmDrop=false;bKeyboardTooltip=true;
    if(auto* HUD=TooltipHUD()){if(KeyboardCarry.IsEmpty()&&!Selected.IsEmpty())HUD->ShowItemTooltip(Selected,G.LocalToAbsolute(FVector2D(12,28)/Scale),false,this);else HUD->HideItemTooltip(true);}
    HoverPreview=KeyboardCarry;PreviewPlace=FocusPlace;PreviewCell=FocusCell;
    if(KeyboardCarry.IsEmpty())bPreviewValid=true;
    else if(KeyboardHotbar>=0)bPreviewValid=FocusPlace==0||FocusPlace==3;
    else if(FocusPlace==3){const auto* I=Model->FindItem(KeyboardCarry);bPreviewValid=I&&I->Place==0&&Text(*I,TEXT("category"))==TEXT("consumable");}
    else bPreviewValid=Model->ProposeMove(KeyboardCarry,FocusPlace,FocusCell).bValid;
    return FReply::Handled();
}
void UColdSteelInventoryWidget::NativeOnDragDetected(const FGeometry& G,const FPointerEvent& E,UDragDropOperation*& Out)
{
    bPendingClick=false;if(auto* HUD=TooltipHUD())HUD->HideItemTooltip(true);
    const auto* I=Model->FindItem(Selected);if(!I||IdAt(PressPlace,PressCell)!=Selected)return;
    auto* Drag=NewObject<UColdSteelItemDrag>(this);Drag->ItemId=Selected;Drag->HotbarIndex=PressPlace==3?PressCell:-1;Drag->SourceBoard=this;
    Drag->SourcePlace=I->Place;Drag->SourceCell=I->Cell;if(PressPlace==0)Drag->GrabOffset=FIntPoint(PressCell%18-I->Cell%18,PressCell/18-I->Cell/18);
    auto* Visual=NewObject<UImage>(this);if(const auto* Brush=IconBrushes.Find(I->Definition))Visual->SetBrush(*Brush);
    auto* Frame=NewObject<USizeBox>(this);Frame->SetWidthOverride(I->Width*Layout(G).Cell/Scale);Frame->SetHeightOverride(I->Height*Layout(G).Cell/Scale);
    auto* Fit=NewObject<UScaleBox>(this);Fit->SetStretch(EStretch::ScaleToFit);Fit->SetContent(Visual);Frame->SetContent(Fit);Frame->SetRenderOpacity(.65f);Frame->SetVisibility(ESlateVisibility::HitTestInvisible);
    Drag->DefaultDragVisual=Frame;Drag->Pivot=EDragPivot::TopLeft;
    Drag->Offset=FVector2D(-(Drag->GrabOffset.X+.5f)/I->Width,-(Drag->GrabOffset.Y+.5f)/I->Height);
    DraggedItem=Selected;Out=Drag;
}
bool UColdSteelInventoryWidget::NativeOnDragOver(const FGeometry& G,const FDragDropEvent& E,UDragDropOperation* O)
{
    bPreviewValid=false;PreviewReason.Empty();auto* D=Cast<UColdSteelItemDrag>(O);
    if(!D||!Hit(G,E.GetScreenSpacePosition(),PreviewPlace,PreviewCell)){PreviewPlace=-1;return false;}
    HoverPreview=D->ItemId;const auto* Source=Model->FindItem(D->ItemId);
    if(!Source||Source->Place!=D->SourcePlace||Source->Cell!=D->SourceCell){PreviewReason=TEXT("物品已移动，请重新拖动");return true;}
    if(D->HotbarIndex>=0){const auto* Bound=Model->ResolveHotbar(D->HotbarIndex);bPreviewValid=Bound&&Bound->InstanceId==D->ItemId&&(PreviewPlace==0||PreviewPlace==3);PreviewReason=bPreviewValid?(PreviewPlace==0?TEXT("松开解绑，物品保留在背包"):TEXT("松开交换快捷栏")):TEXT("快捷物品只能放回背包或快捷栏");return true;}
    if(PreviewPlace==0){
        const int32 HoverCell=PreviewCell;const int32 X=HoverCell%18-D->GrabOffset.X,Y=HoverCell/18-D->GrabOffset.Y;
        FColdSteelProposal Proposal;Proposal.Reason=TEXT("物品超出背包边界，请向内移动");
        if(X>=0&&Y>=0){PreviewCell=Y*18+X;Proposal=Model->ProposeMove(D->ItemId,0,PreviewCell);}
        // Keep normal grab-offset placement; retry at an occupied target's anchor only
        // if the original proposal fails and the same inventory rules accept the swap.
        if(!Proposal.bValid){const int32 N=Owner(Model->Items(),0,HoverCell);if(N>=0&&Model->Items()[N].InstanceId!=D->ItemId){
            const int32 Target=Model->Items()[N].Cell;const auto Swap=Model->ProposeMove(D->ItemId,0,Target);
            if(Swap.bValid){PreviewCell=Target;Proposal=Swap;}else Proposal.Reason=Swap.Reason;
        }}
        if(Proposal.bValid){const auto L=Layout(G);const auto Local=G.AbsoluteToLocal(E.GetScreenSpacePosition())*Scale;D->Offset=FVector2D((12+PreviewCell%18*L.Cell-Local.X)/(Source->Width*L.Cell),(L.BagY+PreviewCell/18*L.Cell-Local.Y)/(Source->Height*L.Cell));}
        bPreviewValid=Proposal.bValid;PreviewReason=Proposal.bValid?TEXT("松开放置 / 交换物品"):Proposal.Reason;
    }
    else if(PreviewPlace==3){bPreviewValid=Source->Place==0&&Text(*Source,TEXT("category"))==TEXT("consumable");PreviewReason=bPreviewValid?TEXT("松开绑定快捷物品"):TEXT("快捷栏仅接受背包中的消耗品");}
    else {const auto Proposal=Model->ProposeMove(D->ItemId,PreviewPlace,PreviewCell);bPreviewValid=Proposal.bValid;PreviewReason=Proposal.bValid?TEXT("松开放置 / 交换物品"):Proposal.Reason;}

    return true;
}
bool UColdSteelInventoryWidget::DropAt(const FString& Id,int32 Place,int32 Cell){return Place==3?Model->BindHotbar(Cell,Id):Model->MoveItem(Id,Place,Cell);}
bool UColdSteelInventoryWidget::NativeOnDrop(const FGeometry& G,const FDragDropEvent& E,UDragDropOperation* O)
{
    auto* D=Cast<UColdSteelItemDrag>(O);if(!D||!NativeOnDragOver(G,E,O))return false;bool Result=false;
    if(bPreviewValid)Result=D->HotbarIndex>=0?(PreviewPlace==3?Model->SwapHotbar(D->HotbarIndex,PreviewCell):Model->BindHotbar(D->HotbarIndex,TEXT(""))):DropAt(D->ItemId,PreviewPlace,PreviewCell);
    InteractionMessage=Result?TEXT("物品操作已保存"):bPreviewValid?Model->ResultMessage():PreviewReason;
    PreviewPlace=-1;LoadIcons();return true;
}
void UColdSteelInventoryWidget::NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*){PreviewPlace=-1;}

UColdSteelHUDWidget* UColdSteelInventoryWidget::TooltipHUD()const{return GetParent()?GetParent()->GetTypedOuter<UColdSteelHUDWidget>():nullptr;}
FReply UColdSteelInventoryWidget::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E)
{
    if(E.GetCursorDelta().IsNearlyZero())return Super::NativeOnMouseMove(G,E);
    bKeyboardTooltip=false;int32 Place,Cell;
    if(auto* HUD=TooltipHUD()){
        if(bPendingClick||FSlateApplication::Get().IsDragDropping()||!KeyboardCarry.IsEmpty()){HUD->HideItemTooltip(true);return FReply::Handled();}
        const FString Id=Hit(G,E.GetScreenSpacePosition(),Place,Cell)?IdAt(Place,Cell):TEXT("");
        if(!Id.IsEmpty())HUD->ShowItemTooltip(Id,E.GetScreenSpacePosition(),false,this);else HUD->HideItemTooltip();
    }
    return FReply::Handled();
}
void UColdSteelInventoryWidget::NativeOnMouseLeave(const FPointerEvent& E){Super::NativeOnMouseLeave(E);if(!bKeyboardTooltip)if(auto* HUD=TooltipHUD())HUD->HideItemTooltip();}
void UColdSteelInventoryWidget::NativeOnFocusLost(const FFocusEvent& E){Super::NativeOnFocusLost(E);bKeyboardTooltip=false;if(!IsHovered())if(auto* HUD=TooltipHUD())HUD->HideItemTooltip();}
