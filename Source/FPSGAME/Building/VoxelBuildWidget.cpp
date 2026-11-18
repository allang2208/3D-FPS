#include "VoxelBuildWidget.h"
#include "VoxelBuildComponent.h"
#include "VoxelBuildIcons.h"
#include "../UI/ColdSteelUIStyle.h"
#include "../UI/GunsmithUIStyle.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScaleBox.h"
#include "Components/ScaleBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/SizeBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WrapBox.h"
#include "Components/WrapBoxSlot.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "InputCoreTypes.h"
#include "Framework/Application/SlateApplication.h"

#include "VoxelBuildWidgetLayoutPrivate.h"
using namespace VoxelBuildWidgetLayoutPrivate;


// Pixel sizes follow Docs/UI/ui-cold-steel-design-system.md (20/16/14/12 tiers).
namespace
{
    // Number row while the drawer is focused: the Nth card of the visible category.
    // Unity builds concatenate this file with VoxelBuildComponent.cpp, which already
    // declares its own anonymous-namespace NumberKeyIndex; keep this one distinct.
    int32 WidgetNumberKeyIndex(const FKey& Key)
    {
        static const FKey Keys[]={EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four,EKeys::Five,EKeys::Six,EKeys::Seven,EKeys::Eight,EKeys::Nine};
        for(int32 Index=0;Index<UE_ARRAY_COUNT(Keys);++Index)if(Key==Keys[Index])return Index;
        return INDEX_NONE;
    }
}

void UVoxelBuildCardProxy::Clicked()
{
    auto* Owner=Panel.Get();if(!Owner)return;
    // The 其他构造 disclosure sits on the same row as the material pick button.
    if(bToggleCard)Owner->ToggleMaterial(CardId);else Owner->Pick(CardId,bComponentCard,ShapeMode);
}

void UVoxelBuildCardProxy::Hovered()
{
    if(auto* Owner=Panel.Get())Owner->ShowTooltip(CardIndex);
}

void UVoxelBuildCardProxy::Unhovered()
{
    if(auto* Owner=Panel.Get())Owner->HideTooltip();
}

UTextBlock* UVoxelBuildWidget::Text(const FString& Caption,float Pixels,bool Numeric,bool Medium,bool bTrack)
{
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Caption));
    Label->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Label->SetFont(Numeric?GunsmithUI::NumberFont(Pixels/Scale,Medium):GunsmithUI::TextFont(Pixels/Scale,Medium));
    Label->SetVisibility(ESlateVisibility::HitTestInvisible);
    // Tooltip rows are rebuilt on every hover, so they are not tracked for DPI re-scaling.
    if(bTrack)Labels.Add({Label,Pixels,Numeric,Medium});return Label;
}

UButton* UVoxelBuildWidget::Tab(const FString& Caption,bool bComponents)
{
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Button=WidgetTree->ConstructWidget<UButton>();
    Button->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    // 字重由 RefreshCategory 按选中态设置，所以这里不把页签文字交给 DPI 托管（否则会被重设为 Regular）。
    Button->SetContent(Text(Caption,14,false,false,false));
    if(bComponents)Button->OnClicked.AddDynamic(this,&ThisClass::ShowComponentCategory);
    else Button->OnClicked.AddDynamic(this,&ThisClass::ShowMaterialCategory);
    return Button;
}

void UVoxelBuildWidget::ShowTooltip(int32 CardIndex)
{
    // VisibleCards holds the same rows as Cards in list order, so a submenu row shows its own card.
    if(!TooltipCard||!TooltipBox||!VisibleCards.IsValidIndex(CardIndex))return;
    const FVoxelBuildPanelCard* Entry=&VisibleCards[CardIndex];
    const float Scale=ColdSteelUI::PixelScale(this);
    TooltipTitle->SetText(FText::FromString(Entry->Caption));
    TooltipSubtitle->SetText(FText::FromString(Entry->Subtitle));
    TooltipBox->ClearChildren();
    for(const TPair<FString,FString>& Row:Entry->Rows)
    {
        if(Row.Value.IsEmpty())
        {
            auto* Section=Text(Row.Key,16,false,true,false);
            TooltipBox->AddChildToVerticalBox(Section)->SetPadding(FMargin(0,10/Scale,0,4/Scale));
            auto* Divider=WidgetTree->ConstructWidget<UBorder>();
            Divider->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Border,0));
            auto* Height=WidgetTree->ConstructWidget<USizeBox>();Height->SetHeightOverride(1/Scale);Divider->SetContent(Height);
            TooltipBox->AddChildToVerticalBox(Divider)->SetPadding(FMargin(0,0,0,4/Scale));
            continue;
        }
        auto* Line=WidgetTree->ConstructWidget<UHorizontalBox>();
        TooltipBox->AddChildToVerticalBox(Line)->SetPadding(FMargin(0,2/Scale));
        auto* Label=Text(Row.Key,14,false,false,false);Label->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        Label->SetAutoWrapText(true);
        FSlateChildSize LabelSize(ESlateSizeRule::Fill);LabelSize.Value=.45f;
        Line->AddChildToHorizontalBox(Label)->SetSize(LabelSize);
        auto* Value=Text(Row.Value,14,Entry->NumericRows.Contains(Row.Key),false,false);Value->SetJustification(ETextJustify::Right);
        Value->SetAutoWrapText(true);
        FSlateChildSize ValueSize(ESlateSizeRule::Fill);ValueSize.Value=.55f;
        Line->AddChildToHorizontalBox(Value)->SetSize(ValueSize);
    }
    if(!Entry->Note.IsEmpty())
    {
        auto* Note=Text(Entry->Note,12,false,false,false);Note->SetColorAndOpacity(ColdSteelUI::TextTertiary);Note->SetAutoWrapText(true);
        TooltipBox->AddChildToVerticalBox(Note)->SetPadding(FMargin(0,8/Scale,0,0));
    }
    const bool bSameCard=(TooltipIndex==CardIndex);
    TooltipIndex=CardIndex;
    // New card: restart the follow phase so the card settles under the pointer's approach.
    if(!bSameCard){bTooltipPinned=false;TooltipShownAtSeconds=-1.f;TooltipScroll->ScrollToStart();}
    if(TooltipShownAtSeconds<0.f&&GetWorld())TooltipShownAtSeconds=GetWorld()->GetRealTimeSeconds();
    TooltipCard->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    UpdateTooltipPlacement();
}

bool UVoxelBuildWidget::PointerWithin(UWidget* Target,float Margin) const
{
    if(!Target)return false;
    if(!FSlateApplication::IsInitialized())return false;
    const FGeometry& Geometry=Target->GetCachedGeometry();
    const FVector2D Local=Geometry.AbsoluteToLocal(FSlateApplication::Get().GetCursorPos());
    const FVector2D Size=Geometry.GetLocalSize();
    return Local.X>=-Margin&&Local.Y>=-Margin&&Local.X<=Size.X+Margin&&Local.Y<=Size.Y+Margin;
}

void UVoxelBuildWidget::HideTooltip(bool bForce)
{
    // Keep the card open while the pointer sits on the tooltip itself, so its close button is reachable.
    // 浮窗跟随阶段永远追不上指针，靠 UpdateTooltipPlacement 的「跟随一小段时间后钉住」让这个分支
    // 真正可达（2026-09-19 审计：此前关闭按钮永远点不到）。
    if(!bForce&&TooltipIndex!=INDEX_NONE&&TooltipCard&&TooltipCard->IsVisible())
    {
        if(PointerWithin(TooltipCard,TooltipKeepMarginPixels/ColdSteelUI::PixelScale(this)))return;
    }
    TooltipIndex=INDEX_NONE;bTooltipPinned=false;TooltipShownAtSeconds=-1.f;
    if(TooltipCard)TooltipCard->SetVisibility(ESlateVisibility::Collapsed);
}

void UVoxelBuildWidget::CloseTooltip(){HideTooltip(true);}

void UVoxelBuildWidget::UpdateTooltipPlacement()
{
    if(!TooltipCard||!TooltipSlot||TooltipIndex==INDEX_NONE)return;
    const float Scale=ColdSteelUI::PixelScale(this);
    const float KeepMargin=TooltipKeepMarginPixels/Scale;
    // 跟随一段时间后钉住位置，让「指针在浮窗内则保持」的分支真正可达（关闭按钮此前永远点不到）。
    if(!bTooltipPinned&&TooltipShownAtSeconds>=0.f&&GetWorld()&&
        GetWorld()->GetRealTimeSeconds()-TooltipShownAtSeconds>=TooltipFollowSeconds)bTooltipPinned=true;
    if(bTooltipPinned)
    {
        // 钉住后指针离开浮窗和来源卡片一起收掉，避免浮窗永远挂在屏幕上。
        UButton* Source=Cards.IsValidIndex(TooltipIndex)?Cards[TooltipIndex].Button.Get():nullptr;
        if(!PointerWithin(TooltipCard,KeepMargin)&&!PointerWithin(Source,KeepMargin)){HideTooltip(true);return;}
    }
    if(!FSlateApplication::IsInitialized())return;
    const FGeometry& RootGeometry=WidgetTree->RootWidget->GetCachedGeometry();
    const FVector2D Mouse=RootGeometry.AbsoluteToLocal(FSlateApplication::Get().GetCursorPos());
    FVector2D Units=RootGeometry.GetLocalSize();
    if(Units.IsNearlyZero())Units=UWidgetLayoutLibrary::GetViewportSize(this)/Scale;
    const float Gap=10/Scale;
    const FVector2D Extent(FMath::Max(1.f,FMath::Min(430.f/Scale,float(Units.X)-2*Gap)),
        FMath::Max(1.f,FMath::Min(520.f/Scale,float(Units.Y)-2*Gap)));
    // Open to the left of the cursor: the drawer itself sits on the right edge.
    FVector2D Position=bTooltipPinned?TooltipSlot->GetPosition():FVector2D(Mouse.X-Extent.X-Gap,Mouse.Y+Gap);
    if(!bTooltipPinned&&Position.X<Gap)Position.X=Mouse.X+Gap;
    Position.X=FMath::Clamp(Position.X,Gap,FMath::Max(Gap,Units.X-Extent.X-Gap));
    Position.Y=FMath::Clamp(Position.Y,Gap,FMath::Max(Gap,Units.Y-Extent.Y-Gap));
    TooltipSlot->SetPosition(Position);
    TooltipSlot->SetSize(Extent);
}

void UVoxelBuildWidget::SetDrawerOpen(bool Open)
{
    bDrawerOpen=Open;
    // A collapsed widget is not ticked, so the drawer has to be visible before it can slide in.
    if(Open){bIconPinsDirty=true;SetVisibility(ESlateVisibility::SelfHitTestInvisible);RefreshLayout();SetHudYielded(true);}
    else {HideTooltip(true);if(auto* Icons=IconsFor())Icons->Suspend();}
}

UColdSteelHUDWidget* UVoxelBuildWidget::ResolveHUD() const
{
    // HUD 持有让位标志（右侧入口列、世界时钟、右下武器详情共用），与开发面板同一路径。
    const auto* PC=GetOwningPlayer<AFPSGAMEPlayerController>();
    return PC?PC->GetColdSteelHUD():nullptr;
}

void UVoxelBuildWidget::SetHudYielded(bool bYielded)
{
    if(bYielded)
    {
        // 打开时无条件置位（HUD 可能晚于首次打开才就绪）；重复置位无副作用。
        if(auto* HUD=ResolveHUD())HUD->SetExternalDrawerOpen(true);
        bHudYielded=true;
        return;
    }
    if(!bHudYielded)return;
    bHudYielded=false;
    if(auto* HUD=ResolveHUD())HUD->SetExternalDrawerOpen(false);
}

void UVoxelBuildWidget::NativeDestruct()
{
    // 面板销毁时收回动画不会跑完，HUD 让位必须在这里直接解除（与开发面板同一处理）。
    SetHudYielded(false);
    if(auto* Icons=IconsFor())Icons->Suspend();
    Super::NativeDestruct();
}

void UVoxelBuildWidget::SetContent(const TArray<FVoxelBuildPanelCard>& Materials,const TArray<FVoxelBuildPanelCard>& Shapes,
    const TArray<FVoxelBuildPanelCard>& Components)
{
    auto Same=[](const TArray<FVoxelBuildPanelCard>& Current,const TArray<FVoxelBuildPanelCard>& Next)
    {
        if(Current.Num()!=Next.Num())return false;
        for(int32 Index=0;Index<Next.Num();++Index)
        {
            const auto& A=Current[Index];const auto& B=Next[Index];
            if(A.Id!=B.Id||A.Caption!=B.Caption||A.Detail!=B.Detail||A.MaterialId!=B.MaterialId||
                A.bComponent!=B.bComponent||A.ShapeMode!=B.ShapeMode||A.bExpandable!=B.bExpandable||
                A.IconCells!=B.IconCells||A.IconMesh!=B.IconMesh||A.IconSurface!=B.IconSurface||
                A.IconActorClass!=B.IconActorClass||A.IconPivotOffsetCm!=B.IconPivotOffsetCm||
                A.Subtitle!=B.Subtitle||A.Note!=B.Note||A.Rows.Num()!=B.Rows.Num()||
                A.NumericRows.Num()!=B.NumericRows.Num())return false;
            for(int32 Row=0;Row<A.Rows.Num();++Row)
                if(A.Rows[Row].Key!=B.Rows[Row].Key||A.Rows[Row].Value!=B.Rows[Row].Value)return false;
            for(const FString& Key:A.NumericRows)if(!B.NumericRows.Contains(Key))return false;
        }
        return true;
    };
    if(Same(MaterialCards,Materials)&&Same(ShapeCards,Shapes)&&Same(ComponentCards,Components))return;
    MaterialCards=Materials;ShapeCards=Shapes;ComponentCards=Components;bCardsDirty=true;
}

void UVoxelBuildWidget::SetSelection(FName Material,FName Component,int32 ShapeMode)
{
    if(SelectedMaterial==Material&&SelectedComponent==Component&&SelectedShape==ShapeMode)return;
    SelectedMaterial=Material;SelectedComponent=Component;SelectedShape=ShapeMode;bSelectionDirty=true;
}

void UVoxelBuildWidget::ToggleMaterial(FName MaterialId)
{
    if(MaterialId.IsNone())return;
    if(ExpandedMaterials.Contains(MaterialId))ExpandedMaterials.Remove(MaterialId);else ExpandedMaterials.Add(MaterialId);
    bCardsDirty=true;
}

void UVoxelBuildWidget::Pick(FName Id,bool bComponent,int32 ShapeMode)
{
    auto* Owner=Builder();
    if(!Owner)return;
    UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL 点击卡片 id=%s component=%d shape=%d"),*Id.ToString(),bComponent?1:0,ShapeMode);
    // Picking an entry ends the mouse phase; the component restores game input and aiming.
    if(bComponent)Owner->SelectComponent(Id);
    else if(ShapeMode>=0)Owner->SelectShape(Id,ShapeMode);
    else Owner->SelectMaterial(Id);
}

UVoxelBuildComponent* UVoxelBuildWidget::Builder() const
{
    auto* PC=GetOwningPlayer();
    return PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
}

FReply UVoxelBuildWidget::NativeOnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    auto* Owner=Builder();
    if(!Owner)return Super::NativeOnKeyDown(Geometry,Event);
    // Every key the focused drawer sees is consumed here; the game-side shortcuts skip that frame.
    Owner->MarkDrawerKeyHandled();
    const FKey Key=Event.GetKey();
    if(Key!=EKeys::Zero)
    {
        const int32 Number=WidgetNumberKeyIndex(Key);
        if(Number!=INDEX_NONE)
        {
            // 编号只认可见行：未命中即忽略，不再回落到 HandleDrawerKey 的调色板顺序
            // （2026-09-19 审计：此前会选中当前分类里没显示的条目并直接开建）。
            if(Cards.IsValidIndex(Number))Pick(Cards[Number].Id,Cards[Number].bComponent,Cards[Number].ShapeMode);
            return FReply::Handled();
        }
    }
    if(Owner->HandleDrawerKey(Key))return FReply::Handled();
    return Super::NativeOnKeyDown(Geometry,Event);
}

void UVoxelBuildWidget::ShowMaterialCategory(){if(bComponentCategory){bComponentCategory=false;bCardsDirty=true;}}
void UVoxelBuildWidget::ShowComponentCategory(){if(!bComponentCategory){bComponentCategory=true;bCardsDirty=true;}}

UButton* UVoxelBuildWidget::DisclosureButton(FName MaterialId,bool bExpanded)
{
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Proxy=NewObject<UVoxelBuildCardProxy>(this);
    Proxy->CardId=MaterialId;Proxy->bToggleCard=true;Proxy->Panel=this;
    CardProxies.Add(Proxy);
    auto* Button=WidgetTree->ConstructWidget<UButton>();
    // Expanded rows reuse the category tabs' selected style, so the state reads without an arrow glyph.
    Button->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    if(bExpanded)Button->SetStyle(ColdSteelUI::ButtonStyle(Scale).SetNormal(
        ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::ButtonRadius/Scale,ColdSteelUI::Accent,1/Scale)));
    Button->OnClicked.AddDynamic(Proxy,&UVoxelBuildCardProxy::Clicked);
    auto* Size=WidgetTree->ConstructWidget<USizeBox>();
    Size->SetWidthOverride(DisclosureWidth/Scale);Size->SetHeightOverride(DisclosureHeight/Scale);
    Button->SetContent(Size);
    auto* Label=Text(bExpanded?TEXT("收起构造"):TEXT("其他构造"),12,false,true);
    Label->SetJustification(ETextJustify::Center);
    Size->AddChild(Label);
    return Button;
}

UVoxelBuildIcons* UVoxelBuildWidget::IconsFor() const
{
    const auto* PC=GetOwningPlayer();
    auto* Instance=PC?PC->GetGameInstance():nullptr;
    return Instance?Instance->GetSubsystem<UVoxelBuildIcons>():nullptr;
}

void UVoxelBuildWidget::RefreshIcons()
{
    if(!bDrawerOpen)return;
    RefreshIconPins();
    auto* Icons=IconsFor();
    if(!Icons)return;
    for(const FCard& Card:Cards)
    {
        auto* Image=Card.Image.Get();
        if(!Image||Card.IconKey.IsEmpty())continue;
        if(UMaterialInterface* Material=Icons->Find(Card.IconKey))
        {
            // 同一键的缩略图会被重建（换了材质或重新出图），画刷还指着旧实例就重新绑定。
            if(Cast<UMaterialInterface>(Image->GetBrush().GetResourceObject())!=Material)
                Image->SetBrushFromMaterial(Material);
            Image->SetVisibility(ESlateVisibility::HitTestInvisible);
            if(auto* Placeholder=Card.Placeholder.Get())Placeholder->SetVisibility(ESlateVisibility::Collapsed);
            continue;
        }
        Image->SetVisibility(ESlateVisibility::Hidden);
        if(auto* Placeholder=Card.Placeholder.Get())
        {
            Placeholder->SetVisibility(ESlateVisibility::HitTestInvisible);
            Placeholder->SetText(FText::FromString(Icons->HasFailed(Card.IconKey)?TEXT("暂无预览"):TEXT("加载中")));
        }
        Icons->Request(Card.IconRequest);
    }
}

void UVoxelBuildWidget::RefreshIconPins()
{
    if(!bIconPinsDirty||!bDrawerOpen)return;
    bIconPinsDirty=false;
    auto* Icons=IconsFor();
    if(!Icons)return;
    TSet<FString> Keys;
    for(const FCard& Card:Cards)if(!Card.IconKey.IsEmpty())Keys.Add(Card.IconKey);
    Icons->SetVisibleKeys(Keys);
}

void UVoxelBuildWidget::RefreshSelection()
{
    const float Scale=ColdSteelUI::PixelScale(this);
    for(const FCard& Card:Cards)
    {
        auto* Widget=Card.Surface.Get();if(!Widget)continue;
        // Material rows stay highlighted for the current material; a submenu row highlights only when
        // it is the exact shape or component in hand.
        const bool bSelected=Card.bComponent?(!SelectedComponent.IsNone()&&SelectedComponent==Card.Id):
            (SelectedComponent.IsNone()&&SelectedMaterial==Card.Id&&(Card.ShapeMode==INDEX_NONE||Card.ShapeMode==SelectedShape));
        Widget->SetBrush(ColdSteelUI::RoundedBrush(bSelected?ColdSteelUI::ButtonHover:(Card.bChild?ColdSteelUI::Content:ColdSteelUI::StatusCard),
            ColdSteelUI::CardRadius/Scale,
            bSelected?ColdSteelUI::Accent:ColdSteelUI::Border,
            bSelected?2/Scale:1/Scale));
    }
}

void UVoxelBuildWidget::RefreshCategory()
{
    const float Scale=ColdSteelUI::PixelScale(this);
    const FButtonStyle Normal=ColdSteelUI::ButtonStyle(Scale);
    const FButtonStyle Selected=ColdSteelUI::ButtonStyle(Scale).SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::ButtonRadius/Scale,ColdSteelUI::Accent,1/Scale));
    if(MaterialTab)MaterialTab->SetStyle(bComponentCategory?Normal:Selected);
    if(ComponentTab)ComponentTab->SetStyle(bComponentCategory?Selected:Normal);
    // 选中＝Medium、未选中＝Regular（规划条款）；两个页签字体各自按当前 Scale 设置。
    auto ApplyTabFont=[](UTextBlock* Label,bool bSelected,float Scale)
    {
        if(Label)Label->SetFont(GunsmithUI::TextFont(14/Scale,bSelected));
    };
    ApplyTabFont(MaterialTabLabel.Get(),!bComponentCategory,Scale);
    ApplyTabFont(ComponentTabLabel.Get(),bComponentCategory,Scale);
}

void UVoxelBuildWidget::RefreshLayout()
{
    if(!PanelSlot||!Surface)return;
    const FVector2D View=UWidgetLayoutLibrary::GetViewportSize(this);const float Scale=ColdSteelUI::PixelScale(this);
    if(View.Equals(LastViewport,.5)&&FMath::IsNearlyEqual(Scale,LastScale,.001f))return;
    const bool bScaleChanged=!FMath::IsNearlyEqual(Scale,LastScale,.001f);
    LastViewport=View;LastScale=Scale;
    if(bScaleChanged)bCardsDirty=true;
    const float Pixels=FMath::Max(320.f,View.X);
    const float Width=FMath::Min(FMath::Clamp(Pixels*DrawerViewportFraction,DrawerMinWidth,DrawerMaxWidth),FMath::Max(240.f,Pixels-DrawerEdgeInset));
    DrawerWidth=Width/Scale;
    PanelSlot->SetOffsets(FMargin(0,DrawerEdgeInset/Scale,Width/Scale,DrawerEdgeInset/Scale));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));
    Surface->SetPadding(FMargin(DrawerBorderInset/Scale));
    if(HeaderSize)HeaderSize->SetHeightOverride(HeaderHeight/Scale);
    if(HeaderPanel)
    {
        HeaderPanel->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
        HeaderPanel->SetPadding(FMargin(18/Scale,0));
    }
    if(GlassTintPanel)GlassTintPanel->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));
    if(Blur)
    {
        Blur->SetCornerRadius(FVector4(ColdSteelUI::PanelRadius/Scale));
        Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius/Scale));
    }
    auto Pad=[Scale](UWidget* Widget,FMargin Pixels)
    {
        if(Widget)if(auto* LayoutSlot=Cast<UVerticalBoxSlot>(Widget->Slot))
            LayoutSlot->SetPadding(FMargin(Pixels.Left/Scale,Pixels.Top/Scale,Pixels.Right/Scale,Pixels.Bottom/Scale));
    };
    Pad(Status,FMargin(18,10,12,2));Pad(Selection,FMargin(18,0,12,4));
    Pad(Structure,FMargin(18,0,12,10));Pad(Risk,FMargin(18,0,12,8));
    Pad(Scroll,FMargin(BuildScrollLeft,0,BuildScrollRight,0));Pad(Controls,FMargin(18,8,18,12));
    if(MaterialTab)Pad(MaterialTab->GetParent(),FMargin(12,0,12,8));
    for(UButton* TabButton:{MaterialTab.Get(),ComponentTab.Get()})if(TabButton)
    {
        if(auto* TabSlot=Cast<UHorizontalBoxSlot>(TabButton->Slot))TabSlot->SetPadding(FMargin(ColdSteelUI::ActionGap*.5f/Scale,0));
        if(auto* ContentSlot=Cast<UButtonSlot>(TabButton->GetContent()->Slot))ContentSlot->SetPadding(FMargin(10/Scale,8/Scale));
    }
    if(bScaleChanged&&TooltipCard){HideTooltip(true);TooltipCard->RemoveFromParent();BuildTooltipCard();}
    if(Scroll)ConfigureBuildScroll(Scroll,Scale);
    // Grid spacing and the identical card sizes are DPI-dependent, so they are re-applied with the
    // same scale as the fonts instead of being baked at construction time.
    for(const TWeakObjectPtr<UWrapBox>& Grid:Grids)
        if(auto* Box=Grid.Get())ConfigureBuildGrid(Box,DrawerWidth,Scale,!bComponentCategory);
    for(const FCard& Card:Cards)
    {
        if(!Card.bGridCard)
        {
            // 材质行：只重算它自己的行高与 28px 缩略图，不套 116×150 网格卡尺寸
            // （2026-09-19 审计：此前 DPI/视口变化把材质行重排成大卡片）。
            if(auto* CardBox=Card.Box.Get())CardBox->SetHeightOverride((CardHeight-8.f)/Scale);
            if(auto* IconBox=Card.IconBox.Get())
            {IconBox->SetWidthOverride(MaterialThumbPixels/Scale);IconBox->SetHeightOverride(MaterialThumbPixels/Scale);}
            continue;
        }
        if(auto* CardBox=Card.Box.Get()){CardBox->SetWidthOverride(GridCardWidth/Scale);CardBox->SetMinDesiredHeight(GridCardMinHeight/Scale);}
        if(auto* IconBox=Card.IconBox.Get()){IconBox->SetWidthOverride(GridIconPixels/Scale);IconBox->SetHeightOverride(GridIconPixels/Scale);}
    }
    for(const FLabel& Label:Labels)if(auto* TextBlock=Label.Widget.Get())
        TextBlock->SetFont(Label.Numeric?GunsmithUI::NumberFont(Label.Pixels/Scale,Label.Medium):GunsmithUI::TextFont(Label.Pixels/Scale,Label.Medium));
    Controls->SetText(FText::FromString(
        TEXT("「其他构造」含该分类的形状与构件；「其他」仅含未归类构件。\n")
        TEXT("1–9 选面板前 9 项 · 0 取消构件 · Esc 返回建造 · B 退出建造\n")
        TEXT("建造时：左键放 / 右键拆 · 滚轮换形状 · R 旋转 · F 吸附 · 中键取样 · Ctrl+Z 撤建 · Z 拾取")));
    RefreshCategory();
}

void UVoxelBuildWidget::ShowState(const FString& Headline,const FString& Brush,const FString& Message,bool bValid,bool bSnapEnabled,
    float StructureRisk,const FString& StructureSummary)
{
    // 审计 P16（本函数由组件每帧调用一次）：
    // 原实现**先**构造 SelectionText（1 次 Printf）与 Signature（1 次拼接），**之后**才比较
    // LastState —— 守卫存在但成本已经付掉；Risk 块更是无条件执行（含 1–2 次 Printf）后才发现
    // 内容没变。现在把"要不要更新"的判定放在最前：先用廉价分量（含风险分级与风险文本）
    // 组签名，只有签名变化时才构造要写进控件的字符串。
    const bool bDanger=StructureRisk>=1.f;
    const bool bWarn=StructureRisk>=.85f;
    // 风险行只在 bWarn 时可见且显示 StructureSummary；把分级与摘要一起纳入签名，
    // 使得"风险从 90% 涨到 92%"这类只在文本里体现的变化仍然会刷新。
    const int32 RiskLevel=bDanger?2:(bWarn?1:0);
    const FString Signature=FString::Printf(TEXT("%d|%d|%d|%s|%s|%s|%s"),
        bValid?1:0,bSnapEnabled?1:0,RiskLevel,*Headline,*Brush,*Message,bWarn?*StructureSummary:TEXT(""));
    if(Signature==LastState)return;
    LastState=Signature;
    if(Risk)
    {
        // 85% warns, 100% means a joint is breaking: same semantic colours as the rest of the HUD.
        Risk->SetVisibility(bWarn?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(bWarn)
        {
            const FString Detail=StructureSummary.IsEmpty()?FString::Printf(TEXT("%.0f%%"),StructureRisk*100.):StructureSummary;
            Risk->SetText(FText::FromString(bDanger
                ?FString::Printf(TEXT("结构超限 · 正在断裂 · %s"),*Detail)
                :FString::Printf(TEXT("结构预警 · %s · 加厚或补支撑"),*Detail)));
            Risk->SetColorAndOpacity(bDanger?ColdSteelUI::Danger:ColdSteelUI::Warning);
        }
    }
    Selection->SetText(FText::FromString(Brush));
    Status->SetText(FText::FromString(Headline));
    Status->SetColorAndOpacity(bValid?ColdSteelUI::TextPrimary:ColdSteelUI::Warning);
    const TCHAR* Snap=bSnapEnabled?TEXT("体素吸附已开启 · F 自由放置"):TEXT("自由位置 · F 开启体素吸附");
    Structure->SetText(FText::FromString(FString(Snap)+TEXT("\n")+Message));
}

void UVoxelBuildWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    RefreshLayout();
    if(bCardsDirty){bCardsDirty=false;RebuildCards();bSelectionDirty=true;RefreshCategory();}
    // Thumbnails are captured one per frame by the icon subsystem; the cards pick them up here.
    RefreshIcons();
    if(bSelectionDirty){bSelectionDirty=false;RefreshSelection();}
    if(TooltipIndex!=INDEX_NONE)UpdateTooltipPlacement();
    DrawerProgress=FMath::FInterpConstantTo(DrawerProgress,bDrawerOpen?1.f:0.f,Delta,4.f);
    if(Surface)Surface->SetRenderTranslation(FVector2D((1.f-DrawerProgress)*DrawerWidth,0.f));
    // 与背包同一抽屉规格：压暗底与玻璃随进度淡入（文字保持清晰）；收起动画播完才解让位。
    // 压暗底只做视觉（HitTestInvisible）：建造面板没有「点外部关闭」，不能吞掉回到瞄准后的点击。
    if(Backdrop)
    {
        Backdrop->SetRenderOpacity(DrawerProgress);
        Backdrop->SetVisibility(DrawerProgress>KINDA_SMALL_NUMBER?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    }
    if(Blur)Blur->SetRenderOpacity(DrawerProgress);
    if(!bDrawerOpen&&DrawerProgress<=KINDA_SMALL_NUMBER)
    {
        SetVisibility(ESlateVisibility::Collapsed);
        SetHudYielded(false);
    }
}
