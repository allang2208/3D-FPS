#include "VoxelBuildWidget.h"
#include "../UI/ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"

void UVoxelBuildWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(false);
    auto* Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    Surface=WidgetTree->ConstructWidget<UBorder>();PanelSlot=Root->AddChildToCanvas(Surface);
    PanelSlot->SetAnchors(FAnchors(1.f,.7f));PanelSlot->SetAlignment(FVector2D(1,.5));
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Surface->SetContent(Stack);
    auto Add=[&](const FLinearColor& Color)
    {
        auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetColorAndOpacity(Color);Label->SetAutoWrapText(true);
        Stack->AddChildToVerticalBox(Label)->SetPadding(FMargin(0,3));return Label;
    };
    Title=Add(ColdSteelUI::TextPrimary);Selection=Add(ColdSteelUI::TextPrimary);
    Status=Add(ColdSteelUI::Success);Controls=Add(ColdSteelUI::TextSecondary);
    Title->SetText(FText::FromString(TEXT("自由建造 · 材料不限量")));RefreshLayout();
}

void UVoxelBuildWidget::ShowState(const FString& Material,const FString& Brush,const FString& Message,bool bValid,int32 Count)
{
    const FString SelectionText=FString::Printf(TEXT("%s\n%s\n已建造 %d 格"),*Material,*Brush,Count);
    const FString Signature=SelectionText+Message+(bValid?TEXT("1"):TEXT("0"));if(Signature==LastState)return;LastState=Signature;
    Selection->SetText(FText::FromString(SelectionText));Status->SetText(FText::FromString(Message));
    Status->SetColorAndOpacity(bValid?ColdSteelUI::Success:ColdSteelUI::Warning);
}

void UVoxelBuildWidget::RefreshLayout()
{
    const FVector2D View=UWidgetLayoutLibrary::GetViewportSize(this);const float Scale=ColdSteelUI::PixelScale(this);
    if(View.Equals(LastViewport,.5)&&FMath::IsNearlyEqual(Scale,LastScale,.001f))return;
    LastViewport=View;LastScale=Scale;
    const float Width=FMath::Min(FMath::Clamp(View.X*.26f,230.f,340.f),FMath::Max(100.f,View.X-40.f))/Scale;
    const float Height=FMath::Min(View.Y<650?228.f:280.f,FMath::Max(100.f,View.Y-40.f))/Scale;
    PanelSlot->SetPosition(FVector2D(-20.f/Scale,0));PanelSlot->SetSize(FVector2D(Width,Height));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));
    Surface->SetPadding(FMargin(12/Scale,8/Scale));
    Title->SetFont(ColdSteelUI::TextFont(16*.75f/Scale,true));Selection->SetFont(ColdSteelUI::TextFont(14*.75f/Scale));
    Status->SetFont(ColdSteelUI::TextFont(12*.75f/Scale));Controls->SetFont(ColdSteelUI::TextFont(12*.75f/Scale));
    Controls->SetText(FText::FromString(View.Y<650?TEXT("1 木材 / 2 石头 · 滚轮换刷子\n左键放置 / 右键拆除 · R 旋转\n中键取样 · Ctrl+Z 撤销\nV / Esc 退出"):
        TEXT("1 木材 / 2 石头\n滚轮切换单格、地板、墙面\n左键放置 / 右键拆除\nR 旋转墙面 · 中键取样\nCtrl+Z 撤销 · V / Esc 退出")));
}

void UVoxelBuildWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);RefreshLayout();
}
