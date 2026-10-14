#include "ColdSteelShopWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/EditableTextBox.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "String/LexFromString.h"
#include "Widgets/Layout/SDPIScaler.h"
using namespace ColdSteelInventory;

namespace
{
UTextBlock* ShopText(UWidgetTree* Tree,const FString& Caption,float Pixels=14,bool Bold=false)
{
    auto* T=Tree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Caption));
    T->SetFont(ColdSteelUI::TextFont(Pixels*.75f,Bold));T->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    T->SetAutoWrapText(false);T->SetVisibility(ESlateVisibility::HitTestInvisible);return T;
}
void ShopSet(UTextBlock* Text,const FString& Value)
{const auto T=FText::FromString(Value);if(!Text->GetText().EqualTo(T))Text->SetText(T);}
UButton* ShopButton(UWidgetTree* Tree,const FString& Caption)
{
    auto* B=Tree->ConstructWidget<UButton>();B->SetStyle(ColdSteelUI::ButtonStyle());B->SetContent(ShopText(Tree,Caption));
    Cast<UButtonSlot>(B->GetContent()->Slot)->SetPadding(FMargin(10,8));return B;
}
UBorder* ShopSurface(UWidgetTree* Tree)
{
    auto* B=Tree->ConstructWidget<UBorder>();B->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,8,ColdSteelUI::Border,1));
    B->SetPadding(FMargin(12));return B;
}
UEditableTextBox* QuantityBox(UWidgetTree* Tree)
{
    auto* Q=Tree->ConstructWidget<UEditableTextBox>();Q->SetText(FText::FromString(TEXT("1")));
    auto Edit=Q->GetWidgetStyle();Edit.TextStyle.SetFont(ColdSteelUI::NumberFont(10.5f));
    Edit.SetForegroundColor(ColdSteelUI::TextPrimary);Edit.SetFocusedForegroundColor(ColdSteelUI::TextPrimary);
    Edit.SetBackgroundImageNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,5,ColdSteelUI::Border,1));
    Edit.SetBackgroundImageHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,5,ColdSteelUI::HUDGold,1));
    Edit.SetBackgroundImageFocused(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,5,ColdSteelUI::HUDGold,1));
    Q->SetWidgetStyle(Edit);Q->SetSelectAllTextWhenFocused(true);return Q;
}
int64 ReadQuantity(const UEditableTextBox* Box)
{
    int64 Count=0;const FString Input=Box->GetText().ToString().TrimStartAndEnd();
    if(Input.IsNumeric()&&!Input.Contains(TEXT(".")))LexTryParseString(Count,*Input);return Count;
}
}

void UColdSteelShopWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(false);
    Model=GetGameInstance()->GetSubsystem<UColdSteelShopModel>();
    auto* Root=WidgetTree->ConstructWidget<UOverlay>();WidgetTree->RootWidget=Root;
    // Same one-pixel shell, 60px header and full-height drawer as the warehouse.
    auto* Shell=ShopSurface(WidgetTree);Shell->SetPadding(FMargin(1));
    Shell->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,10,ColdSteelUI::Border,1));
    // UOverlaySlot defaults to Left/Top: without Fill the drawer collapses to
    // header/button desired size and both Fill grid rows receive zero height.
    auto* ShellSlot=Root->AddChildToOverlay(Shell);
    ShellSlot->SetHorizontalAlignment(HAlign_Fill);ShellSlot->SetVerticalAlignment(VAlign_Fill);
    Shell->SetHorizontalAlignment(HAlign_Fill);Shell->SetVerticalAlignment(VAlign_Fill);
    auto* Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
    Blur->SetOverrideAutoRadiusCalculation(true);Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);Blur->SetCornerRadius(FVector4(10));
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10));Shell->SetContent(Blur);
    auto* Surface=ShopSurface(WidgetTree);Surface->SetPadding(FMargin(0));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius));Blur->SetContent(Surface);
    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();Surface->SetContent(Body);
    auto* HeaderSurface=ShopSurface(WidgetTree);HeaderSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius));
    HeaderSurface->SetPadding(FMargin(18,12));Body->AddChildToVerticalBox(HeaderSurface);
    auto* HeaderSize=WidgetTree->ConstructWidget<USizeBox>();HeaderSize->SetHeightOverride(36);HeaderSurface->SetContent(HeaderSize);
    auto* Header=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(Header);
    auto* TitleSlot=Header->AddChildToHorizontalBox(ShopText(WidgetTree,TEXT("商店"),20,true));
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    Balance=ShopText(WidgetTree,TEXT(""),12,true);Balance->SetColorAndOpacity(ColdSteelUI::HUDGoldLight);
    auto* BalanceSlot=Header->AddChildToHorizontalBox(Balance);BalanceSlot->SetVerticalAlignment(VAlign_Center);BalanceSlot->SetPadding(FMargin(0,0,12,0));
    auto* CloseButton=ShopButton(WidgetTree,TEXT("关闭 · O"));CloseButton->OnClicked.AddDynamic(this,&ThisClass::Close);Header->AddChildToHorizontalBox(CloseButton);

    auto AddSection=[&](bool Sale)
    {
        auto* Area=WidgetTree->ConstructWidget<UBorder>();Area->SetBrushColor(FLinearColor::Transparent);Area->SetPadding(FMargin(0));
        // Equal Fill weights keep the two spatial grids the same size.
        auto* AreaSlot=Body->AddChildToVerticalBox(Area);AreaSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        AreaSlot->SetHorizontalAlignment(HAlign_Fill);AreaSlot->SetVerticalAlignment(VAlign_Fill);
        Area->SetHorizontalAlignment(HAlign_Fill);Area->SetVerticalAlignment(VAlign_Fill);
        auto* Section=WidgetTree->ConstructWidget<UVerticalBox>();Area->SetContent(Section);
        auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();
        Section->AddChildToVerticalBox(Heading)->SetPadding(FMargin(12,6,12,6));
        auto* Title=Heading->AddChildToHorizontalBox(ShopText(WidgetTree,Sale?TEXT("待售物品"):TEXT("购买物品"),16,true));
        Title->SetSize(FSlateChildSize(ESlateSizeRule::Fill));Title->SetVerticalAlignment(VAlign_Center);
        auto* Previous=ShopButton(WidgetTree,TEXT("上一页"));Heading->AddChildToHorizontalBox(Previous);
        auto* PageText=ShopText(WidgetTree,TEXT("1 / 1"),12);PageText->SetJustification(ETextJustify::Center);
        auto* PageSize=WidgetTree->ConstructWidget<USizeBox>();PageSize->SetMinDesiredWidth(76);PageSize->SetContent(PageText);
        auto* PageSlot=Heading->AddChildToHorizontalBox(PageSize);PageSlot->SetVerticalAlignment(VAlign_Center);
        auto* Next=ShopButton(WidgetTree,TEXT("下一页"));Heading->AddChildToHorizontalBox(Next);
        auto* Grid=CreateWidget<UColdSteelShopGrid>(GetOwningPlayer());Grid->Configure(this,Sale);
        auto* GridSlot=Section->AddChildToVerticalBox(Grid);GridSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        GridSlot->SetHorizontalAlignment(HAlign_Fill);GridSlot->SetVerticalAlignment(VAlign_Fill);
        auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();Section->AddChildToVerticalBox(Actions)->SetPadding(FMargin(12,6,12,8));
        auto* Info=ShopText(WidgetTree,TEXT(""),12);Info->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);
        auto* InfoSlot=Actions->AddChildToHorizontalBox(Info);InfoSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));InfoSlot->SetVerticalAlignment(VAlign_Center);
        auto* QuantityLabel=Actions->AddChildToHorizontalBox(ShopText(WidgetTree,TEXT("数量"),12));QuantityLabel->SetPadding(FMargin(6,0));QuantityLabel->SetVerticalAlignment(VAlign_Center);
        auto* Quantity=QuantityBox(WidgetTree);auto* QuantitySize=WidgetTree->ConstructWidget<USizeBox>();
        QuantitySize->SetWidthOverride(58);QuantitySize->SetHeightOverride(32);QuantitySize->SetContent(Quantity);
        Actions->AddChildToHorizontalBox(QuantitySize)->SetPadding(FMargin(0,0,8,0));
        auto* Action=ShopButton(WidgetTree,Sale?TEXT("移出"):TEXT("购买"));Actions->AddChildToHorizontalBox(Action);
        if(Sale)
        {
            SaleArea=Area;SaleGrid=Grid;SaleInfo=Info;SaleQuantity=Quantity;SaleAction=Action;
            SalePrevious=Previous;SaleNext=Next;SalePage=PageText;
            Previous->OnClicked.AddDynamic(this,&ThisClass::PreviousSalePage);Next->OnClicked.AddDynamic(this,&ThisClass::NextSalePage);
            Action->OnClicked.AddDynamic(this,&ThisClass::RemoveSelected);Quantity->OnTextCommitted.AddDynamic(this,&ThisClass::SaleQuantityCommitted);
        }
        else
        {
            BuyArea=Area;BuyGrid=Grid;BuyInfo=Info;BuyQuantity=Quantity;BuyAction=Action;
            BuyPrevious=Previous;BuyNext=Next;BuyPage=PageText;
            Previous->OnClicked.AddDynamic(this,&ThisClass::PreviousBuyPage);Next->OnClicked.AddDynamic(this,&ThisClass::NextBuyPage);
            Action->OnClicked.AddDynamic(this,&ThisClass::BuySelected);
        }
    };
    AddSection(false);
    auto* Divider=WidgetTree->ConstructWidget<UBorder>();Divider->SetBrushColor(ColdSteelUI::Border);Divider->SetPadding(FMargin(0));
    auto* DividerSize=WidgetTree->ConstructWidget<USizeBox>();DividerSize->SetHeightOverride(1);DividerSize->SetContent(Divider);
    Body->AddChildToVerticalBox(DividerSize)->SetPadding(FMargin(12,0));
    AddSection(true);
    auto* Footer=WidgetTree->ConstructWidget<UHorizontalBox>();Body->AddChildToVerticalBox(Footer)->SetPadding(FMargin(12,8,12,4));
    Total=ShopText(WidgetTree,TEXT(""),14,true);Total->SetColorAndOpacity(ColdSteelUI::HUDGoldLight);Total->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);
    auto* TotalSlot=Footer->AddChildToHorizontalBox(Total);TotalSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TotalSlot->SetVerticalAlignment(VAlign_Center);
    auto* ClearButton=ShopButton(WidgetTree,TEXT("清空"));ClearButton->OnClicked.AddDynamic(this,&ThisClass::Clear);
    Footer->AddChildToHorizontalBox(ClearButton)->SetPadding(FMargin(8,0));
    SellButton=ShopButton(WidgetTree,TEXT("确认出售…"));SellButton->OnClicked.AddDynamic(this,&ThisClass::RequestSell);Footer->AddChildToHorizontalBox(SellButton);
    Message=ShopText(WidgetTree,TEXT(""),12);Message->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);
    auto* MessageSize=WidgetTree->ConstructWidget<USizeBox>();MessageSize->SetHeightOverride(18);MessageSize->SetContent(Message);
    Body->AddChildToVerticalBox(MessageSize)->SetPadding(FMargin(12,0,12,8));

    Confirmation=WidgetTree->ConstructWidget<UBorder>();Confirmation->SetBrushColor(FLinearColor(0,0,0,.72f));Confirmation->SetPadding(FMargin(20));
    Confirmation->SetHorizontalAlignment(HAlign_Fill);Confirmation->SetVerticalAlignment(VAlign_Center);
    auto* ConfirmationSlot=Root->AddChildToOverlay(Confirmation);
    ConfirmationSlot->SetHorizontalAlignment(HAlign_Fill);ConfirmationSlot->SetVerticalAlignment(VAlign_Fill);
    Confirmation->SetVisibility(ESlateVisibility::Collapsed);
    ConfirmationCard=WidgetTree->ConstructWidget<USizeBox>();ConfirmationCard->SetHeightOverride(360);Confirmation->SetContent(ConfirmationCard);
    auto* ConfirmSurface=ShopSurface(WidgetTree);ConfirmSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10,ColdSteelUI::HUDGold,1));ConfirmationCard->SetContent(ConfirmSurface);
    auto* ConfirmBody=WidgetTree->ConstructWidget<UVerticalBox>();ConfirmSurface->SetContent(ConfirmBody);
    ConfirmBody->AddChildToVerticalBox(ShopText(WidgetTree,TEXT("确认出售这些物品？"),16,true));
    auto* ConfirmScroll=WidgetTree->ConstructWidget<UScrollBox>();ConfirmScroll->SetAllowOverscroll(false);
    ConfirmBody->AddChildToVerticalBox(ConfirmScroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    ConfirmationSummary=ShopText(WidgetTree,TEXT(""));ConfirmationSummary->SetAutoWrapText(true);ConfirmScroll->AddChild(ConfirmationSummary);
    ConfirmationTotal=ShopText(WidgetTree,TEXT(""),16,true);ConfirmationTotal->SetColorAndOpacity(ColdSteelUI::HUDGoldLight);
    ConfirmBody->AddChildToVerticalBox(ConfirmationTotal)->SetPadding(FMargin(0,14,0,14));
    auto* ConfirmActions=WidgetTree->ConstructWidget<UHorizontalBox>();ConfirmBody->AddChildToVerticalBox(ConfirmActions);
    CancelButton=ShopButton(WidgetTree,TEXT("返回修改"));CancelButton->OnClicked.AddDynamic(this,&ThisClass::CancelSell);
    auto* CancelSlot=ConfirmActions->AddChildToHorizontalBox(CancelButton);CancelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CancelSlot->SetPadding(FMargin(0,0,8,0));
    auto* Final=ShopButton(WidgetTree,TEXT("出售并获得灵魂"));Final->OnClicked.AddDynamic(this,&ThisClass::ConfirmSell);
    ConfirmActions->AddChildToHorizontalBox(Final)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
}
TSharedRef<SWidget> UColdSteelShopWidget::RebuildWidget()
{return SNew(SDPIScaler).DPIScale_Lambda([this]{return 1.f/FMath::Max(.1f,UWidgetLayoutLibrary::GetViewportScale(this));})[Super::RebuildWidget()];}
void UColdSteelShopWidget::Configure(UColdSteelHUDWidget* Owner){HUD=Owner;}
void UColdSteelShopWidget::NativeConstruct(){Super::NativeConstruct();if(Model&&!Changed.IsValid())Changed=Model->OnChanged.AddUObject(this,&ThisClass::Refresh);Refresh();}
void UColdSteelShopWidget::NativeDestruct(){if(Model&&Changed.IsValid())Model->OnChanged.Remove(Changed);Changed.Reset();Super::NativeDestruct();}
void UColdSteelShopWidget::ResetSession(){CancelConfirmation();BuyGrid->ResetPage();SaleGrid->ResetPage();BuyQuantity->SetText(FText::FromString(TEXT("1")));Refresh();}
UTexture2D* UColdSteelShopWidget::IconFor(const FColdSteelItem& Item)
{
    const FString Path=Text(Item,TEXT("ue_icon"));if(Path.IsEmpty())return nullptr;
    if(const auto* Existing=Icons.Find(Path))return Existing->Get();if(Icons.Num()>=256)return nullptr;
    auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path);
    Icons.Add(Path,Texture);return Texture;
}
void UColdSteelShopWidget::Refresh()
{
    if(!Model||!Model->IsOpen())return;
    const auto* Status=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    ShopSet(Balance,FString::Printf(TEXT("灵魂  %lld"),Status->SoulBalance()));
    TArray<FColdSteelShopSaleLine> Stock,Sale;
    for(const auto& Item:Model->Stock())Stock.Add({Item,1,Model->BuyPrice(Item.Definition)});
    for(const auto& Selection:Model->Selection())if(const auto* Item=Status->FindItem(Selection.Id))Sale.Add({*Item,Selection.Count,Model->SellPrice(*Item)});
    BuyGrid->SetItems(Stock);SaleGrid->SetItems(Sale);
    FColdSteelShopQuote Quote;const bool Valid=Model->QuoteSale(Quote);
    const FString Income=FString::Printf(TEXT("预计获得  %lld 灵魂"),Valid?Quote.Total:0);
    ShopSet(Total,Income);Total->SetToolTipText(FText::FromString(Income));SellButton->SetIsEnabled(Valid);
    ShopSet(Message,Model->ResultMessage());Message->SetToolTipText(FText::FromString(Model->ResultMessage()));
}
void UColdSteelShopWidget::GridChanged(bool Sale,bool ResetQuantity)
{
    auto* Grid=Sale?SaleGrid.Get():BuyGrid.Get();if(!Grid)return;
    auto* Info=Sale?SaleInfo.Get():BuyInfo.Get();auto* Quantity=Sale?SaleQuantity.Get():BuyQuantity.Get();
    auto* Action=Sale?SaleAction.Get():BuyAction.Get();const auto* Line=Grid->SelectedLine();
    const FString Description=Line?FString::Printf(TEXT("%s · %lld 灵魂/件"),*Text(Line->Item,TEXT("name")),Line->UnitPrice)
        :Sale?TEXT("拖入或右键背包物品加入待售"):TEXT("选择商品购买；右键购买 1 件");
    ShopSet(Info,Description);Info->SetToolTipText(FText::FromString(Description));Action->SetIsEnabled(Line!=nullptr);Quantity->SetIsEnabled(Line!=nullptr);
    if(ResetQuantity||(Sale&&!Quantity->HasKeyboardFocus()))Quantity->SetText(FText::FromString(FString::Printf(TEXT("%lld"),Line&&Sale?Line->Count:1)));
    ShopSet(Sale?SalePage.Get():BuyPage.Get(),FString::Printf(TEXT("%d / %d"),Grid->PageNumber(),Grid->PageCount()));
    (Sale?SalePrevious.Get():BuyPrevious.Get())->SetIsEnabled(Grid->PageNumber()>1);
    (Sale?SaleNext.Get():BuyNext.Get())->SetIsEnabled(Grid->PageNumber()<Grid->PageCount());
}
void UColdSteelShopWidget::ActivateGridItem(bool Sale){if(Sale)RemoveSelected();else BuySelected();}
void UColdSteelShopWidget::BuySelected()
{
    if(IsConfirming())return;const auto* Line=BuyGrid->SelectedLine();if(!Line)return;
    // Copy the key before Buy publishes OnChanged and repacks the grid.
    const FString Definition=Line->Item.Definition;const int64 Count=ReadQuantity(BuyQuantity);
    Model->Buy(Definition,Count>=1&&Count<=99?int32(Count):0);
}
void UColdSteelShopWidget::RemoveSelected()
{
    if(IsConfirming())return;if(const auto* Line=SaleGrid->SelectedLine()){const FString Id=Line->Item.InstanceId;Model->RemoveFromSale(Id);}
}
void UColdSteelShopWidget::SaleQuantityCommitted(const FText&,ETextCommit::Type)
{
    if(IsConfirming())return;if(const auto* Line=SaleGrid->SelectedLine())
    {const FString Id=Line->Item.InstanceId;Model->SetSaleCount(Id,ReadQuantity(SaleQuantity));GridChanged(true,true);}
}
void UColdSteelShopWidget::PreviousBuyPage(){BuyGrid->TurnPage(-1);}
void UColdSteelShopWidget::NextBuyPage(){BuyGrid->TurnPage(1);}
void UColdSteelShopWidget::PreviousSalePage(){SaleGrid->TurnPage(-1);}
void UColdSteelShopWidget::NextSalePage(){SaleGrid->TurnPage(1);}
FReply UColdSteelShopWidget::NativeOnMouseWheel(const FGeometry& G,const FPointerEvent& E)
{
    if(IsConfirming())return FReply::Handled();const int32 Direction=E.GetWheelDelta()>0?-1:E.GetWheelDelta()<0?1:0;
    if(BuyArea->GetCachedGeometry().IsUnderLocation(E.GetScreenSpacePosition())){BuyGrid->TurnPage(Direction,true);return FReply::Handled();}
    if(SaleArea->GetCachedGeometry().IsUnderLocation(E.GetScreenSpacePosition())){SaleGrid->TurnPage(Direction,true);return FReply::Handled();}
    return Super::NativeOnMouseWheel(G,E);
}
void UColdSteelShopWidget::Close(){if(HUD&&HUD->IsShopOpen())HUD->ToggleShop();}
void UColdSteelShopWidget::Clear(){CancelConfirmation();Model->ClearSale();}
bool UColdSteelShopWidget::AddToSale(const FString& Id)
{
    if(IsConfirming()||!Model||!Model->AddToSale(Id))return false;
    SaleGrid->SelectKey(Id,true);return true;
}
bool UColdSteelShopWidget::IsConfirming()const{return Confirmation&&Confirmation->GetVisibility()!=ESlateVisibility::Collapsed;}
bool UColdSteelShopWidget::ConfirmationContains(FVector2D P)const{return IsConfirming()&&ConfirmationCard->GetCachedGeometry().IsUnderLocation(P);}
void UColdSteelShopWidget::CancelConfirmation(){if(Confirmation)Confirmation->SetVisibility(ESlateVisibility::Collapsed);PendingQuote={};}
void UColdSteelShopWidget::CancelSell(){CancelConfirmation();}
void UColdSteelShopWidget::RequestSell()
{
    if(HUD)HUD->HideItemTooltip(true);if(!Model->QuoteSale(PendingQuote))return;
    FString Summary;
    for(const auto& Line:PendingQuote.Lines)Summary+=FString::Printf(TEXT("%s × %lld    %lld 灵魂\n"),*Text(Line.Item,TEXT("name")),Line.Count,Line.Count*Line.UnitPrice);
    ShopSet(ConfirmationSummary,Summary);ShopSet(ConfirmationTotal,FString::Printf(TEXT("合计获得  %lld 灵魂"),PendingQuote.Total));
    Confirmation->SetVisibility(ESlateVisibility::Visible);
}
void UColdSteelShopWidget::ConfirmSell(){const auto Quote=PendingQuote;CancelConfirmation();Model->ConfirmSale(Quote);}
bool UColdSteelShopWidget::HandleItemDrop(UColdSteelItemDrag* Drag,FVector2D Position)
{
    if(!Drag||!GetCachedGeometry().IsUnderLocation(Position))return false;
    const auto* Status=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!IsConfirming()&&SaleArea->GetCachedGeometry().IsUnderLocation(Position)&&Drag->IsCurrent(Status))AddToSale(Drag->ItemId);
    return true; // Never let a drop over the shop fall through to world-drop.
}
bool UColdSteelShopWidget::NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation* Op){return Cast<UColdSteelItemDrag>(Op)!=nullptr;}
bool UColdSteelShopWidget::NativeOnDrop(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Op){return HandleItemDrop(Cast<UColdSteelItemDrag>(Op),E.GetScreenSpacePosition());}
