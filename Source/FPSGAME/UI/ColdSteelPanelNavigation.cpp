#include "ColdSteelHUDWidget.h"
#include "ColdSteelAmmoReadout.h"
#include "ColdSteelUIStyle.h"
#include "SColdSteelCooldownMask.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScaleBox.h"
#include "Components/TextBlock.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "GameFramework/PlayerController.h"

namespace
{
    // CSS transition timing-function: ease = cubic-bezier(.25, .1, .25, 1).
    float NavigationEase(float X)
    {
        if(X<=0.f||X>=1.f)return FMath::Clamp(X,0.f,1.f);
        float Low=0.f,High=1.f,U=0.f;
        for(int32 Step=0;Step<12;++Step)
        {
            U=(Low+High)*.5f;
            const float CurveX=3*(1-U)*(1-U)*U*.25f+3*(1-U)*U*U*.25f+U*U*U;
            if(CurveX<X)Low=U;else High=U;
        }
        return 3*(1-U)*(1-U)*U*.1f+3*(1-U)*U*U+U*U*U;
    }
}

void UColdSteelHUDWidget::BuildPanelNavigation(UCanvasPanel* Root)
{
    PanelNavigation=WidgetTree->ConstructWidget<UVerticalBox>();
    PanelNavigation->SetVisibility(ESlateVisibility::HitTestInvisible);
    PanelNavigationSlot=Root->AddChildToCanvas(PanelNavigation);
    PanelNavigationSlot->SetAnchors(FAnchors(1,0));
    PanelNavigationSlot->SetAlignment(FVector2D(1,0));
    PanelNavigationSlot->SetAutoSize(true);
    PanelNavigationSlot->SetZOrder(45);
    const TCHAR* Names[]={TEXT("人物状态"),TEXT("背包"),TEXT("技能"),TEXT("图鉴")};
    const TCHAR* Keys[]={TEXT("Caps"),TEXT("Tab"),TEXT("P"),TEXT("N")};
    const TCHAR* Files[]={TEXT("Navigation/status_subject.png"),TEXT("Navigation/backpack_subject.png"),TEXT("Navigation/skills_subject.png"),TEXT("Navigation/codex_subject.png")};
    for(int32 Index=0;Index<4;++Index)
    {
        auto* Size=WidgetTree->ConstructWidget<USizeBox>();PanelNavigationSizes.Add(Size);
        PanelNavigation->AddChildToVerticalBox(Size);
        auto* Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();Size->SetContent(Canvas);
        auto* Button=WidgetTree->ConstructWidget<UButton>();PanelNavigationButtons.Add(Button);
        auto* ButtonCanvasSlot=Canvas->AddChildToCanvas(Button);
        ButtonCanvasSlot->SetAnchors(FAnchors(0,0,1,1));ButtonCanvasSlot->SetOffsets(FMargin(0));
        auto* Layers=WidgetTree->ConstructWidget<UOverlay>();Button->SetContent(Layers);
        auto* ContentSlot=Cast<UButtonSlot>(Layers->Slot);
        ContentSlot->SetHorizontalAlignment(HAlign_Fill);ContentSlot->SetVerticalAlignment(VAlign_Fill);ContentSlot->SetPadding(FMargin(0));
        auto Fill=[Layers](UWidget* Child)
        {
            Child->SetVisibility(ESlateVisibility::HitTestInvisible);
            auto* Slot=Layers->AddChildToOverlay(Child);
            Slot->SetHorizontalAlignment(HAlign_Fill);Slot->SetVerticalAlignment(VAlign_Fill);
        };
        auto* Icon=WidgetTree->ConstructWidget<UImage>();
        auto* Texture=LoadUiTexture(Files[Index]);Icon->SetBrushFromTexture(Texture,true);
        auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);
        Fit->SetContent(Icon);Fill(Fit);Fit->SetRenderTransformPivot(FVector2D(.5f,.5f));
        PanelNavigationSubjects.Add(Fit);
        auto* Fallback=MakeReferenceText(Names[Index],12,ColdSteelUI::TextPrimary);
        Fallback->SetJustification(ETextJustify::Center);Fallback->SetAutoWrapText(true);
        auto* FallbackSlot=Layers->AddChildToOverlay(Fallback);
        FallbackSlot->SetHorizontalAlignment(HAlign_Fill);FallbackSlot->SetVerticalAlignment(VAlign_Center);
        Fallback->SetVisibility(Texture?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
        PanelNavigationFallbacks.Add(Fallback);
        auto* Marker=WidgetTree->ConstructWidget<UImage>();Marker->SetVisibility(ESlateVisibility::Hidden);
        auto* MarkerSlot=Layers->AddChildToOverlay(Marker);
        MarkerSlot->SetHorizontalAlignment(HAlign_Left);MarkerSlot->SetVerticalAlignment(VAlign_Center);
        PanelNavigationMarkers.Add(Marker);
        auto* Key=MakeReferenceText(Keys[Index],16,ColdSteelUI::NavigationKey,true,true);
        Key->SetVisibility(ESlateVisibility::HitTestInvisible);
        Key->SetShadowColorAndOpacity(FLinearColor(0,0,0,.95f));
        auto* KeySlot=Layers->AddChildToOverlay(Key);
        KeySlot->SetHorizontalAlignment(HAlign_Right);KeySlot->SetVerticalAlignment(VAlign_Bottom);
        PanelNavigationKeys.Add(Key);
        auto* Name=MakeSurface(ColdSteelUI::Tooltip,6,ColdSteelUI::Border);
        Name->SetContent(MakeReferenceText(Names[Index],12,ColdSteelUI::TextPrimary));
        Name->SetVisibility(ESlateVisibility::Collapsed);
        auto* NameSlot=Canvas->AddChildToCanvas(Name);
        NameSlot->SetAnchors(FAnchors(0,.5f));NameSlot->SetAlignment(FVector2D(1,.5f));NameSlot->SetAutoSize(true);
        PanelNavigationNames.Add(Name);
    }
    PanelNavigationButtons[0]->OnClicked.AddDynamic(this,&UColdSteelHUDWidget::HandleNavigationStatus);
    PanelNavigationButtons[1]->OnClicked.AddDynamic(this,&UColdSteelHUDWidget::HandleNavigationBackpack);
    PanelNavigationButtons[2]->OnClicked.AddDynamic(this,&UColdSteelHUDWidget::HandleNavigationSkills);
    PanelNavigationButtons[3]->OnClicked.AddDynamic(this,&UColdSteelHUDWidget::HandleNavigationCodex);
    PanelNavigationStates.Init(255,4);
    PanelNavigationHover.SetNum(4);
}

void UColdSteelHUDWidget::TickPanelNavigation(const FGeometry& Geometry,float Delta)
{
    if(!PanelNavigationSlot)return;
    const float Scale=ColdSteelUI::PixelScale(this);
    const FVector2D View=Geometry.GetLocalSize()*Scale;
    if(View.X<100||View.Y<100)return;
    float Bottom=float(View.Y)-20.f;
    // Use the same weapon readout position even while its drawer visibility is hidden.
    if(AmmoReadout)
        if(const auto* AmmoSlot=Cast<UCanvasPanelSlot>(AmmoReadout->Slot))
            Bottom=FMath::Min(Bottom,float(View.Y)+(float(AmmoSlot->GetPosition().Y)-FMath::Max(124.f/Scale,float(AmmoReadout->GetDesiredSize().Y)))*Scale-12.f);
    const float MinimumTop=TopHUDBottom*Scale+12.f;
    const float Available=FMath::Max(1.f,Bottom-MinimumTop);
    // 四个入口：可分配高度里先扣悬停外伸（0.25×Size），再按 4 项与 3 段间距分配。
    const float Gap=FMath::Min(ColdSteelUI::NavigationGap,FMath::Max(0.f,(Available-4.25f*ColdSteelUI::NavigationSize)/3.f));
    const float Size=FMath::Min(ColdSteelUI::NavigationSize,(Available-3*Gap)/4.25f);
    const float Overflow=Size*(ColdSteelUI::NavigationHoverScale-1.f)*.5f;
    const float Height=4*Size+3*Gap;
    const float LastTop=FMath::Max(12.f,Bottom-Height-Overflow);
    const float FirstTop=FMath::Min(MinimumTop+Overflow,LastTop);
    const bool Rescale=!FMath::IsNearlyEqual(Scale,PanelNavigationScale,.001f)
        ||!FMath::IsNearlyEqual(Size,PanelNavigationSize,.1f)||!FMath::IsNearlyEqual(Gap,PanelNavigationGap,.1f);
    const float Top=FMath::Clamp(float(View.Y)*.375f-Height*.5f,FirstTop,LastTop);
    const FVector2D Position(-ColdSteelUI::NavigationRight/Scale,Top/Scale);
    if(!PanelNavigationSlot->GetPosition().Equals(Position,.1f))PanelNavigationSlot->SetPosition(Position);
    auto* PC=GetOwningPlayer();
    const bool Interactive=PC&&PC->bShowMouseCursor;
    // The drawer sits against the right edge now, so the entry column steps aside while it is out.
    // 开发面板（外部抽屉）共用同一让位条件。
    const bool bDrawerOut=bInventoryOpen||DrawerProgress>KINDA_SMALL_NUMBER||bExternalDrawerOpen;
    PanelNavigation->SetVisibility(bDrawerOut?ESlateVisibility::Collapsed:(Interactive?ESlateVisibility::Visible:ESlateVisibility::HitTestInvisible));
    PanelNavigationElapsed=FMath::Fmod(PanelNavigationElapsed+Delta,ColdSteelQuickSlotFX::KeyPeriod);
    const float KeyAlpha=ColdSteelQuickSlotFX::KeyOpacity(PanelNavigationElapsed);
    const int32 Active=bInventoryOpen?(bStatusTabActive?0:bSkillsTabActive?2:bCodexTabActive?3:1):INDEX_NONE;
    for(int32 Index=0;Index<4;++Index)
    {
        auto* Button=PanelNavigationButtons[Index].Get();
        auto* Key=PanelNavigationKeys[Index].Get();
        auto* Name=PanelNavigationNames[Index].Get();
        const bool Hover=Interactive&&(Button->IsHovered()||Button->HasKeyboardFocus());
        if(Rescale)
        {
            auto Style=ColdSteelUI::ButtonStyle(Scale);
            FSlateBrush Empty;Empty.DrawAs=ESlateBrushDrawType::NoDrawType;
            Style.SetNormal(Empty).SetHovered(Empty).SetPressed(Empty).SetDisabled(Empty);
            Style.SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0));Button->SetStyle(Style);
            PanelNavigationSizes[Index]->SetWidthOverride(Size/Scale);
            PanelNavigationSizes[Index]->SetHeightOverride(Size/Scale);
            Cast<UVerticalBoxSlot>(PanelNavigationSizes[Index]->Slot)->SetPadding(FMargin(0,0,0,Index<3?Gap/Scale:0));
            Key->SetFont(ColdSteelUI::NumberFont((Size>=64.f?12.f:9.f)/Scale,true));Key->SetShadowOffset(FVector2D(0,1/Scale));
            Cast<UOverlaySlot>(Key->Slot)->SetPadding(FMargin(0,0,4/Scale,2/Scale));
            PanelNavigationFallbacks[Index]->SetFont(ColdSteelUI::TextFont(9/Scale));
            Name->SetPadding(FMargin(8/Scale,5/Scale));
            Name->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Tooltip,6/Scale,ColdSteelUI::Border,1/Scale));
            Cast<UTextBlock>(Name->GetContent())->SetFont(ColdSteelUI::TextFont(9/Scale));
            Cast<UCanvasPanelSlot>(Name->Slot)->SetPosition(FVector2D(-(Overflow+16)/Scale,0));
            PanelNavigationMarkers[Index]->SetDesiredSizeOverride(FVector2D(3/Scale,24/Scale));
            PanelNavigationMarkers[Index]->SetRenderTranslation(FVector2D(-(Overflow+5)/Scale,0));
            PanelNavigationMarkers[Index]->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::NavigationSelected,1.5f/Scale,FLinearColor::Transparent,0));
        }
        const uint8 State=(Index==Active?1:0)|(Hover?2:0);
        if(Rescale||PanelNavigationStates[Index]!=State)
        {
            PanelNavigationMarkers[Index]->SetVisibility(Index==Active?ESlateVisibility::HitTestInvisible:ESlateVisibility::Hidden);
            PanelNavigationStates[Index]=State;
        }
        auto& Motion=PanelNavigationHover[Index];
        if(Motion.Target!=Hover){Motion.Target=Hover;Motion.From=Motion.Value;Motion.Elapsed=0.f;}
        if(Motion.Elapsed<ColdSteelUI::NavigationHoverDuration)
        {
            Motion.Elapsed=FMath::Min(ColdSteelUI::NavigationHoverDuration,Motion.Elapsed+Delta);
            Motion.Value=FMath::Lerp(Motion.From,Motion.Target?1.f:0.f,NavigationEase(Motion.Elapsed/ColdSteelUI::NavigationHoverDuration));
            const float Zoom=FMath::Lerp(1.f,ColdSteelUI::NavigationHoverScale,Motion.Value);
            PanelNavigationSubjects[Index]->SetRenderScale(FVector2D(Zoom,Zoom));
        }
        Name->SetVisibility(Motion.Value>.001f?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        Name->SetRenderOpacity(Motion.Value);
        Key->SetRenderOpacity(KeyAlpha);
    }
    PanelNavigationScale=Scale;
    PanelNavigationSize=Size;PanelNavigationGap=Gap;
}

void UColdSteelHUDWidget::ActivatePanelNavigation(int32 Entry)
{
    if(IsQuickDragging()){CancelQuickDrag();return;}
    // 入口序（0 状态／1 背包／2 技能／3 图鉴）与抽屉页面号不同：图鉴是第 4 页。
    const int32 Page=Entry==3?4:Entry;
    const int32 Active=bStatusTabActive?0:bSkillsTabActive?2:bCodexTabActive?3:1;
    if(bInventoryOpen&&Active==Entry){SetInventoryOpen(false);return;}
    UWidgetBlueprintLibrary::CancelDragDrop();
    if(Page!=1)CloseWarehouse();
    SetInventoryPage(Page);
    SetInventoryOpen(true);
    if(CloseButton)CloseButton->SetKeyboardFocus();
}

void UColdSteelHUDWidget::HandleNavigationStatus(){ActivatePanelNavigation(0);}
void UColdSteelHUDWidget::HandleNavigationBackpack(){ActivatePanelNavigation(1);}
void UColdSteelHUDWidget::HandleNavigationSkills(){ActivatePanelNavigation(2);}
void UColdSteelHUDWidget::HandleNavigationCodex(){ActivatePanelNavigation(3);}

bool UColdSteelHUDWidget::HandlePanelNavigationClick(FVector2D Position)
{
    if(!PanelNavigation||!PanelNavigation->IsVisible())return false;
    for(int32 Index=0;Index<PanelNavigationButtons.Num();++Index)
        if(PanelNavigationButtons[Index]->GetCachedGeometry().IsUnderLocation(Position))
        {ActivatePanelNavigation(Index);return true;}
    return false;
}
