#include "ColdSteelInventoryPopup.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../FPSGAMEPlayerController.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/EditableTextBox.h"
#include "Components/Button.h"
#include "String/LexFromString.h"
using namespace ColdSteelInventory;
UTextBlock* UColdSteelInventoryPopup::Label(const FString& Text)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Text));T->SetFont(ColdSteelUI::TextFont(11/Scale));T->SetColorAndOpacity(ColdSteelUI::TextPrimary);T->SetAutoWrapText(true);T->SetVisibility(ESlateVisibility::HitTestInvisible);return T;
}
UButton* UColdSteelInventoryPopup::Button(const FString& Text)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();FButtonStyle S;S.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal,4/Scale,ColdSteelUI::Border));S.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,4/Scale,ColdSteelUI::Accent));S.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,4/Scale));B->SetStyle(S);B->SetContent(Label(Text));Stack->AddChildToVerticalBox(B)->SetPadding(FMargin(0,3/Scale));return B;
}
void UColdSteelInventoryPopup::Open(UColdSteelInventoryWidget* Board,UColdSteelStatusModel* Source,const FString& Id,FVector2D Anchor,bool SplitOnly)
{
    OwnerBoard=Board;Model=Source;ItemId=Id;Scale=ColdSteelUI::PixelScale(this);const auto* I=Model?Model->FindItem(Id):nullptr;if(!I)return;
    SetIsFocusable(true);auto* Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    auto* Surface=WidgetTree->ConstructWidget<UBorder>();Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,8/Scale,ColdSteelUI::Border));Surface->SetPadding(FMargin(12/Scale));
    auto* PopupSlot=Root->AddChildToCanvas(Surface);
    const auto View=UWidgetLayoutLibrary::GetViewportWidgetGeometry(this);const auto Size=UWidgetLayoutLibrary::GetViewportSize(this)/Scale;auto At=View.AbsoluteToLocal(Anchor);
    const float Height=SplitOnly?220:280;
    PopupSlot->SetPosition(FVector2D(FMath::Clamp(At.X,8./Scale,FMath::Max(8./Scale,Size.X-328/Scale)),FMath::Clamp(At.Y,8./Scale,FMath::Max(8./Scale,Size.Y-(Height+8)/Scale))));PopupSlot->SetSize(FVector2D(320,Height)/Scale);
    Stack=WidgetTree->ConstructWidget<UVerticalBox>();Surface->SetContent(Stack);
    Stack->AddChildToVerticalBox(Label(Text(*I,TEXT("name"))));
    if(!SplitOnly){Button(I->Place==1?TEXT("卸下装备"):Model->bWarehouseOpen?TEXT("存入仓库"):TEXT("使用 / 穿戴"))->OnClicked.AddDynamic(this,&ThisClass::Use);
        if(I->Place==0&&I->Count>1&&Text(*I,TEXT("category"))!=TEXT("gold"))Button(TEXT("拆分数量…"))->OnClicked.AddDynamic(this,&ThisClass::Split);
        Button(TEXT("查看详情"))->OnClicked.AddDynamic(this,&ThisClass::Details);
        auto* D=Button(TEXT("丢下物品…"));DropCaption=Cast<UTextBlock>(D->GetContent());D->OnClicked.AddDynamic(this,&ThisClass::Drop);
        if(I->Definition==TEXT("ue_m4a1"))Button(TEXT("改造武器"))->OnClicked.AddDynamic(this,&ThisClass::OpenGunsmith);
        Button(TEXT("整理背包"))->OnClicked.AddDynamic(this,&ThisClass::SortBag);
        Button(TEXT("保存背包"))->OnClicked.AddDynamic(this,&ThisClass::SaveBag);
    }
    Message=Label(TEXT(""));Stack->AddChildToVerticalBox(Message);
    if(SplitOnly)Split();else Button(TEXT("取消 · Esc"))->OnClicked.AddDynamic(this,&ThisClass::Cancel);
    AddToViewport(300);SetVisibility(ESlateVisibility::Visible);if(Quantity)Quantity->SetKeyboardFocus();else SetKeyboardFocus();
}
void UColdSteelInventoryPopup::Split()
{
    const auto* I=Model->FindItem(ItemId);if(!I||I->Place!=0||I->Count<2||Text(*I,TEXT("category"))==TEXT("gold")){Message->SetText(FText::FromString(TEXT("此物品无法拆分")));return;}
    Stack->ClearChildren();Stack->AddChildToVerticalBox(Label(TEXT("拆分 · ")+Text(*I,TEXT("name"))));
    Stack->AddChildToVerticalBox(Label(FString::Printf(TEXT("输入数量 1～%lld"),I->Count-1)));
    Quantity=WidgetTree->ConstructWidget<UEditableTextBox>();Quantity->SetText(FText::FromString(FString::Printf(TEXT("%lld"),FMath::Max<int64>(1,I->Count/2))));auto EditStyle=Quantity->GetWidgetStyle();EditStyle.TextStyle.SetFont(ColdSteelUI::NumberFont(13/Scale));EditStyle.SetForegroundColor(ColdSteelUI::ItemTooltipText);EditStyle.SetFocusedForegroundColor(ColdSteelUI::ItemTooltipText);Quantity->SetWidgetStyle(EditStyle);Quantity->SetSelectAllTextWhenFocused(true);Quantity->OnTextCommitted.AddDynamic(this,&ThisClass::QuantityCommitted);Stack->AddChildToVerticalBox(Quantity)->SetPadding(FMargin(0,12/Scale));
    Message=Label(TEXT("确认后放入背包空位"));Stack->AddChildToVerticalBox(Message);Button(TEXT("确认拆分 · Enter"))->OnClicked.AddDynamic(this,&ThisClass::ConfirmSplit);Button(TEXT("取消 · Esc"))->OnClicked.AddDynamic(this,&ThisClass::Cancel);Quantity->SetKeyboardFocus();
}
void UColdSteelInventoryPopup::ConfirmSplit()
{
    const auto* I=Model->FindItem(ItemId);int64 Count=0;const FString Value=Quantity?Quantity->GetText().ToString().TrimStartAndEnd():TEXT("");
    if(!I||!Value.IsNumeric()||Value.Contains(TEXT("."))||!LexTryParseString(Count,*Value)||Count<1||Count>=I->Count){Message->SetText(FText::FromString(TEXT("请输入小于当前堆叠数量的正整数")));return;}
    if(Model->Split(ItemId,Count))Close();else Message->SetText(FText::FromString(Model->ResultMessage()));
}
void UColdSteelInventoryPopup::Use(){if(Model->DefaultAction(ItemId))Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::Drop(){if(!bConfirmDrop){bConfirmDrop=true;DropCaption->SetText(FText::FromString(TEXT("确认丢下整组物品")));return;}if(Model->Drop(ItemId))Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::OpenGunsmith(){if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer())){Close(false);PC->OpenGunsmith(ItemId);}}
void UColdSteelInventoryPopup::Details(){Close(false);if(OwnerBoard.IsValid()){OwnerBoard->SelectItem(ItemId);OwnerBoard->PerformAction(4);}}
void UColdSteelInventoryPopup::SortBag(){if(Model->Sort())Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::SaveBag(){if(Model->SaveNow())Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::QuantityCommitted(const FText&,ETextCommit::Type Type){if(Type==ETextCommit::OnEnter)ConfirmSplit();}
void UColdSteelInventoryPopup::Cancel(){Close();}
void UColdSteelInventoryPopup::Close(bool RestoreFocus){RemoveFromParent();if(RestoreFocus&&OwnerBoard.IsValid()&&OwnerBoard->IsVisible())OwnerBoard->SetKeyboardFocus();}
FReply UColdSteelInventoryPopup::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E){if(E.GetKey()==EKeys::Escape){Close();return FReply::Handled();}return Super::NativeOnKeyDown(G,E);}
FReply UColdSteelInventoryPopup::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent& E)
{
    // This popup is a separate viewport root, so the HUD never receives its background click.
    if(E.GetEffectingButton()==EKeys::LeftMouseButton&&OwnerBoard.IsValid())
        if(auto* HUD=OwnerBoard->TooltipHUD();HUD&&HUD->HandleInventoryOutsideClick(E.GetScreenSpacePosition()))return FReply::Handled();
    Close();return FReply::Handled();
}
FReply UColdSteelInventoryPopup::NativeOnPreviewKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape){Close();return FReply::Handled();}
    if((E.GetKey()==EKeys::Tab||E.GetKey()==EKeys::CapsLock)&&OwnerBoard.IsValid())if(auto* HUD=OwnerBoard->TooltipHUD()){HUD->HandlePanelShortcut(E.GetKey(),E.IsRepeat());return FReply::Handled();}
    return Super::NativeOnPreviewKeyDown(G,E);
}
