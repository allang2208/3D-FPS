#include "ColdSteelHUDWidget.h"
#include "ColdSteelMountButton.h"
#include "ColdSteelMountGearPanel.h"
#include "ColdSteelShopModel.h"
#include "ColdSteelInventoryWidget.h"
#include "SColdSteelHorseMarket.h"
#include "Components/NativeWidgetHost.h"
#include "Components/BackgroundBlur.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/SizeBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Brushes/SlateNoResource.h"
#include "../Movement/StableHorseAppearance.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/ButtonSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WrapBox.h"

namespace
{
struct FPotionChoice { const TCHAR* Id; const TCHAR* Name; };
constexpr FPotionChoice Potions[]={{TEXT("hp_potion"),TEXT("治疗药水")},{TEXT("hp_potion_medium"),TEXT("中级生命药水")},
    {TEXT("hp_potion_high"),TEXT("高级生命药水")},{TEXT("hp_potion_special"),TEXT("特级生命药水")}};
void SetTextIfChanged(UTextBlock* Widget,const FString& Value)
{
    const FText New=FText::FromString(Value);if(Widget && !Widget->GetText().EqualTo(New))Widget->SetText(New);
}
UTextBlock* Caption(UButton* Button){return CastChecked<UTextBlock>(Button->GetContent());}
bool Carried(const FColdSteelItem& Item){return Item.Place==0||Item.Place==ColdSteelInventory::ColdSteelCompartment::Place;}
}

void UColdSteelMountButton::Bind(UColdSteelHUDWidget* Widget,EMountPageAction InAction,FGuid InHorse,int32 InTier)
{
    Journal=Widget;Action=InAction;Horse=InHorse;Tier=InTier;
    OnClicked.AddDynamic(this,&ThisClass::Press);
}
void UColdSteelMountButton::Press()
{
    auto* HUD=Journal.Get();if(!HUD)return;
    HUD->PlayButtonClick();
    switch(Action)
    {
        case EMountPageAction::Buy: HUD->BuyViewedMount();break;
        case EMountPageAction::Back: HUD->CloseMountDetails(true);break;
        case EMountPageAction::Deploy: HUD->ToggleMountDeployment();break;
        case EMountPageAction::Call: HUD->CallJournalMount();break;
        case EMountPageAction::Potion: HUD->GiveJournalPotion(Tier);break;
        case EMountPageAction::Release: HUD->RequestReleaseMount();break;
        case EMountPageAction::ReleaseConfirm: HUD->ConfirmReleaseMount();break;
        case EMountPageAction::ReleaseCancel: HUD->CancelReleaseMount();break;
    }
}

bool UColdSteelHUDWidget::IsViewingMountDetails() const
{
    return bMountDetailsOpen && ViewedMount.IsValid() && MountDetailsDrawer && MountDetailsDrawer->GetVisibility()==ESlateVisibility::Visible;
}

bool UColdSteelHUDWidget::QuickEquipMountTack(const FString& ItemId)
{
    return IsViewingMountDetails() && MountGear && MountGear->TryQuickEquip(ItemId);
}

UWidget* UColdSteelHUDWidget::BuildMountPage()
{
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();
    MountPageHint=MakeInventoryText(TEXT(""),15,ColdSteelUI::TextSecondary);MountPageHint->SetAutoWrapText(true);
    Column->AddChildToVerticalBox(MountPageHint)->SetPadding(FMargin(8/Scale,6/Scale));
    MountList=WidgetTree->ConstructWidget<UNativeWidgetHost>();
    Column->AddChildToVerticalBox(MountList)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    // Match InventoryPanel's exact ColdSteel frosted glass shell (10px radius, 9px blur, 60px HeaderTint)
    auto* Root=CastChecked<UCanvasPanel>(WidgetTree->RootWidget);
    MountDetailsDrawer=MakeSurface(FLinearColor::Transparent,10/Scale,ColdSteelUI::Border,1/Scale);
    MountDetailsDrawer->SetPadding(FMargin(1.f/Scale));
    MountDrawerSlot=Root->AddChildToCanvas(MountDetailsDrawer);MountDrawerSlot->SetAutoSize(false);MountDrawerSlot->SetZOrder(40);
    MountDetailsDrawer->SetVisibility(ESlateVisibility::Collapsed);

    auto* Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
    Blur->SetOverrideAutoRadiusCalculation(true);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
    Blur->SetCornerRadius(FVector4(10,10,10,10));
    Blur->SetApplyAlphaToBlur(true);
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
    MountDetailsDrawer->SetContent(Blur);

    auto* Glass=MakeSurface(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale,FLinearColor::Transparent,0);
    Glass->SetPadding(FMargin(0));
    Blur->SetContent(Glass);

    auto* Shell=WidgetTree->ConstructWidget<UVerticalBox>();
    Glass->SetContent(Shell);

    auto MakeAction=[&](const TCHAR* Title,EMountPageAction Action,int32 Tier=0)
    {
        auto* B=WidgetTree->ConstructWidget<UColdSteelMountButton>();B->Bind(this,Action,{},Tier);
        auto Style=ColdSteelUI::ButtonStyle(Scale);
        if(Action==EMountPageAction::Buy || Action==EMountPageAction::Call)
        {
            Style.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(62,53,36,232)),5/Scale,ColdSteelUI::HUDGold,1.2f/Scale));
            Style.SetHovered(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(78,66,43,244)),5/Scale,ColdSteelUI::HUDGoldLight,1.4f/Scale));
            Style.SetPressed(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(42,36,25,244)),5/Scale,ColdSteelUI::HUDGold,1.4f/Scale));
            Style.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(30,200),5/Scale,ColdSteelUI::HUDGoldDim,1/Scale));
        }
        else if(Action==EMountPageAction::Potion)
        {
            Style.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::Health.R,ColdSteelUI::Health.G,ColdSteelUI::Health.B,.18f),5/Scale,
                FLinearColor(ColdSteelUI::Health.R,ColdSteelUI::Health.G,ColdSteelUI::Health.B,.52f),1/Scale));
            Style.SetHovered(ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::Health.R,ColdSteelUI::Health.G,ColdSteelUI::Health.B,.30f),5/Scale,
                ColdSteelUI::Health,1.2f/Scale));
        }
        else if(Action==EMountPageAction::Release || Action==EMountPageAction::ReleaseConfirm)
        {
            Style.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::Danger.R,ColdSteelUI::Danger.G,ColdSteelUI::Danger.B,Action==EMountPageAction::ReleaseConfirm?.32f:.16f),5/Scale,
                FLinearColor(ColdSteelUI::Danger.R,ColdSteelUI::Danger.G,ColdSteelUI::Danger.B,Action==EMountPageAction::ReleaseConfirm?.88f:.55f),1.1f/Scale));
            Style.SetHovered(ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::Danger.R,ColdSteelUI::Danger.G,ColdSteelUI::Danger.B,.42f),5/Scale,
                ColdSteelUI::Danger,1.3f/Scale));
            Style.SetPressed(ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::Danger.R,ColdSteelUI::Danger.G,ColdSteelUI::Danger.B,.22f),5/Scale,
                ColdSteelUI::Danger,1.3f/Scale));
        }
        B->SetStyle(Style);
        B->SetContent(MakeInventoryText(Title,Action==EMountPageAction::Potion?12.5f:14.f,
            (Action==EMountPageAction::Buy || Action==EMountPageAction::Call)?ColdSteelUI::HUDGoldLight:
            (Action==EMountPageAction::Release || Action==EMountPageAction::ReleaseConfirm)?FLinearColor(1.f,.78f,.80f,1.f):ColdSteelUI::TextPrimary,false,true));
        if(auto* Slot=Cast<UButtonSlot>(B->GetContent()->Slot))
            Slot->SetPadding(Action==EMountPageAction::Potion?FMargin(10/Scale,5/Scale):FMargin(14/Scale,9/Scale));
        return B;
    };

    // 60px Header aligned pixel-for-pixel with InventoryPanel header right beside it
    auto* Header=MakeSurface(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale,FLinearColor::Transparent,0);
    Header->SetPadding(FMargin(18/Scale,12/Scale));
    auto* HeaderSize=WidgetTree->ConstructWidget<USizeBox>();
    HeaderSize->SetHeightOverride(36/Scale);
    Header->SetContent(HeaderSize);
    auto* HeaderRow=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(HeaderRow);
    auto* AccentBar=MakeSurface(ColdSteelUI::HUDGold,1/Scale,FLinearColor::Transparent,0);
    auto* AccentSize=WidgetTree->ConstructWidget<USizeBox>();
    AccentSize->SetWidthOverride(3/Scale);AccentSize->SetHeightOverride(20/Scale);AccentSize->SetContent(AccentBar);
    HeaderRow->AddChildToHorizontalBox(AccentSize)->SetVerticalAlignment(VAlign_Center);
    auto* TitleSlot=HeaderRow->AddChildToHorizontalBox(MakeInventoryText(TEXT("马匹详情"),20,ColdSteelUI::TextPrimary,false,true));
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);TitleSlot->SetPadding(FMargin(10/Scale,0,0,0));
    HeaderRow->AddChildToHorizontalBox(MakeAction(TEXT("‹  返回名册"),EMountPageAction::Back))->SetVerticalAlignment(VAlign_Center);
    Shell->AddChildToVerticalBox(Header);

    MountDetailsScroll=WidgetTree->ConstructWidget<UScrollBox>();MountDetailsScroll->SetAllowOverscroll(false);
    auto ScrollStyle=MountDetailsScroll->GetWidgetStyle();
    ScrollStyle.SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource());
    MountDetailsScroll->SetWidgetStyle(ScrollStyle);
    MountDetailsScroll->SetScrollBarVisibility(ESlateVisibility::Collapsed);
    auto* ScrollSlot=Shell->AddChildToVerticalBox(MountDetailsScroll);ScrollSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    ScrollSlot->SetPadding(FMargin(14/Scale,10/Scale));
    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();MountDetailsScroll->AddChild(Body);
    MountGear=CreateWidget<UColdSteelMountGearPanel>(GetOwningPlayer());Body->AddChildToVerticalBox(MountGear);

    // Embedded Horse Spatial Backpack (reuses UColdSteelInventoryWidget + all backpack interaction rules!)
    MountBagBoard=CreateWidget<UColdSteelInventoryWidget>(GetOwningPlayer());
    MountBagBoard->ConfigureMountBag(this,2);
    Body->AddChildToVerticalBox(MountBagBoard)->SetPadding(FMargin(0,10/Scale,0,0));

    MountBagEmptyHintBox=MakeSurface(ColdSteelUI::Gray(14,212),8/Scale,ColdSteelUI::Border,1/Scale);
    MountBagEmptyHintBox->SetPadding(FMargin(14/Scale,12/Scale));
    MountBagEmptyHintText=MakeInventoryText(TEXT(""),12.5f,ColdSteelUI::TextSecondary);
    MountBagEmptyHintText->SetAutoWrapText(true);
    MountBagEmptyHintBox->SetContent(MountBagEmptyHintText);
    MountBagEmptyHintBox->SetVisibility(ESlateVisibility::Collapsed);
    Body->AddChildToVerticalBox(MountBagEmptyHintBox)->SetPadding(FMargin(0,10/Scale,0,0));

    // Quick-heal potion care strip (synced with real right-hand spatial backpack)
    MountPotionPanel=MakeSurface(ColdSteelUI::Gray(14,218),6/Scale,ColdSteelUI::Border,1/Scale);
    MountPotionPanel->SetPadding(FMargin(12/Scale,8/Scale));
    auto* PotionBox=WidgetTree->ConstructWidget<UVerticalBox>();
    MountPotionPanel->SetContent(PotionBox);
    MountPotionHint=MakeInventoryText(TEXT(""),12.5f,ColdSteelUI::TextSecondary);
    PotionBox->AddChildToVerticalBox(MountPotionHint)->SetPadding(FMargin(0,0,0,6/Scale));
    auto* PotionRow=WidgetTree->ConstructWidget<UWrapBox>();PotionRow->SetInnerSlotPadding(FVector2D(6/Scale,5/Scale));
    PotionBox->AddChildToVerticalBox(PotionRow);
    MountPotions.Reset();
    for(int32 I=0;I<UE_ARRAY_COUNT(Potions);++I)
    {
        auto* B=MakeAction(Potions[I].Name,EMountPageAction::Potion,I);MountPotions.Add(B);PotionRow->AddChildToWrapBox(B);
    }
    Body->AddChildToVerticalBox(MountPotionPanel)->SetPadding(FMargin(0,10/Scale,0,0));

    // Fixed authoritative footer with market soul-balance delta readout
    auto* Footer=MakeSurface(ColdSteelUI::Content,0,ColdSteelUI::Border,1/Scale);
    Footer->SetPadding(FMargin(16/Scale,10/Scale));Shell->AddChildToVerticalBox(Footer);
    auto* FooterStack=WidgetTree->ConstructWidget<UVerticalBox>();Footer->SetContent(FooterStack);
    MountBalanceDelta=MakeInventoryText(TEXT(""),12.5f,ColdSteelUI::HUDGoldLight,true);
    MountBalanceDelta->SetVisibility(ESlateVisibility::Collapsed);
    FooterStack->AddChildToVerticalBox(MountBalanceDelta)->SetPadding(FMargin(2/Scale,0,0,7/Scale));
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();FooterStack->AddChildToVerticalBox(Actions);
    MountBuy=MakeAction(TEXT("确认购买"),EMountPageAction::Buy);
    MountRelease=MakeAction(TEXT("解散马匹"),EMountPageAction::Release);
    MountDeploy=MakeAction(TEXT("设为出战"),EMountPageAction::Deploy);
    MountCall=MakeAction(TEXT("✦  召唤坐骑 (X)"),EMountPageAction::Call);
    {
        auto* ReleaseSlot=Actions->AddChildToHorizontalBox(MountRelease);
        ReleaseSlot->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
        ReleaseSlot->SetPadding(FMargin(4/Scale,0));
    }
    for(UButton* B:{MountBuy.Get(),MountDeploy.Get(),MountCall.Get()})
    {
        auto* ActionSlot=Actions->AddChildToHorizontalBox(B);
        ActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));ActionSlot->SetPadding(FMargin(4/Scale,0));
    }

    // Centered Permanent Release Confirmation Modal Overlay
    MountReleaseModal=MakeSurface(FLinearColor(0.f,0.f,0.f,.58f),0.f,FLinearColor::Transparent,0.f);
    MountReleaseModal->SetHorizontalAlignment(HAlign_Center);
    MountReleaseModal->SetVerticalAlignment(VAlign_Center);
    auto* ModalSlot=Root->AddChildToCanvas(MountReleaseModal);
    ModalSlot->SetAnchors(FAnchors(0,0,1,1));
    ModalSlot->SetOffsets(FMargin(0));
    ModalSlot->SetZOrder(180);
    MountReleaseModal->SetVisibility(ESlateVisibility::Collapsed);

    auto* ModalWidth=WidgetTree->ConstructWidget<USizeBox>();
    ModalWidth->SetWidthOverride(440.f/Scale);
    MountReleaseModal->SetContent(ModalWidth);

    auto* ModalCard=MakeSurface(ColdSteelUI::Gray(18,246),10/Scale,FLinearColor(ColdSteelUI::Danger.R,ColdSteelUI::Danger.G,ColdSteelUI::Danger.B,.65f),1.25f/Scale);
    ModalCard->SetPadding(FMargin(20/Scale,18/Scale));
    ModalWidth->SetContent(ModalCard);

    auto* ModalStack=WidgetTree->ConstructWidget<UVerticalBox>();
    ModalCard->SetContent(ModalStack);
    MountReleaseTitle=MakeInventoryText(TEXT("确认解散马匹？"),18,ColdSteelUI::TextPrimary,false,true);
    ModalStack->AddChildToVerticalBox(MountReleaseTitle)->SetPadding(FMargin(0,0,0,10/Scale));
    MountReleaseBody=MakeInventoryText(TEXT(""),13.5f,ColdSteelUI::TextSecondary);
    MountReleaseBody->SetAutoWrapText(true);
    ModalStack->AddChildToVerticalBox(MountReleaseBody)->SetPadding(FMargin(0,0,0,16/Scale));
    auto* ModalButtons=WidgetTree->ConstructWidget<UHorizontalBox>();
    ModalStack->AddChildToVerticalBox(ModalButtons);
    auto* CancelBtn=MakeAction(TEXT("取消"),EMountPageAction::ReleaseCancel);
    auto* ConfirmBtn=MakeAction(TEXT("确认永久解散"),EMountPageAction::ReleaseConfirm);
    ModalButtons->AddChildToHorizontalBox(CancelBtn)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* ConfirmSlot=ModalButtons->AddChildToHorizontalBox(ConfirmBtn);
    ConfirmSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    ConfirmSlot->SetPadding(FMargin(10/Scale,0,0,0));

    MountLabelsRevision=-1;
    return Column;
}

void UColdSteelHUDWidget::BrowseMount(FGuid Id)
{
    if(Id.IsValid())OpenMountDetails(Id,false);
    else RefreshMountPage();
}
void UColdSteelHUDWidget::OpenMarketMountDetails(FGuid Id){OpenMountDetails(Id,true);}
void UColdSteelHUDWidget::OpenMountDetails(FGuid Id,bool FromMarket)
{
    if(!StatusModel || !Id.IsValid() || !MountDetailsDrawer)return;
    const bool WasOpen=bMountDetailsOpen && MountDrawerMotion>KINDA_SMALL_NUMBER;
    if(!WasOpen)
    {
        CloseMagicConfiguration();CloseWarehouse();HideForgingInstantly();HideSmeltingInstantly();HideWorkbenchInstantly();
        SetInventoryPage(1); // The real inventory board owns the right-hand drawer and its drag operations.
    }
    ViewedMount=Id;bMountFromMarket=FromMarket;bMountDetailsOpen=true;bMountDrawerRiding=false;bMountReturnToRoster=false;
    CancelReleaseMount();
    MountItemGeneration=-1;MountGearFor.Invalidate();
    if(const auto* OwnedHorse=StatusModel->ProfileView().MountRoster.Find(Id))
    {
        StatusModel->BeginMountBagSession(Id,OwnedHorse->DisplayName());
        if(MountBagBoard)MountBagBoard->ConfigureMountBag(this,OwnedHorse->BagRows());
    }
    else StatusModel->EndMountBagSession();
    if(InventoryPanel)InventoryPanel->SetVisibility(ESlateVisibility::Visible);
    if(!WasOpen)
    {
        MountDrawerMotion=0.f;
        MountDetailsDrawer->SetVisibility(ESlateVisibility::HitTestInvisible);
        MountDetailsDrawer->SetRenderOpacity(0.f);
    }
    MountDetailsScroll->ScrollToStart();
    InventoryLayoutSize=FVector2D::ZeroVector;RefreshMountPage();
}
void UColdSteelHUDWidget::CloseMountDetails(bool Back,bool RideWithDrawer)
{
    if(!bMountDetailsOpen && !bMountDrawerRiding && MountDrawerMotion<=0.f && !ViewedMount.IsValid())return;
    CancelReleaseMount();
    if(MountBagBoard)MountBagBoard->CancelInteraction();
    if(StatusModel)StatusModel->EndMountBagSession();
    bMountDetailsOpen=false;
    if(RideWithDrawer)
    {
        bMountReturnToRoster=false;
        if(MountDrawerMotion>KINDA_SMALL_NUMBER)
        {
            bMountDrawerRiding=true;
            if(MountDetailsDrawer)MountDetailsDrawer->SetVisibility(ESlateVisibility::HitTestInvisible);
            return;
        }
    }
    else
    {
        bMountDrawerRiding=false;
        bMountReturnToRoster=Back;
        if(MountDrawerMotion>KINDA_SMALL_NUMBER)
        {
            if(MountDetailsDrawer)MountDetailsDrawer->SetVisibility(ESlateVisibility::HitTestInvisible);
            return;
        }
    }
    const bool Market=bMountFromMarket;
    if(MountGear)MountGear->ClearHorse();
    ViewedMount.Invalidate();bMountFromMarket=false;bMountReturnToRoster=false;bMountDrawerRiding=false;
    MountDrawerMotion=0.f;MountGearFor.Invalidate();
    if(MountDetailsDrawer)
    {
        MountDetailsDrawer->SetVisibility(ESlateVisibility::Collapsed);
        MountDetailsDrawer->SetRenderTranslation(FVector2D::ZeroVector);
        MountDetailsDrawer->SetRenderOpacity(0.f);
    }
    if(MountDrawerSlot)MountDrawerSlot->SetZOrder(40);
    InventoryLayoutSize=FVector2D::ZeroVector;
    if(Back && !Market && bInventoryOpen)SetInventoryPage(6);
}
void UColdSteelHUDWidget::TickMountDrawer(float Delta)
{
    if(!MountDetailsDrawer || !InventoryPanel)return;
    if(!bMountDetailsOpen && !bMountDrawerRiding && MountDrawerMotion<=0.f)return;
    const float Scale=ColdSteelUI::PixelScale(this);
    if(bMountDrawerRiding)
    {
        const float DrawerX=InventoryPanel->GetRenderTransform().Translation.X;
        MountDetailsDrawer->SetRenderTranslation(FVector2D(DrawerX+(1.f-ColdSteelUI::EaseSmooth(MountDrawerMotion))*InventoryWidth/Scale,0.f));
        MountDetailsDrawer->SetRenderOpacity(ColdSteelUI::EaseSmooth(DrawerProgress));
        if(MountDrawerSlot)MountDrawerSlot->SetZOrder(40);
        if(DrawerProgress<=KINDA_SMALL_NUMBER)
        {
            CancelReleaseMount();
            if(MountBagBoard)MountBagBoard->CancelInteraction();
            if(StatusModel)StatusModel->EndMountBagSession();
            if(MountGear)MountGear->ClearHorse();
            bMountDrawerRiding=false;bMountDetailsOpen=false;bMountFromMarket=false;bMountReturnToRoster=false;
            MountDrawerMotion=0.f;ViewedMount.Invalidate();MountGearFor.Invalidate();
            MountDetailsDrawer->SetVisibility(ESlateVisibility::Collapsed);
            MountDetailsDrawer->SetRenderTranslation(FVector2D::ZeroVector);
            MountDetailsDrawer->SetRenderOpacity(0.f);
            InventoryLayoutSize=FVector2D::ZeroVector;
        }
        return;
    }
    const float Target=bMountDetailsOpen && DrawerProgress>1.f-KINDA_SMALL_NUMBER?1.f:0.f;
    MountDrawerMotion=FMath::FInterpConstantTo(MountDrawerMotion,Target,Delta,4.f);
    const float Ease=ColdSteelUI::EaseSmooth(MountDrawerMotion);
    const float DrawerX=InventoryPanel->GetRenderTransform().Translation.X;
    MountDetailsDrawer->SetRenderTranslation(FVector2D((1.f-Ease)*InventoryWidth/Scale+DrawerX,0.f));
    MountDetailsDrawer->SetRenderOpacity(Ease);
    const bool Ready=bMountDetailsOpen && MountDrawerMotion>1.f-KINDA_SMALL_NUMBER;
    if(MountDrawerSlot)MountDrawerSlot->SetZOrder(Ready?42:40);
    if(MountDrawerMotion<=KINDA_SMALL_NUMBER)
    {
        const bool Market=bMountFromMarket;
        const bool ReturnRoster=bMountReturnToRoster;
        CancelReleaseMount();
        if(MountBagBoard)MountBagBoard->CancelInteraction();
        if(StatusModel)StatusModel->EndMountBagSession();
        if(MountGear)MountGear->ClearHorse();
        ViewedMount.Invalidate();bMountFromMarket=false;bMountReturnToRoster=false;
        MountDrawerMotion=0.f;MountGearFor.Invalidate();
        MountDetailsDrawer->SetVisibility(ESlateVisibility::Collapsed);
        MountDetailsDrawer->SetRenderTranslation(FVector2D::ZeroVector);
        MountDetailsDrawer->SetRenderOpacity(0.f);
        InventoryLayoutSize=FVector2D::ZeroVector;
        if(ReturnRoster && !Market && bInventoryOpen)SetInventoryPage(6);
        else if(ReturnRoster && Market && bShopOpen && bInventoryOpen)TickShop(0.f);
    }
    else
    {
        MountDetailsDrawer->SetVisibility(Ready?ESlateVisibility::Visible:ESlateVisibility::HitTestInvisible);
    }
}
void UColdSteelHUDWidget::BuyViewedMount()
{
    auto* Shop=GetGameInstance()->GetSubsystem<UColdSteelShopModel>();
    if(bShopOpen && bMountFromMarket && ViewedMount.IsValid() && Shop && Shop->IsStableShop() && !Shop->IsTradePending())
    {
        if(!Shop->BuyHorse(ViewedMount) && StatusModel)StatusModel->PostNotice(TEXT("马市"),Shop->ResultMessage());
    }
}
bool UColdSteelHUDWidget::IsMountReleaseModalOpen() const
{
    return MountReleaseModal && MountReleaseModal->GetVisibility()==ESlateVisibility::Visible;
}
void UColdSteelHUDWidget::RequestReleaseMount()
{
    if(!StatusModel || !ViewedMount.IsValid() || !MountReleaseModal)return;
    const auto* Horse=StatusModel->ProfileView().MountRoster.Find(ViewedMount);
    if(!Horse)return;
    auto* Pawn=GetOwningPlayerPawn();
    if(const auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr)
    {
        if(Ride->Active() && (!Ride->GetMount() || Ride->GetMount()->Identity()==ViewedMount))
        {
            StatusModel->PostNotice(TEXT("马匹"),TEXT("请先下马后再解散马匹"));
            return;
        }
    }
    PendingReleaseMount=ViewedMount;
    const int32 BagItems=StatusModel->CountMountBagItems(ViewedMount);
    const int32 TackItems=Horse->Equipment.Num();
    SetTextIfChanged(MountReleaseTitle,FString::Printf(TEXT("永久解散「%s」？"),*Horse->DisplayName()));
    if(BagItems>0 || TackItems>0)
    {
        TArray<FString> CarriedList;
        if(BagItems>0)CarriedList.Add(FString::Printf(TEXT("马匹背包 %d 件物品"),BagItems));
        if(TackItems>0)CarriedList.Add(FString::Printf(TEXT("已装配 %d 件马具"),TackItems));
        SetTextIfChanged(MountReleaseBody,FString::Printf(
            TEXT("检测到该马匹当前携带：%s。\n\n确认解散后，所有物品与马具将按「随身背包 → 主仓库 → 玩家所在地面」顺序自动转移，马匹将被永久移除（不返还灵魂）。"),
            *FString::Join(CarriedList,TEXT("、"))));
    }
    else
    {
        SetTextIfChanged(MountReleaseBody,FString::Printf(
            TEXT("确认永久解散「%s」？\n该马匹将从名册中永久移除且无法恢复（不返还灵魂）。"),
            *Horse->DisplayName()));
    }
    MountReleaseModal->SetVisibility(ESlateVisibility::Visible);
}
void UColdSteelHUDWidget::CancelReleaseMount()
{
    PendingReleaseMount.Invalidate();
    if(MountReleaseModal)MountReleaseModal->SetVisibility(ESlateVisibility::Collapsed);
}
void UColdSteelHUDWidget::ConfirmReleaseMount()
{
    const FGuid TargetId=PendingReleaseMount;
    CancelReleaseMount();
    auto* Pawn=GetOwningPlayerPawn();
    if(!StatusModel || !Pawn || !TargetId.IsValid())return;
    if(Pawn->GetNetMode()==NM_Standalone)
    {
        FString Reason;
        const bool Ok=StatusModel->ReleaseMount(TargetId,Reason);
        StatusModel->PostNotice(TEXT("马匹"),Reason);
        if(Ok)CloseMountDetails(true);
    }
    else if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())
    {
        FColdSteelInventoryRequest Req;
        Req.Action=EColdSteelInventoryAction::MountRelease;
        Req.MountId=TargetId;
        if(!PS->RequestInventoryAction(Req))
            StatusModel->PostNotice(TEXT("马匹"),TEXT("背包正在同步，请稍候再试"));
    }
}
bool UColdSteelHUDWidget::HandleMountDetailDrop(UColdSteelItemDrag* Drag,FVector2D Position)
{
    if(!ViewedMount.IsValid() || !MountDetailsDrawer || !MountDetailsDrawer->GetCachedGeometry().IsUnderLocation(Position))return false;
    if(MountGear && MountGear->HandleItemDrop(Drag,Position))return true;
    if(MountBagBoard && MountBagBoard->IsVisible() && MountBagBoard->GetCachedGeometry().IsUnderLocation(Position))return false;
    return true;
}
void UColdSteelHUDWidget::ToggleMountDeployment()
{
    ToggleMountDeploymentFor(ViewedMount);
}
void UColdSteelHUDWidget::ToggleMountDeploymentFor(FGuid Id)
{
    auto* Pawn=GetOwningPlayerPawn();auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    if(Ride && StatusModel && Id.IsValid() && StatusModel->ProfileView().MountRoster.Find(Id))
        Ride->ServerSelectMount(StatusModel->ProfileView().MountRoster.Deployed==Id?FGuid():Id);
}
void UColdSteelHUDWidget::CallJournalMount()
{
    auto* Pawn=GetOwningPlayerPawn();auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    if(!Ride||!StatusModel||StatusModel->ProfileView().MountRoster.Deployed!=ViewedMount)return;
    SetInventoryOpen(false);Ride->ToggleOwnedHorse();
}
void UColdSteelHUDWidget::CallDeployedMount()
{
    auto* Pawn=GetOwningPlayerPawn();auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    if(!Ride||!StatusModel||!StatusModel->ProfileView().MountRoster.Deployed.IsValid())return;
    SetInventoryOpen(false);Ride->ToggleOwnedHorse();
}
void UColdSteelHUDWidget::GiveJournalPotion(int32 Tier)
{
    auto* Pawn=GetOwningPlayerPawn();if(!StatusModel||!Pawn||Tier<0||Tier>=UE_ARRAY_COUNT(Potions))return;
    const auto* Stack=StatusModel->Items().FindByPredicate([Tier](const FColdSteelItem& I){
        return Carried(I)&&I.Count>0&&I.Cooldown<=0.f&&I.Definition==Potions[Tier].Id;});
    if(!Stack){StatusModel->PostNotice(TEXT("马匹"),TEXT("没有可用的该等级生命药水"));return;}
    const FString ItemId=Stack->InstanceId;
    if(Pawn->GetNetMode()==NM_Standalone)
    {
        StatusModel->SyncRuntime();FString Reason;
        StatusModel->GiveMountPotion(ViewedMount,ItemId,Reason);
        StatusModel->PostNotice(TEXT("马匹"),Reason);
    }
    else if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())
    {
        FColdSteelInventoryRequest Request;
        Request.Action=EColdSteelInventoryAction::MountPotion;Request.MountId=ViewedMount;Request.Item=ItemId;
        PS->RequestInventoryAction(Request);
    }
}
void UColdSteelHUDWidget::RefreshMountPage()
{
    if(!StatusModel||!MountList)return;
    const auto& P=StatusModel->ProfileView();const auto& Book=P.MountRoster;
    if(!bMountDetailsOpen)
    {
        if(!bMountTabActive)return;
        if(!MountCards.IsValid())
        {
            SAssignNew(MountCards,SColdSteelHorseMarket).Owned(true)
                .OnSelect(FSimpleDelegate::CreateWeakLambda(this,[this]{PlayButtonClick();}))
                .OnDetails(SColdSteelHorseMarket::FOpenHorse::CreateWeakLambda(this,[this](FGuid Id){PlayButtonClick();BrowseMount(Id);}))
                .OnDeploy(SColdSteelHorseMarket::FOpenHorse::CreateWeakLambda(this,[this](FGuid Id){PlayButtonClick();ToggleMountDeploymentFor(Id);}))
                .OnCall(FSimpleDelegate::CreateWeakLambda(this,[this]{PlayButtonClick();CallDeployedMount();}));
            MountList->SetContent(SNew(SDPIScaler).DPIScale_Lambda([Weak=TWeakObjectPtr<UColdSteelHUDWidget>(this)]{
                return Weak.IsValid()?1.f/FMath::Max(.1f,ColdSteelUI::PixelScale(Weak.Get())):1.f;})[MountCards.ToSharedRef()]);
            MountLabelsRevision=-1;
        }
        if(MountLabelsRevision!=Book.Revision || MountListProfile!=P.NetworkProfileId)
        {
            MountCards->SetRoster(Book);MountLabelsRevision=Book.Revision;MountListProfile=P.NetworkProfileId;
            MountPageHint->SetVisibility(Book.Horses.IsEmpty()?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
            SetTextIfChanged(MountPageHint,TEXT("可向东门马厩管理员购马，也可点按 E 让身边的马跟随。"));
        }
        return;
    }
    const auto* Owned=Book.Find(ViewedMount);
    auto* Shop=bMountFromMarket?GetGameInstance()->GetSubsystem<UColdSteelShopModel>():nullptr;
    const auto* Offer=Shop && bShopOpen && Shop->IsStableShop()?Shop->HorseOffers().FindByPredicate(
        [this](const FStableHorseOffer& Lot){return Lot.Horse.HorseId==ViewedMount;}):nullptr;
    const auto* H=Owned?Owned:Offer?&Offer->Horse:nullptr;
    if(!H){CloseMountDetails(true);return;}
    if(MountGearFor!=H->HorseId || MountGearRevision!=Book.Revision || MountGearInventoryRevision!=P.CampfireInventoryRevision || bGearWasOwned!=(Owned!=nullptr))
    {
        FString Name=H->DisplayName();
        if(Owned && Book.Horses.ContainsByPredicate([&](const auto& Other){return Other.HorseId!=H->HorseId && Other.DisplayName()==Name;}))
            Name+=TEXT(" · ")+H->HorseId.ToString(EGuidFormats::Digits).Left(8);
        MountGear->ShowHorse(StatusModel,*H,Owned!=nullptr,Name);
        const int32 HorseBagRows=H->BagRows();
        if(Owned)
        {
            StatusModel->BeginMountBagSession(H->HorseId,H->DisplayName());
            if(HorseBagRows>0)
            {
                if(MountBagBoard){MountBagBoard->ConfigureMountBag(this,HorseBagRows);MountBagBoard->SetVisibility(ESlateVisibility::Visible);}
                if(MountBagEmptyHintBox)MountBagEmptyHintBox->SetVisibility(ESlateVisibility::Collapsed);
            }
            else
            {
                if(MountBagBoard){MountBagBoard->CancelInteraction();MountBagBoard->SetVisibility(ESlateVisibility::Collapsed);}
                if(MountBagEmptyHintBox)MountBagEmptyHintBox->SetVisibility(ESlateVisibility::Visible);
                SetTextIfChanged(MountBagEmptyHintText,TEXT("马匹背包 · 0 排（0 格）\n受词条「懒惰」影响，该马匹暂无背包空间"));
            }
        }
        else
        {
            StatusModel->EndMountBagSession();
            if(MountBagBoard){MountBagBoard->CancelInteraction();MountBagBoard->SetVisibility(ESlateVisibility::Collapsed);}
            if(MountBagEmptyHintBox)MountBagEmptyHintBox->SetVisibility(ESlateVisibility::Visible);
            SetTextIfChanged(MountBagEmptyHintText,HorseBagRows>0
                ? FString::Printf(TEXT("马匹背包容量预览 · %d 排（%d 格）\n购入后即可存取物品，交互规则与随身背包一致"),HorseBagRows,HorseBagRows*18)
                : TEXT("马匹背包容量预览 · 0 排（0 格）\n受词条「懒惰」影响，该马匹暂无背包空间"));
        }
        MountGearFor=H->HorseId;MountGearRevision=Book.Revision;MountGearInventoryRevision=P.CampfireInventoryRevision;bGearWasOwned=Owned!=nullptr;
    }
    MountBuy->SetVisibility(Owned?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
    if(MountRelease)MountRelease->SetVisibility(Owned?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    MountDeploy->SetVisibility(Owned?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(MountBalanceDelta)MountBalanceDelta->SetVisibility(Owned?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
    if(!Owned && Offer)
    {
        const int64 BalanceNow=StatusModel->SoulBalance();
        const int64 After=BalanceNow-Offer->Price;
        const int64 Shortfall=Offer->Price-BalanceNow;
        MountBuy->SetIsEnabled(!Shop->IsTradePending() && Shortfall<=0);
        SetTextIfChanged(Caption(MountBuy),Shop->IsTradePending()?TEXT("正在登记购买…"):Shortfall>0?
            FString::Printf(TEXT("灵魂不足 · 还差 %lld 灵魂"),Shortfall):FString::Printf(TEXT("✦  确认购买  ·  %d 灵魂"),Offer->Price));
        if(MountBalanceDelta)
        {
            SetTextIfChanged(MountBalanceDelta,Shortfall>0
                ? FString::Printf(TEXT("灵魂结余：✦ %lld   →   还差 %lld 灵魂"),BalanceNow,Shortfall)
                : FString::Printf(TEXT("灵魂结余：✦ %lld   →   购后剩余 ✦ %lld"),BalanceNow,After));
            MountBalanceDelta->SetColorAndOpacity(Shortfall>0?ColdSteelUI::Danger:ColdSteelUI::HUDGoldLight);
        }
    }
    auto* Pawn=GetOwningPlayerPawn();auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    auto* Live=Ride?Ride->GetOwnedHorse():nullptr;
    if(!IsValid(Live)||Live->Identity()!=H->HorseId||Live->IsRetreating())Live=nullptr;
    const float Health=Live?Live->GetHealth():H->Health;
    const int64 Now=Ride?Ride->HorseUtcNow():FDateTime::UtcNow().GetTicks();
    const int32 Seconds=FMath::CeilToInt32(FMath::Max(0.,FTimespan(H->RecallAfterUtc-Now).GetTotalSeconds()));
    const bool Out=Book.Deployed==H->HorseId;
    FString State=Health<=0?TEXT("已逃离 · 使用生命药水恢复"):!Live?(Out?TEXT("★ 当前出战 · 待召唤"):TEXT("马棚待命")):
        Live->Visit()==EStableHorseVisit::Arriving?TEXT("召唤中"):Live->Visit()==EStableHorseVisit::Departing?TEXT("遣散中"):
        Live->GetRider()?TEXT("★ 骑乘中"):Live->NeedsRecall()?TEXT("已远离或受阻"):Live->GetLeader()?TEXT("★ 跟随中"):TEXT("★ 场内待命");
    if(!Owned && Offer)State=FString::Printf(TEXT("东门马市 · 在售 %d 灵魂"),Offer->Price);
    if(Seconds>0)State+=FString::Printf(TEXT(" · 冷却 %d 秒"),Seconds);
    MountGear->UpdateCondition(*H,State,Health,Live?Live->GetStamina():H->Stamina);
    SetTextIfChanged(Caption(MountDeploy),Out?TEXT("取消出战"):TEXT("设为出战"));MountDeploy->SetIsEnabled(Ride&&!Ride->Active());
    MountCall->SetVisibility(Owned&&Out?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    const bool Far=Live&&!Live->GetRider()&&(Live->NeedsRecall()||Live->IsFarFrom(*Pawn));
    SetTextIfChanged(Caption(MountCall),Far?TEXT("✦  再次召唤 (X)"):Live?TEXT("遣散坐骑"):TEXT("✦  召唤坐骑 (X)"));
    MountCall->SetIsEnabled(Ride&&Health>0.f&&Seconds==0&&(!Live||Live->Visit()==EStableHorseVisit::Present));
    const bool Hurt=Owned && Health<H->MaxHealth;
    if(MountPotionPanel)MountPotionPanel->SetVisibility(Hurt?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!Hurt){for(const auto& B:MountPotions)B->SetVisibility(ESlateVisibility::Collapsed);MountItemGeneration=-1;return;}
    if(MountItemGeneration==P.Generation)return;
    MountItemGeneration=P.Generation;
    int64 Counts[UE_ARRAY_COUNT(Potions)]={};
    for(const auto& I:P.Items)if(Carried(I))for(int32 T=0;T<UE_ARRAY_COUNT(Potions);++T)if(I.Definition==Potions[T].Id)Counts[T]+=I.Count;
    bool Any=false;
    for(int32 T=0;T<MountPotions.Num();++T)
    {
        Any|=Counts[T]>0;MountPotions[T]->SetVisibility(Counts[T]?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        SetTextIfChanged(Caption(MountPotions[T]),FString::Printf(TEXT("%s  ×%lld"),Potions[T].Name,Counts[T]));
    }
    SetTextIfChanged(MountPotionHint,Any?TEXT("生命药水"):TEXT("背包暂无生命药水"));
}
