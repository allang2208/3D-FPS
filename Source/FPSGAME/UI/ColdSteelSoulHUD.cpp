#include "ColdSteelHUDWidget.h"
#include "ColdSteelSoulCounter.h"
#include "ColdSteelAcquisitionFeed.h"
#include "ColdSteelDungeonTracker.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"

void UColdSteelHUDWidget::BuildSoulHUD(UCanvasPanel* Root)
{
    SoulHUD=CreateWidget<UColdSteelSoulCounter>(GetOwningPlayer());
    SoulHUDSlot=Root->AddChildToCanvas(SoulHUD);SoulHUDSlot->SetAnchors(FAnchors(0,1));SoulHUDSlot->SetAlignment(FVector2D(0,1));SoulHUDSlot->SetZOrder(28);
    AcquisitionFeed=CreateWidget<UColdSteelAcquisitionFeed>(GetOwningPlayer());
    AcquisitionFeedSlot=Root->AddChildToCanvas(AcquisitionFeed);AcquisitionFeedSlot->SetAnchors(FAnchors(0,1));
    AcquisitionFeedSlot->SetAlignment(FVector2D(0,1));AcquisitionFeedSlot->SetZOrder(28);
}

void UColdSteelHUDWidget::BuildSoulWallet(UVerticalBox* Body)
{
    SoulWallet=CreateWidget<UColdSteelSoulCounter>(GetOwningPlayer());
    SoulWalletSize=WidgetTree->ConstructWidget<USizeBox>();SoulWalletSize->SetContent(SoulWallet);
    Body->AddChildToVerticalBox(SoulWalletSize)->SetPadding(FMargin(16/ColdSteelUI::PixelScale(this),0,16/ColdSteelUI::PixelScale(this),8/ColdSteelUI::PixelScale(this)));
    SoulWalletSize->SetHeightOverride(UColdSteelSoulCounter::PixelHeight/ColdSteelUI::PixelScale(this));
}

void UColdSteelHUDWidget::LayoutSoulHUD(float S,float Left,float Bottom,float Width)
{
    if(SoulHUDSlot)
    {
        SoulHUDSlot->SetPosition(FVector2D(Left,-Bottom)/S);
        SoulHUDSlot->SetSize(FVector2D(FMath::Min(360.f,Width),UColdSteelSoulCounter::PixelHeight)/S);
        SoulHUD->SetDisplayScale(S);
    }
    if(SoulWallet)
    {
        SoulWallet->SetDisplayScale(S);SoulWalletSize->SetHeightOverride(UColdSteelSoulCounter::PixelHeight/S);
        CastChecked<UVerticalBoxSlot>(SoulWalletSize->Slot)->SetPadding(FMargin(16/S,0,16/S,8/S));
    }
    if(AcquisitionFeedSlot)
    {
        const float ViewHeight=TopHUDViewport.Y*S;
        const float FeedBottom=Bottom+UColdSteelSoulCounter::PixelHeight+8.f;
        const float Available=FMath::Max(0.f,ViewHeight-FeedBottom-220.f);
        const float FeedHeight=FMath::Min(UColdSteelAcquisitionFeed::PreferredHeight,Available);
        AcquisitionFeedSlot->SetPosition(FVector2D(Left,-FeedBottom)/S);
        AcquisitionFeedSlot->SetSize(FVector2D(FMath::Min(360.f,Width),FeedHeight)/S);
        AcquisitionFeed->SetLayout(S,FMath::Min(360.f,Width),FeedHeight);
        if(TaskTracker)TaskTracker->SetBottomBoundaryPixels(ViewHeight-FeedBottom-FeedHeight-8.f);
    }
}

void UColdSteelHUDWidget::RefreshSoulBalance()
{
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model)return;
    const int64 Balance=Model->SoulBalance();
    if(SoulHUD)SoulHUD->SetBalance(Balance);
    if(SoulWallet)SoulWallet->SetBalance(Balance,bInventoryOpen&&SoulWalletSize->GetVisibility()!=ESlateVisibility::Collapsed);
}
