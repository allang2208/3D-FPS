#include "ColdSteelHUDWidget.h"
#include "ColdSteelMountButton.h"
#include "ColdSteelMountGearPanel.h"
#include "ColdSteelShopModel.h"
#include "ColdSteelInventoryWidget.h"
#include "SColdSteelHorseMarket.h"
#include "Components/NativeWidgetHost.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
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
    const FText New=FText::FromString(Value);if(!Widget->GetText().EqualTo(New))Widget->SetText(New);
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
    }
}
UWidget* UColdSteelHUDWidget::BuildMountPage()
{
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();
    MountPageHint=MakeInventoryText(TEXT(""),15,ColdSteelUI::TextSecondary);MountPageHint->SetAutoWrapText(true);
    Column->AddChildToVerticalBox(MountPageHint);
    MountList=WidgetTree->ConstructWidget<UNativeWidgetHost>();
    Column->AddChildToVerticalBox(MountList)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    auto* Root=CastChecked<UCanvasPanel>(WidgetTree->RootWidget);
    MountDetailsDrawer=MakeSurface(ColdSteelUI::GlassFallback,8,ColdSteelUI::Border);
    const float Scale=ColdSteelUI::PixelScale(this);
    MountDetailsDrawer->SetPadding(FMargin(1.f/Scale));
    MountDrawerSlot=Root->AddChildToCanvas(MountDetailsDrawer);MountDrawerSlot->SetAutoSize(false);MountDrawerSlot->SetZOrder(44);
    MountDetailsDrawer->SetVisibility(ESlateVisibility::Collapsed);
    auto* Shell=WidgetTree->ConstructWidget<UVerticalBox>();MountDetailsDrawer->SetContent(Shell);
    auto MakeAction=[&](const TCHAR* Title,EMountPageAction Action,int32 Tier=0)
    {
        auto* B=WidgetTree->ConstructWidget<UColdSteelMountButton>();B->Bind(this,Action,{},Tier);
        auto Style=ColdSteelUI::ButtonStyle(Scale);
        if(Action==EMountPageAction::Buy || Action==EMountPageAction::Deploy)
        {
            Style.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(43),5/Scale,ColdSteelUI::HUDGoldDim,1/Scale));
            Style.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(54),5/Scale,ColdSteelUI::HUDGold,1/Scale));
        }
        B->SetStyle(Style);B->SetContent(MakeInventoryText(Title,14,ColdSteelUI::TextPrimary,false,true));
        return B;
    };
    auto* Header=MakeSurface(ColdSteelUI::HeaderTint,6,ColdSteelUI::Border);
    Header->SetPadding(FMargin(14/Scale,8/Scale));
    auto* HeaderRow=WidgetTree->ConstructWidget<UHorizontalBox>();Header->SetContent(HeaderRow);
    auto* TitleSlot=HeaderRow->AddChildToHorizontalBox(MakeInventoryText(TEXT("马匹详情"),17,ColdSteelUI::TextPrimary,false,true));
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    HeaderRow->AddChildToHorizontalBox(MakeAction(TEXT("返回名册"),EMountPageAction::Back));
    Shell->AddChildToVerticalBox(Header);
    MountDetailsScroll=WidgetTree->ConstructWidget<UScrollBox>();MountDetailsScroll->SetAllowOverscroll(false);
    auto ScrollStyle=MountDetailsScroll->GetWidgetStyle();
    ScrollStyle.SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource());
    MountDetailsScroll->SetWidgetStyle(ScrollStyle);
    MountDetailsScroll->SetScrollBarVisibility(ESlateVisibility::Collapsed);
    auto* ScrollSlot=Shell->AddChildToVerticalBox(MountDetailsScroll);ScrollSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    ScrollSlot->SetPadding(FMargin(10/Scale,8/Scale));
    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();MountDetailsScroll->AddChild(Body);
    MountGear=CreateWidget<UColdSteelMountGearPanel>(GetOwningPlayer());Body->AddChildToVerticalBox(MountGear);
    MountPotionHint=MakeInventoryText(TEXT(""),13,ColdSteelUI::TextSecondary);
    Body->AddChildToVerticalBox(MountPotionHint)->SetPadding(FMargin(4/Scale,8/Scale,0,3/Scale));
    auto* PotionRow=WidgetTree->ConstructWidget<UWrapBox>();PotionRow->SetInnerSlotPadding(FVector2D(5/Scale,4/Scale));
    Body->AddChildToVerticalBox(PotionRow);
    MountPotions.Reset();
    for(int32 I=0;I<UE_ARRAY_COUNT(Potions);++I)
    {
        auto* B=MakeAction(Potions[I].Name,EMountPageAction::Potion,I);MountPotions.Add(B);PotionRow->AddChildToWrapBox(B);
    }
    auto* Footer=MakeSurface(ColdSteelUI::Content,6,ColdSteelUI::Border);
    Footer->SetPadding(FMargin(12/Scale,8/Scale));Shell->AddChildToVerticalBox(Footer);
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();Footer->SetContent(Actions);
    MountBuy=MakeAction(TEXT("确认购买"),EMountPageAction::Buy);
    MountDeploy=MakeAction(TEXT("设为出战"),EMountPageAction::Deploy);
    MountCall=MakeAction(TEXT("召唤"),EMountPageAction::Call);
    for(UButton* B:{MountBuy.Get(),MountDeploy.Get(),MountCall.Get()})
    {
        auto* ActionSlot=Actions->AddChildToHorizontalBox(B);
        ActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));ActionSlot->SetPadding(FMargin(3/Scale,0));
    }
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
    SetInventoryPage(1); // The real inventory board owns the right-hand drawer and its drag operations.
    ViewedMount=Id;bMountFromMarket=FromMarket;MountItemGeneration=-1;MountGearFor.Invalidate();
    InventoryPanel->SetVisibility(ESlateVisibility::Visible);
    MountDetailsDrawer->SetVisibility(ESlateVisibility::Visible);
    MountDetailsScroll->ScrollToStart();
    InventoryLayoutSize=FVector2D::ZeroVector;RefreshMountPage();
}
void UColdSteelHUDWidget::CloseMountDetails(bool Back)
{
    if(!ViewedMount.IsValid())return;
    const bool Market=bMountFromMarket;
    if(MountGear)MountGear->ClearHorse();
    ViewedMount.Invalidate();bMountFromMarket=false;MountGearFor.Invalidate();
    MountDetailsDrawer->SetVisibility(ESlateVisibility::Collapsed);
    InventoryLayoutSize=FVector2D::ZeroVector;
    if(Back && !Market && bInventoryOpen)SetInventoryPage(6);
}
void UColdSteelHUDWidget::BuyViewedMount()
{
    auto* Shop=GetGameInstance()->GetSubsystem<UColdSteelShopModel>();
    if(bShopOpen && bMountFromMarket && ViewedMount.IsValid() && Shop && Shop->IsStableShop() && !Shop->IsTradePending())
    {
        if(!Shop->BuyHorse(ViewedMount) && StatusModel)StatusModel->PostNotice(TEXT("马市"),Shop->ResultMessage());
    }
}
bool UColdSteelHUDWidget::HandleMountDetailDrop(UColdSteelItemDrag* Drag,FVector2D Position)
{
    if(!ViewedMount.IsValid() || !MountDetailsDrawer || !MountDetailsDrawer->GetCachedGeometry().IsUnderLocation(Position))return false;
    if(MountGear)MountGear->HandleItemDrop(Drag,Position);
    return true;
}
void UColdSteelHUDWidget::ToggleMountDeployment()
{
    auto* Pawn=GetOwningPlayerPawn();auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    if(Ride&&StatusModel&&StatusModel->ProfileView().MountRoster.Find(ViewedMount))
        Ride->ServerSelectMount(StatusModel->ProfileView().MountRoster.Deployed==ViewedMount?FGuid():ViewedMount);
}
void UColdSteelHUDWidget::CallJournalMount()
{
    auto* Pawn=GetOwningPlayerPawn();auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    if(!Ride||!StatusModel||StatusModel->ProfileView().MountRoster.Deployed!=ViewedMount)return;
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
    if(!ViewedMount.IsValid())
    {
        if(!bMountTabActive)return;
        if(!MountCards.IsValid())
        {
            SAssignNew(MountCards,SColdSteelHorseMarket).Owned(true)
                .OnSelect(FSimpleDelegate::CreateWeakLambda(this,[this]{PlayButtonClick();}))
                .OnDetails(SColdSteelHorseMarket::FOpenHorse::CreateWeakLambda(this,[this](FGuid Id){PlayButtonClick();BrowseMount(Id);}));
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
        MountGearFor=H->HorseId;MountGearRevision=Book.Revision;MountGearInventoryRevision=P.CampfireInventoryRevision;bGearWasOwned=Owned!=nullptr;
    }
    MountBuy->SetVisibility(Owned?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
    MountDeploy->SetVisibility(Owned?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!Owned)
    {
        const int64 Shortfall=Offer->Price-StatusModel->SoulBalance();
        MountBuy->SetIsEnabled(!Shop->IsTradePending() && Shortfall<=0);
        SetTextIfChanged(Caption(MountBuy),Shop->IsTradePending()?TEXT("正在登记购买"):Shortfall>0?
            FString::Printf(TEXT("还差 %lld 灵魂"),Shortfall):FString::Printf(TEXT("确认购买  ·  %d 灵魂"),Offer->Price));
    }
    auto* Pawn=GetOwningPlayerPawn();auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    auto* Live=Ride?Ride->GetOwnedHorse():nullptr;
    if(!IsValid(Live)||Live->Identity()!=H->HorseId||Live->IsRetreating())Live=nullptr;
    const float Health=Live?Live->GetHealth():H->Health;
    const int64 Now=Ride?Ride->HorseUtcNow():FDateTime::UtcNow().GetTicks();
    const int32 Seconds=FMath::CeilToInt32(FMath::Max(0.,FTimespan(H->RecallAfterUtc-Now).GetTotalSeconds()));
    const bool Out=Book.Deployed==H->HorseId;
    FString State=Health<=0?TEXT("已逃离 · 使用生命药水恢复生命"):!Live?TEXT("待召唤"):
        Live->Visit()==EStableHorseVisit::Arriving?TEXT("召唤中"):Live->Visit()==EStableHorseVisit::Departing?TEXT("遣散中"):
        Live->GetRider()?TEXT("骑乘中"):Live->NeedsRecall()?TEXT("已远离或受阻"):Live->GetLeader()?TEXT("跟随中"):TEXT("场内待命");
    if(!Owned)State=FString::Printf(TEXT("在售 · %d 灵魂"),Offer->Price);
    if(Seconds>0)State+=FString::Printf(TEXT("    召唤冷却 %d 秒"),Seconds);
    MountGear->UpdateCondition(*H,State,Health,Live?Live->GetStamina():H->Stamina);
    SetTextIfChanged(Caption(MountDeploy),Out?TEXT("取消出战"):TEXT("设为出战"));MountDeploy->SetIsEnabled(Ride&&!Ride->Active());
    MountCall->SetVisibility(Owned&&Out?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    const bool Far=Live&&!Live->GetRider()&&(Live->NeedsRecall()||Live->IsFarFrom(*Pawn));
    SetTextIfChanged(Caption(MountCall),Far?TEXT("再次召唤"):Live?TEXT("遣散"):TEXT("召唤"));
    MountCall->SetIsEnabled(Ride&&Health>0.f&&Seconds==0&&(!Live||Live->Visit()==EStableHorseVisit::Present));
    const bool Hurt=Owned && Health<H->MaxHealth;
    MountPotionHint->SetVisibility(Hurt?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!Hurt){for(const auto& B:MountPotions)B->SetVisibility(ESlateVisibility::Collapsed);MountItemGeneration=-1;return;}
    if(MountItemGeneration==P.Generation)return;
    MountItemGeneration=P.Generation;
    int64 Counts[UE_ARRAY_COUNT(Potions)]={};
    for(const auto& I:P.Items)if(Carried(I))for(int32 T=0;T<UE_ARRAY_COUNT(Potions);++T)if(I.Definition==Potions[T].Id)Counts[T]+=I.Count;
    bool Any=false;
    for(int32 T=0;T<MountPotions.Num();++T)
    {
        Any|=Counts[T]>0;MountPotions[T]->SetVisibility(Counts[T]?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        SetTextIfChanged(Caption(MountPotions[T]),FString::Printf(TEXT("使用%s  ×%lld"),Potions[T].Name,Counts[T]));
    }
    SetTextIfChanged(MountPotionHint,Any?TEXT("选择一瓶生命药水给马匹使用"):TEXT("随身背包中没有生命药水"));
}
