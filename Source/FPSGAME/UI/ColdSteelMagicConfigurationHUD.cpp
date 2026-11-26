#include "ColdSteelHUDWidget.h"
#include "ColdSteelMagicWheel.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"

void UColdSteelHUDWidget::ToggleMagicConfiguration()
{
    PlayButtonClick();
    if(bMagicConfigurationOpen){CloseMagicConfiguration();return;}
    if(!bInventoryOpen||!bSkillsTabActive)return;
    CancelQuickDrag();HideItemTooltip(true);
    CloseWarehouse();CloseShop();HideForgingInstantly();HideSmeltingInstantly();HideWorkbenchInstantly();
    if(!MagicConfigurationPanel)
    {
        const float Scale=ColdSteelUI::PixelScale(this);
        MagicConfigurationPanel=MakeSurface(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1.f/Scale);
        MagicConfigurationPanel->SetPadding(FMargin(1.f/Scale));
        auto* Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();
        Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetOverrideAutoRadiusCalculation(true);Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
        Blur->SetCornerRadius(FVector4(10,10,10,10));Blur->SetApplyAlphaToBlur(true);
        Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
        MagicConfigurationPanel->SetContent(Blur);
        auto* Glass=MakeSurface(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale,FLinearColor::Transparent,0);
        Glass->SetPadding(FMargin(0));Blur->SetContent(Glass);
        auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();Glass->SetContent(Body);
        auto* Header=MakeSurface(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale,FLinearColor::Transparent,0);
        MagicConfigurationHeader=Header;
        Header->SetPadding(FMargin(18.f/Scale,12.f/Scale));
        auto* HeaderHeight=WidgetTree->ConstructWidget<USizeBox>();HeaderHeight->SetHeightOverride(36.f/Scale);Header->SetContent(HeaderHeight);
        MagicConfigurationHeaderSize=HeaderHeight;
        auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderHeight->SetContent(Row);
        auto* TitleSlot=Row->AddChildToHorizontalBox(MakeInventoryText(TEXT("快捷施法配置"),20,ColdSteelUI::TextPrimary,false,true));
        TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
        auto* Close=WidgetTree->ConstructWidget<UButton>();Close->SetStyle(ColdSteelUI::ButtonStyle(Scale));
        MagicConfigurationClose=Close;
        Close->SetContent(MakeInventoryText(TEXT("收回"),14,ColdSteelUI::TextPrimary));
        Cast<UButtonSlot>(Close->GetContent()->Slot)->SetPadding(FMargin(12.f/Scale,8.f/Scale));
        Close->OnClicked.AddDynamic(this,&ThisClass::ToggleMagicConfiguration);
        Row->AddChildToHorizontalBox(Close)->SetVerticalAlignment(VAlign_Center);
        Body->AddChildToVerticalBox(Header)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
        MagicConfiguration=CreateWidget<UColdSteelMagicWheel>(GetOwningPlayer());MagicConfiguration->Configure(this);
        Body->AddChildToVerticalBox(MagicConfiguration)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        MagicConfigurationSlot=CastChecked<UCanvasPanel>(WidgetTree->RootWidget)->AddChildToCanvas(MagicConfigurationPanel);
        MagicConfigurationSlot->SetAnchors(InventoryPanelSlot->GetAnchors());MagicConfigurationSlot->SetAlignment(InventoryPanelSlot->GetAlignment());
        MagicConfigurationSlot->SetAutoSize(false);MagicConfigurationSlot->SetZOrder(40);
        auto Bounds=InventoryPanelSlot->GetOffsets();Bounds.Left-=InventoryWidth/Scale;MagicConfigurationSlot->SetOffsets(Bounds);
        UpdateMagicConfigurationLayout(Scale);
    }
    bMagicConfigurationOpen=true;bMagicRiding=false;InventoryLayoutSize=FVector2D::ZeroVector;
    MagicConfigurationPanel->SetVisibility(ESlateVisibility::HitTestInvisible);
    MagicConfigurationPanel->SetRenderOpacity(0.f);
}
void UColdSteelHUDWidget::UpdateMagicConfigurationLayout(float Scale)
{
    if(!MagicConfigurationPanel)return;
    MagicConfigurationPanel->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1.f/Scale));
    MagicConfigurationPanel->SetPadding(FMargin(1.f/Scale));
    if(auto* Blur=Cast<UBackgroundBlur>(MagicConfigurationPanel->GetContent()))
        if(auto* Glass=Cast<UBorder>(Blur->GetContent()))
            Glass->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale,FLinearColor::Transparent,0));
    MagicConfigurationHeader->SetPadding(FMargin(18.f/Scale,12.f/Scale));
    MagicConfigurationHeader->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale,FLinearColor::Transparent,0));
    MagicConfigurationHeaderSize->SetHeightOverride(36.f/Scale);
    MagicConfigurationClose->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    Cast<UButtonSlot>(MagicConfigurationClose->GetContent()->Slot)->SetPadding(FMargin(12.f/Scale,8.f/Scale));
}
void UColdSteelHUDWidget::CloseMagicConfiguration(bool RideWithDrawer)
{
    if(!bMagicConfigurationOpen&&!bMagicRiding&&MagicConfigurationMotion<=0.f)return;
    CancelQuickDrag();bMagicConfigurationOpen=false;
    if(RideWithDrawer&&MagicConfigurationMotion>0.f)bMagicRiding=true;
    if(MagicConfiguration)MagicConfiguration->ClearHover();
    if(MagicConfigurationPanel)MagicConfigurationPanel->SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UColdSteelHUDWidget::TickMagicConfiguration(float Delta)
{
    if(!MagicConfigurationPanel)return;
    const float Scale=ColdSteelUI::PixelScale(this);
    if(bMagicRiding)
    {
        const float DrawerX=InventoryPanel->GetRenderTransform().Translation.X;
        MagicConfigurationPanel->SetRenderTranslation(FVector2D(DrawerX+(1.f-ColdSteelUI::EaseSmooth(MagicConfigurationMotion))*InventoryWidth/Scale,0));
        MagicConfigurationPanel->SetRenderOpacity(ColdSteelUI::EaseSmooth(DrawerProgress));
        MagicConfigurationSlot->SetZOrder(40);
        if(DrawerProgress<=KINDA_SMALL_NUMBER)
        {bMagicRiding=false;MagicConfigurationMotion=0.f;MagicConfigurationPanel->SetVisibility(ESlateVisibility::Collapsed);}
        return;
    }
    const float Target=bMagicConfigurationOpen&&DrawerProgress>1.f-KINDA_SMALL_NUMBER?1.f:0.f;
    MagicConfigurationMotion=FMath::FInterpConstantTo(MagicConfigurationMotion,Target,Delta,4.f);
    const float Ease=ColdSteelUI::EaseSmooth(MagicConfigurationMotion);
    const float DrawerX=InventoryPanel->GetRenderTransform().Translation.X;
    MagicConfigurationPanel->SetRenderTranslation(FVector2D((1.f-Ease)*InventoryWidth/Scale+DrawerX,0));
    MagicConfigurationPanel->SetRenderOpacity(Ease);
    const bool Ready=bMagicConfigurationOpen&&MagicConfigurationMotion>1.f-KINDA_SMALL_NUMBER;
    MagicConfigurationSlot->SetZOrder(Ready?42:40);
    MagicConfigurationPanel->SetVisibility(MagicConfigurationMotion<=0?ESlateVisibility::Collapsed:Ready?ESlateVisibility::Visible:ESlateVisibility::HitTestInvisible);
}
bool UColdSteelHUDWidget::DropMagicDrag(UColdSteelQuickDrag* Drag,int32 Target)
{
    if(!Drag||QuickDrag.Get()!=Drag)return false;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if((bMagicConfigurationOpen||IsSkillTreeOpen())&&Model&&Drag->IsCurrent()&&Drag->MagicBindings==Model->MagicBindings())
    {
        const FName Skill=Drag->SourceSlot>=0?Model->QuickBinding(Drag->SourceSlot).Skill:Drag->Skill;
        Model->BindMagic(Target,Skill);
    }
    // A drop on an empty centre or an incompatible skill cancels without clearing the source hotkey.
    Drag->ReleaseVisual();EndQuickDrag();return true;
}
