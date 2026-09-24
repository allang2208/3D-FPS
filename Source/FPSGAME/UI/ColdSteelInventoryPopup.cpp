#include "ColdSteelInventoryPopup.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../FPSGAMEPlayerController.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/BackgroundBlur.h"
#include "Components/ScrollBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/EditableTextBox.h"
#include "Components/Button.h"
#include "String/LexFromString.h"
using namespace ColdSteelInventory;
UTextBlock* UColdSteelInventoryPopup::Label(const FString& Text)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Text));T->SetFont(GunsmithUI::TextFont(14/Scale));T->SetColorAndOpacity(GunsmithUI::Text);T->SetAutoWrapText(true);T->SetVisibility(ESlateVisibility::HitTestInvisible);return T;
}
UButton* UColdSteelInventoryPopup::Button(const FString& Text)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();FButtonStyle S;S.SetNormal(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(43,180),6/Scale,GunsmithUI::Edge));S.SetHovered(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(65,220),6/Scale,GunsmithUI::Silver));S.SetPressed(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(24,235),6/Scale));B->SetStyle(S);B->SetContent(Label(Text));Stack->AddChildToVerticalBox(B)->SetPadding(FMargin(0,3/Scale));return B;
}
void UColdSteelInventoryPopup::Open(UColdSteelInventoryWidget* Board,UColdSteelStatusModel* Source,const FString& Id,FVector2D Anchor,bool SplitOnly)
{
    OwnerBoard=Board;Model=Source;ItemId=Id;Scale=ColdSteelUI::PixelScale(this);const auto* I=Model?Model->FindItem(Id):nullptr;if(!I)return;
    SetIsFocusable(true);auto* Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    auto* Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();Blur->SetBlurStrength(5);Blur->SetOverrideAutoRadiusCalculation(true);Blur->SetBlurRadius(13);Blur->SetCornerRadius(FVector4(10,10,10,10));Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(29),10));
    auto* Surface=WidgetTree->ConstructWidget<UBorder>();Surface->SetBrush(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(26,248),10/Scale,GunsmithUI::Edge));Surface->SetPadding(FMargin(12/Scale));Blur->SetContent(Surface);
    auto* PopupSlot=Root->AddChildToCanvas(Blur);
    const auto View=UWidgetLayoutLibrary::GetViewportWidgetGeometry(this);const auto Size=UWidgetLayoutLibrary::GetViewportSize(this)/Scale;auto At=View.AbsoluteToLocal(Anchor);
    const float Height=FMath::Min(SplitOnly?240.f:336.f,float(Size.Y*Scale)-24.f);
    PopupSlot->SetPosition(FVector2D(FMath::Clamp(At.X,8./Scale,FMath::Max(8./Scale,Size.X-328/Scale)),FMath::Clamp(At.Y,8./Scale,FMath::Max(8./Scale,Size.Y-(Height+8)/Scale))));PopupSlot->SetSize(FVector2D(320,Height)/Scale);
    auto* Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetScrollbarThickness(FVector2D(5/Scale));Surface->SetContent(Scroll);
    Stack=WidgetTree->ConstructWidget<UVerticalBox>();Scroll->AddChild(Stack);
    Stack->AddChildToVerticalBox(Label(Text(*I,TEXT("name"))));
    if(!SplitOnly){const FString DepositLabel=FString::Printf(TEXT("存入%s"),Model->ActiveStorageCaption.IsEmpty()?TEXT("仓库"):*Model->ActiveStorageCaption);Button(I->Place==4?FString(TEXT("取出到背包")):Model->bWarehouseOpen?DepositLabel:I->Place==1?FString(TEXT("卸下装备")):FString(TEXT("使用 / 穿戴")))->OnClicked.AddDynamic(this,&ThisClass::Use);
        if((I->Place==0||I->Place==4)&&I->Count>1&&Text(*I,TEXT("category"))!=TEXT("gold"))Button(TEXT("拆分数量…"))->OnClicked.AddDynamic(this,&ThisClass::Split);
        Button(TEXT("查看详情"))->OnClicked.AddDynamic(this,&ThisClass::Details);
        auto* D=Button(TEXT("丢下物品…"));DropCaption=Cast<UTextBlock>(D->GetContent());D->OnClicked.AddDynamic(this,&ThisClass::Drop);
        if(GetGameInstance()->GetSubsystem<UGunsmithSystem>()->ModifiableWeapon(I->Definition))Button(I->Place==4?TEXT("取出并改造"):TEXT("改造武器"))->OnClicked.AddDynamic(this,&ThisClass::OpenGunsmith);
        if(GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>()->Supports(*I))Button(I->Place==4?TEXT("取出并强化 / 附魔"):TEXT("强化 / 附魔"))->OnClicked.AddDynamic(this,&ThisClass::OpenEnhancement);
        Button(Board->bWarehouse?TEXT("整理仓库"):TEXT("整理背包"))->OnClicked.AddDynamic(this,&ThisClass::SortBag);
        Button(TEXT("保存物品"))->OnClicked.AddDynamic(this,&ThisClass::SaveBag);
    }
    Message=Label(TEXT(""));Stack->AddChildToVerticalBox(Message);
    if(SplitOnly)Split();else Button(TEXT("取消 · Esc"))->OnClicked.AddDynamic(this,&ThisClass::Cancel);
    AddToViewport(300);SetVisibility(ESlateVisibility::Visible);if(Quantity)Quantity->SetKeyboardFocus();else SetKeyboardFocus();
}
void UColdSteelInventoryPopup::Split()
{
    const auto* I=Model->FindItem(ItemId);if(!I||(I->Place!=0&&I->Place!=4)||I->Count<2||Text(*I,TEXT("category"))==TEXT("gold")){Message->SetText(FText::FromString(TEXT("此物品无法拆分")));return;}
    Stack->ClearChildren();Stack->AddChildToVerticalBox(Label(TEXT("拆分 · ")+Text(*I,TEXT("name"))));
    Stack->AddChildToVerticalBox(Label(FString::Printf(TEXT("输入数量 1～%lld"),I->Count-1)));
    Quantity=WidgetTree->ConstructWidget<UEditableTextBox>();Quantity->SetText(FText::FromString(FString::Printf(TEXT("%lld"),FMath::Max<int64>(1,I->Count/2))));auto EditStyle=Quantity->GetWidgetStyle();EditStyle.TextStyle.SetFont(GunsmithUI::NumberFont(16/Scale));EditStyle.SetForegroundColor(GunsmithUI::Text);EditStyle.SetFocusedForegroundColor(GunsmithUI::Text);
    EditStyle.SetBackgroundImageNormal(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(16),5/Scale,GunsmithUI::Edge));EditStyle.SetBackgroundImageHovered(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(24),5/Scale,GunsmithUI::Silver));EditStyle.SetBackgroundImageFocused(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(24),5/Scale,GunsmithUI::Silver));
    Quantity->SetWidgetStyle(EditStyle);Quantity->SetSelectAllTextWhenFocused(true);Quantity->OnTextCommitted.AddDynamic(this,&ThisClass::QuantityCommitted);Stack->AddChildToVerticalBox(Quantity)->SetPadding(FMargin(0,12/Scale));
    Message=Label(I->Place==4?TEXT("确认后放入仓库空位"):TEXT("确认后放入背包空位"));Stack->AddChildToVerticalBox(Message);Button(TEXT("确认拆分 · Enter"))->OnClicked.AddDynamic(this,&ThisClass::ConfirmSplit);Button(TEXT("取消 · Esc"))->OnClicked.AddDynamic(this,&ThisClass::Cancel);Quantity->SetKeyboardFocus();
}
void UColdSteelInventoryPopup::ConfirmSplit()
{
    const auto* I=Model->FindItem(ItemId);int64 Count=0;const FString Value=Quantity?Quantity->GetText().ToString().TrimStartAndEnd():TEXT("");
    if(!I||!Value.IsNumeric()||Value.Contains(TEXT("."))||!LexTryParseString(Count,*Value)||Count<1||Count>=I->Count){Message->SetText(FText::FromString(TEXT("请输入小于当前堆叠数量的正整数")));return;}
    if(Model->Split(ItemId,Count))Close();else Message->SetText(FText::FromString(Model->ResultMessage()));
}
void UColdSteelInventoryPopup::Use(){if(Model->DefaultAction(ItemId))Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::Drop(){if(!bConfirmDrop){bConfirmDrop=true;DropCaption->SetText(FText::FromString(TEXT("确认丢下整组物品")));return;}if(Model->Drop(ItemId))Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::OpenGunsmith(){if(const auto* I=Model->FindItem(ItemId);I&&I->Place==4&&!Model->TransferWarehouse(ItemId,0)){Message->SetText(FText::FromString(Model->ResultMessage()));return;}if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer())){Close(false);PC->OpenGunsmith(ItemId);}}
void UColdSteelInventoryPopup::OpenEnhancement(){if(const auto* I=Model->FindItem(ItemId);I&&I->Place==4&&!Model->TransferWarehouse(ItemId,0)){Message->SetText(FText::FromString(Model->ResultMessage()));return;}if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer())){const FString Id=ItemId;Close(false);PC->OpenEnhancement(Id);}}
void UColdSteelInventoryPopup::Details(){Close(false);if(OwnerBoard.IsValid()){OwnerBoard->SelectItem(ItemId);OwnerBoard->PerformAction(4);}}
void UColdSteelInventoryPopup::SortBag(){if(OwnerBoard.IsValid()&&OwnerBoard->bWarehouse?Model->SortWarehouse(TEXT("category")):Model->Sort())Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::SaveBag(){if(Model->SaveNow())Close();else Message->SetText(FText::FromString(Model->ResultMessage()));}
void UColdSteelInventoryPopup::QuantityCommitted(const FText&,ETextCommit::Type Type){if(Type==ETextCommit::OnEnter)ConfirmSplit();}
void UColdSteelInventoryPopup::Cancel(){Close();}
void UColdSteelInventoryPopup::Close(bool RestoreFocus){RemoveFromParent();if(RestoreFocus&&OwnerBoard.IsValid()&&OwnerBoard->IsVisible())OwnerBoard->SetKeyboardFocus();}
FReply UColdSteelInventoryPopup::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E){if(E.GetKey()==EKeys::Escape){Close();return FReply::Handled();}return Super::NativeOnKeyDown(G,E);}
FReply UColdSteelInventoryPopup::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent& E)
{
    // This popup is a separate viewport root, so the HUD never receives its background click.
    if(E.GetEffectingButton()==EKeys::LeftMouseButton&&OwnerBoard.IsValid())
        if(auto* HUD=OwnerBoard->TooltipHUD())
        {
            if(HUD->HandlePanelNavigationClick(E.GetScreenSpacePosition())){Close(false);return FReply::Handled();}
            if(HUD->HandleInventoryOutsideClick(E.GetScreenSpacePosition()))return FReply::Handled();
        }
    Close();return FReply::Handled();
}
FReply UColdSteelInventoryPopup::NativeOnPreviewKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape){Close();return FReply::Handled();}
    if((E.GetKey()==EKeys::Tab||E.GetKey()==EKeys::CapsLock||E.GetKey()==EKeys::P)&&OwnerBoard.IsValid())if(auto* HUD=OwnerBoard->TooltipHUD()){HUD->HandlePanelShortcut(E.GetKey(),E.IsRepeat());return FReply::Handled();}
    return Super::NativeOnPreviewKeyDown(G,E);
}
