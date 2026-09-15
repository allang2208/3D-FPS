#include "ColdSteelWarehouseWidget.h"
#include "ColdSteelWarehouseSortOption.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/ComboBoxString.h"
#include "Components/TextBlock.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/BackgroundBlur.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"

UTextBlock* UColdSteelWarehouseWidget::Text(const FString& Caption,float Pixels,bool Numeric,bool Medium)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Caption));T->SetColorAndOpacity(GunsmithUI::Text);
    T->SetFont(Numeric?GunsmithUI::NumberFont(Pixels/Scale,Medium):GunsmithUI::TextFont(Pixels/Scale,Medium));
    T->SetVisibility(ESlateVisibility::HitTestInvisible);Labels.Add({T,Pixels,Numeric,Medium});return T;
}
UButton* UColdSteelWarehouseWidget::Button(const FString& Caption)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();B->SetContent(Text(Caption,14));Buttons.Add(B);return B;
}
void UColdSteelWarehouseWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Scale=ColdSteelUI::PixelScale(this);
    auto* Shell=WidgetTree->ConstructWidget<UBorder>();Shell->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,10/Scale,GunsmithUI::Edge,1/Scale));Shell->SetPadding(FMargin(1/Scale));WidgetTree->RootWidget=Shell;
    Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetOverrideAutoRadiusCalculation(true);Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);Blur->SetCornerRadius(FVector4(10,10,10,10));Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));Shell->SetContent(Blur);
    auto* Tint=WidgetTree->ConstructWidget<UBorder>();Tint->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));Tint->SetPadding(FMargin(0));Blur->SetContent(Tint);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Tint->SetContent(Stack);
    Header=WidgetTree->ConstructWidget<UBorder>();Header->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));Stack->AddChildToVerticalBox(Header);
    HeaderSize=WidgetTree->ConstructWidget<USizeBox>();Header->SetContent(HeaderSize);
    auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(Heading);
    auto* TitleSlot=Heading->AddChildToHorizontalBox(Text(TEXT("仓库"),20,false,true));TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    Capacity=Text(TEXT(""),12,true);auto* CapacitySlot=Heading->AddChildToHorizontalBox(Capacity);CapacitySlot->SetVerticalAlignment(VAlign_Center);CapacitySlot->SetPadding(FMargin(0,0,12/Scale,0));
    auto* X=Button(TEXT("收起仓库"));Heading->AddChildToHorizontalBox(X);X->OnClicked.AddDynamic(this,&ThisClass::Close);
    ActionSize=WidgetTree->ConstructWidget<USizeBox>();ActionSlot=Stack->AddChildToVerticalBox(ActionSize);
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();ActionSize->SetContent(Actions);
    auto AddAction=[&](UWidget* W){auto* Slot=Actions->AddChildToHorizontalBox(W);Slot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));Slot->SetHorizontalAlignment(HAlign_Fill);Slot->SetVerticalAlignment(VAlign_Fill);ActionSlots.Add(Slot);};
    auto* Store=Button(TEXT("全部存入"));AddAction(Store);Store->OnClicked.AddDynamic(this,&ThisClass::StoreAll);
    auto* Match=Button(TEXT("取出同类"));AddAction(Match);Match->OnClicked.AddDynamic(this,&ThisClass::Matching);
    auto* DepositMatching=Button(TEXT("存入同类"));AddAction(DepositMatching);DepositMatching->OnClicked.AddDynamic(this,&ThisClass::StoreMatching);
    DepositMatching->SetToolTipText(FText::FromString(TEXT("存入背包中仓库已有的同种物品，优先合并堆叠；武器与装备不参与。")));
    SortMenu=WidgetTree->ConstructWidget<UComboBoxString>();SortMenu->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::SortOption);
    for(const FString Option:{TEXT("整理仓库"),TEXT("按稀有度"),TEXT("按价值"),TEXT("近战武器"),TEXT("远程武器"),TEXT("盾牌"),TEXT("防具与饰品"),TEXT("消耗品"),TEXT("强化材料"),TEXT("材料"),TEXT("贡品"),TEXT("金币"),TEXT("其他")})SortMenu->AddOption(Option);
    SortMenu->SetSelectedIndex(0);AddAction(SortMenu);SortMenu->OnSelectionChanged.AddDynamic(this,&ThisClass::SortChanged);
    Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetAllowOverscroll(false);Stack->AddChildToVerticalBox(Scroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Board=CreateWidget<UColdSteelInventoryWidget>(GetOwningPlayer());Board->ConfigureWarehouse(HUD);Scroll->AddChild(Board);
    auto* Footer=WidgetTree->ConstructWidget<UHorizontalBox>();FooterSlot=Stack->AddChildToVerticalBox(Footer);
    Previous=Button(TEXT("上一页"));Footer->AddChildToHorizontalBox(Previous);Previous->OnClicked.AddDynamic(this,&ThisClass::PreviousPage);
    Page=Text(TEXT(""),12,true);Page->SetJustification(ETextJustify::Center);auto* PageSlot=Footer->AddChildToHorizontalBox(Page);PageSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));PageSlot->SetVerticalAlignment(VAlign_Center);
    Next=Button(TEXT("下一页"));Footer->AddChildToHorizontalBox(Next);Next->OnClicked.AddDynamic(this,&ThisClass::NextPage);
    UpdateScale();Refresh();
}
void UColdSteelWarehouseWidget::UpdateScale()
{
    Scale=ColdSteelUI::PixelScale(this);Header->SetPadding(FMargin(18/Scale,12/Scale));HeaderSize->SetHeightOverride(36/Scale);
    ActionSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);ActionSlot->SetPadding(FMargin(10/Scale,8/Scale));FooterSlot->SetPadding(FMargin(12/Scale,10/Scale));Scroll->SetScrollbarThickness(FVector2D(6/Scale));
    for(auto Weak:ActionSlots)if(auto* ActionButtonSlot=Weak.Get())ActionButtonSlot->SetPadding(FMargin(ColdSteelUI::ActionGap*.5f/Scale,0));
    for(const auto& L:Labels)if(auto* T=L.Widget.Get())T->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    const FButtonStyle Style=ColdSteelUI::ButtonStyle(Scale);
    for(auto Weak:Buttons)if(auto* B=Weak.Get()){B->SetStyle(Style);Cast<UButtonSlot>(B->GetContent()->Slot)->SetPadding(FMargin(10/Scale,8/Scale));}
    auto Combo=SortMenu->GetWidgetStyle();auto CB=Combo.ComboButtonStyle;CB.SetButtonStyle(Style);CB.SetMenuBorderBrush(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(25,252),6/Scale,GunsmithUI::Edge));
    CB.DownArrowImage.ImageSize=FVector2D(8/Scale,8/Scale);CB.SetDownArrowPadding(FMargin(4/Scale,0,0,0));CB.SetShadowOffset(FVector2D::ZeroVector);
    Combo.SetComboButtonStyle(CB);SortMenu->SetWidgetStyle(Combo);SortMenu->SetHasDownArrow(true);
    // Balance the arrow's width on the left so the caption is centered in the whole button.
    SortMenu->SetContentPadding(FMargin(22/Scale,8/Scale,10/Scale,8/Scale));
}
void UColdSteelWarehouseWidget::Configure(UColdSteelHUDWidget* Owner){HUD=Owner;if(Board)Board->ConfigureWarehouse(Owner);}
void UColdSteelWarehouseWidget::NativeConstruct(){Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::Refresh);Refresh();}
void UColdSteelWarehouseWidget::NativeTick(const FGeometry& G,float Delta){Super::NativeTick(G,Delta);if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f))UpdateScale();}
void UColdSteelWarehouseWidget::NativeDestruct(){if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();CancelInteraction();Super::NativeDestruct();}
void UColdSteelWarehouseWidget::CancelInteraction(){if(Board)Board->CancelInteraction();}
void UColdSteelWarehouseWidget::ResetPage(){Model->WarehousePage=0;Board->ResetStoragePage();Scroll->ScrollToStart();Refresh();}
void UColdSteelWarehouseWidget::Refresh()
{
    if(!Model||!Capacity)return;int32 Used=0,Count=0;for(const auto& I:Model->Items())if(I.Place==4){Used+=I.Width*I.Height;++Count;}
    const int32 Pages=Model->WarehouseCapacity()/ColdSteelWarehouse::CellsPerPage;Model->WarehousePage=FMath::Clamp(Model->WarehousePage,0,Pages-1);
    if(ShownPage!=Model->WarehousePage){ShownPage=Model->WarehousePage;if(Board)Board->ResetStoragePage();Scroll->ScrollToStart();}
    Capacity->SetText(FText::FromString(FString::Printf(TEXT("%d / %d 格"),Used,Model->WarehouseCapacity())));
    Page->SetText(FText::FromString(FString::Printf(TEXT("%d / %d 页 · %d 件"),Model->WarehousePage+1,Pages,Count)));
    Previous->SetIsEnabled(Model->WarehousePage>0);Next->SetIsEnabled(Model->WarehousePage<Pages-1);
    if(Board)Board->LoadIcons();
}
void UColdSteelWarehouseWidget::Close(){if(HUD)HUD->CloseWarehouse();}
void UColdSteelWarehouseSortOption::SetCaption(const FString& Caption){auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Caption));Label->SetFont(GunsmithUI::TextFont(14/ColdSteelUI::PixelScale(this)));Label->SetColorAndOpacity(GunsmithUI::Text);Label->SetJustification(ETextJustify::Center);WidgetTree->RootWidget=Label;}
UWidget* UColdSteelWarehouseWidget::SortOption(FString Item){auto* Option=CreateWidget<UColdSteelWarehouseSortOption>(GetOwningPlayer());Option->SetCaption(Item);return Option;}
void UColdSteelWarehouseWidget::StoreAll(){Model->WarehouseBatch(false);Board->InteractionMessage=Model->ResultMessage();Refresh();}
void UColdSteelWarehouseWidget::Matching(){Model->WarehouseBatch(true);Board->InteractionMessage=Model->ResultMessage();Refresh();}
void UColdSteelWarehouseWidget::StoreMatching(){Model->StoreMatchingToWarehouse();Board->InteractionMessage=Model->ResultMessage();Refresh();}
void UColdSteelWarehouseWidget::PreviousPage(){FSlateApplication::Get().CancelDragDrop();Model->WarehousePage=FMath::Max(0,Model->WarehousePage-1);Board->ResetStoragePage();Scroll->ScrollToStart();Refresh();}
void UColdSteelWarehouseWidget::NextPage(){FSlateApplication::Get().CancelDragDrop();Model->WarehousePage=FMath::Min(Model->WarehouseCapacity()/ColdSteelWarehouse::CellsPerPage-1,Model->WarehousePage+1);Board->ResetStoragePage();Scroll->ScrollToStart();Refresh();}
void UColdSteelWarehouseWidget::SortChanged(FString Selection,ESelectInfo::Type Type){const int32 N=SortMenu->FindOptionIndex(Selection);if(N<1)return;Model->SortWarehouse(N==1?TEXT("rarity"):N==2?TEXT("price"):TEXT("category"),N-3);SortMenu->SetSelectedIndex(0);Board->InteractionMessage=Model->ResultMessage();Scroll->ScrollToStart();Refresh();}
