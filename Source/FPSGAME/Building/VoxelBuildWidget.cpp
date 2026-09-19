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

// Pixel sizes follow Docs/UI/ui-cold-steel-design-system.md (20/16/14/12 tiers).
namespace
{
    constexpr float HeaderHeight=36.f,CardHeight=44.f,CardGap=4.f;
    // 指针离浮窗边缘在这个屏幕像素余量内就保持浮窗打开（含指针从卡片移向关闭按钮的路径）。
    constexpr float TooltipKeepMarginPixels=44.f;
    // 浮窗显示后跟随鼠标这么久就钉住位置：跟随阶段浮窗永远在光标外 10px，关闭按钮够不到；
    // 钉住后玩家能移到浮窗上点 ×（2026-09-19 审计）。
    constexpr float TooltipFollowSeconds=.7f;
    // Material rows carry the 其他构造 disclosure; its submenu rows are indented underneath.
    constexpr float ChildIndent=14.f,DisclosureWidth=96.f,DisclosureHeight=26.f;
    // 其他构造 grid: one identical card per construction, equal gaps, wrapping when a row is full.
    constexpr float GridGap=8.f,GridCardWidth=116.f,GridCardMinHeight=170.f,GridIconPixels=104.f;
    constexpr float GridCardPadding=5.f,GridNameInset=2.f;
    constexpr float GridNameWidth=GridCardWidth-2.f*(GridCardPadding+GridNameInset);
    /** 材质行左侧缩略图；DPI/视口变化时按此重算，不跟网格卡的 104px 混用。 */
    constexpr float MaterialThumbPixels=28.f;
    constexpr float DrawerViewportFraction=.48f,DrawerMinWidth=720.f,DrawerMaxWidth=1040.f,DrawerEdgeInset=12.f;
    constexpr float DrawerBorderInset=1.f,BuildScrollLeft=18.f,BuildScrollRight=12.f,BuildScrollbarWidth=6.f;

    void ConfigureBuildScroll(UScrollBox* ScrollBox,float Scale)
    {
        // Reserve the same gutter before and after a material expansion needs scrolling.
        ScrollBox->SetAlwaysShowScrollbar(true);
        ScrollBox->SetScrollbarPadding(FMargin(0));
        ScrollBox->SetScrollbarThickness(FVector2D(BuildScrollbarWidth/Scale));
        FScrollBoxStyle ScrollStyle=ScrollBox->GetWidgetStyle();
        ScrollStyle.SetVerticalScrolledContentPadding(FMargin(0));
        ScrollBox->SetWidgetStyle(ScrollStyle);
        // The track brushes also contribute desired width; thickness alone does not constrain them.
        FScrollBarStyle BarStyle=ScrollBox->GetWidgetBarStyle();
        BarStyle.VerticalTopSlotImage.SetImageSize(FVector2D(BuildScrollbarWidth/Scale,BarStyle.VerticalTopSlotImage.GetImageSize().Y));
        BarStyle.VerticalBottomSlotImage.SetImageSize(FVector2D(BuildScrollbarWidth/Scale,BarStyle.VerticalBottomSlotImage.GetImageSize().Y));
        ScrollBox->SetWidgetBarStyle(BarStyle);
    }

    void ConfigureBuildGrid(UWrapBox* Grid,float DrawerWidth,float Scale,bool bIndented)
    {
        const float Indent=bIndented?ChildIndent:0.f;
        const float AvailableWidth=DrawerWidth-(2.f*DrawerBorderInset+BuildScrollLeft+BuildScrollRight+BuildScrollbarWidth+Indent)/Scale;
        // Recreated grids must not start from UWrapBox's default 500-unit preferred width.
        Grid->SetExplicitWrapSize(true);
        Grid->SetWrapSize(FMath::Max(GridCardWidth/Scale,AvailableWidth));
        Grid->SetInnerSlotPadding(FVector2D(GridGap/Scale,GridGap/Scale));
        if(auto* GridSlot=Cast<UVerticalBoxSlot>(Grid->Slot))
            GridSlot->SetPadding(FMargin(Indent/Scale,bIndented?0.f:2.f/Scale,0,GridGap/Scale));
    }
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

void UVoxelBuildWidget::NativeOnInitialized()
{
    // The drawer takes keyboard focus while it owns the cursor, so Esc/B and 1-9 stay here.
    Super::NativeOnInitialized();SetIsFocusable(true);
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    // 与背包同一抽屉规格：全屏 40% 压暗底在面板之下，随滑出进度淡入淡出（2026-09-19 补齐）。
    Backdrop=WidgetTree->ConstructWidget<UBorder>();
    Backdrop->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor(0,0,0,.40f),0.f,FLinearColor::Transparent,0.f));
    Backdrop->SetVisibility(ESlateVisibility::Collapsed);
    auto* BackdropSlot=Root->AddChildToCanvas(Backdrop);
    BackdropSlot->SetAnchors(FAnchors(0,0,1,1));BackdropSlot->SetOffsets(FMargin(0));BackdropSlot->SetZOrder(0);
    Surface=WidgetTree->ConstructWidget<UBorder>();PanelSlot=Root->AddChildToCanvas(Surface);
    PanelSlot->SetZOrder(1);
    PanelSlot->SetAnchors(FAnchors(1,0,1,1));PanelSlot->SetAlignment(FVector2D(1,0));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));
    Surface->SetPadding(FMargin(DrawerBorderInset/Scale));
    Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();Blur->SetPadding(FMargin(0));
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetOverrideAutoRadiusCalculation(true);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);Blur->SetApplyAlphaToBlur(true);
    Blur->SetCornerRadius(FVector4(ColdSteelUI::PanelRadius));
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
    Surface->SetContent(Blur);
    auto* Tint=WidgetTree->ConstructWidget<UBorder>();GlassTintPanel=Tint;
    Tint->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));Tint->SetPadding(FMargin(0));
    Blur->SetContent(Tint);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Tint->SetContent(Stack);
    auto* Header=WidgetTree->ConstructWidget<UBorder>();HeaderPanel=Header;
    Header->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    Stack->AddChildToVerticalBox(Header);
    HeaderSize=WidgetTree->ConstructWidget<USizeBox>();HeaderSize->SetHeightOverride(HeaderHeight/Scale);Header->SetContent(HeaderSize);
    Header->SetPadding(FMargin(18/Scale,0));
    auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(Heading);
    Title=Text(TEXT("自由建造"),20,false,true);
    auto* TitleSlot=Heading->AddChildToHorizontalBox(Title);
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();Stack->AddChildToVerticalBox(Body)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Status=Text(TEXT(""),14,false,true);Status->SetAutoWrapText(true);
    Body->AddChildToVerticalBox(Status)->SetPadding(FMargin(18/Scale,10/Scale,12/Scale,2/Scale));
    Selection=Text(TEXT(""),14);Selection->SetAutoWrapText(true);
    Selection->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Body->AddChildToVerticalBox(Selection)->SetPadding(FMargin(18/Scale,0,12/Scale,4/Scale));
    Structure=Text(TEXT(""),12);Structure->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Structure->SetAutoWrapText(true);
    Body->AddChildToVerticalBox(Structure)->SetPadding(FMargin(18/Scale,0,12/Scale,10/Scale));
    // Structure warning: hidden until the weakest joint passes 85% of its limit, then it names the
    // governing stress, the percentage and the cell so the player knows what to thicken or support.
    Risk=Text(TEXT(""),12,false,true);Risk->SetAutoWrapText(true);Risk->SetVisibility(ESlateVisibility::Collapsed);
    Body->AddChildToVerticalBox(Risk)->SetPadding(FMargin(18/Scale,0,12/Scale,8/Scale));
    auto* Tabs=WidgetTree->ConstructWidget<UHorizontalBox>();
    Body->AddChildToVerticalBox(Tabs)->SetPadding(FMargin(12/Scale,0,12/Scale,8/Scale));
    // 2026-09-16: the old 构件 category is renamed 其他, because constructions are now grouped under
    // the material that owns them; 其他 contains only pieces without a material category.
    MaterialTab=Tab(TEXT("材质"),false);ComponentTab=Tab(TEXT("其他"),true);
    // 页签字重由 RefreshCategory 按选中态设置；此前把分类标志误当 Medium 传进 Text()，两页签字重恒定不同。
    MaterialTabLabel=Cast<UTextBlock>(MaterialTab->GetContent());
    ComponentTabLabel=Cast<UTextBlock>(ComponentTab->GetContent());
    for(UButton* Entry:{MaterialTab.Get(),ComponentTab.Get()})
    {
        auto* TabSlot=Tabs->AddChildToHorizontalBox(Entry);TabSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        TabSlot->SetPadding(FMargin(ColdSteelUI::ActionGap*.5f/Scale,0));
        Cast<UButtonSlot>(Entry->GetContent()->Slot)->SetPadding(FMargin(10/Scale,8/Scale));
    }
    Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetAllowOverscroll(false);
    ConfigureBuildScroll(Scroll,Scale);
    auto* ScrollSlot=Body->AddChildToVerticalBox(Scroll);
    ScrollSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));ScrollSlot->SetPadding(FMargin(BuildScrollLeft/Scale,0,BuildScrollRight/Scale,0));
    CardList=WidgetTree->ConstructWidget<UVerticalBox>();Scroll->AddChild(CardList);
    Controls=Text(TEXT(""),12);Controls->SetColorAndOpacity(ColdSteelUI::TextTertiary);Controls->SetAutoWrapText(true);
    Stack->AddChildToVerticalBox(Controls)->SetPadding(FMargin(18/Scale,8/Scale,18/Scale,12/Scale));
    BuildTooltipCard();
    SetVisibility(ESlateVisibility::Collapsed);
}

void UVoxelBuildWidget::BuildTooltipCard()
{
    // Same card as the equipment tooltip (surface, outline, 16px radius, red close button).
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Root=Cast<UCanvasPanel>(WidgetTree->RootWidget);
    if(!Root)return;
    TooltipCard=WidgetTree->ConstructWidget<UBorder>();
    TooltipCard->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Tooltip,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));
    TooltipCard->SetPadding(FMargin(20/Scale,16/Scale));
    TooltipCard->SetClipping(EWidgetClipping::ClipToBounds);
    TooltipCard->SetVisibility(ESlateVisibility::Collapsed);
    TooltipSlot=Root->AddChildToCanvas(TooltipCard);
    TooltipSlot->SetAnchors(FAnchors(0));TooltipSlot->SetAlignment(FVector2D(0,0));TooltipSlot->SetZOrder(60);
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();TooltipCard->SetContent(Column);
    auto* Header=WidgetTree->ConstructWidget<UHorizontalBox>();
    Column->AddChildToVerticalBox(Header)->SetPadding(FMargin(0,0,0,8/Scale));
    auto* Titles=WidgetTree->ConstructWidget<UVerticalBox>();
    Header->AddChildToHorizontalBox(Titles)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TooltipTitle=Text(TEXT(""),16,false,true);TooltipTitle->SetAutoWrapText(true);Titles->AddChildToVerticalBox(TooltipTitle);
    TooltipSubtitle=Text(TEXT(""),12);TooltipSubtitle->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    TooltipSubtitle->SetAutoWrapText(true);
    Titles->AddChildToVerticalBox(TooltipSubtitle);
    auto* Close=WidgetTree->ConstructWidget<UButton>();
    Close->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    auto* CloseLabel=Text(TEXT("×"),14);CloseLabel->SetJustification(ETextJustify::Center);
    Close->SetContent(CloseLabel);Cast<UButtonSlot>(CloseLabel->Slot)->SetPadding(FMargin(0));
    Close->OnClicked.AddDynamic(this,&ThisClass::CloseTooltip);
    auto* CloseSize=WidgetTree->ConstructWidget<USizeBox>();
    CloseSize->SetWidthOverride(24/Scale);CloseSize->SetHeightOverride(24/Scale);CloseSize->SetContent(Close);
    Header->AddChildToHorizontalBox(CloseSize);
    TooltipScroll=WidgetTree->ConstructWidget<UScrollBox>();TooltipScroll->SetAllowOverscroll(false);
    TooltipScroll->SetScrollbarThickness(FVector2D(6/Scale));
    Column->AddChildToVerticalBox(TooltipScroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TooltipBox=WidgetTree->ConstructWidget<UVerticalBox>();TooltipScroll->AddChild(TooltipBox);
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

void UVoxelBuildWidget::AddGridCard(UWrapBox* Grid,const FVoxelBuildPanelCard& Entry,FName MaterialId,bool bChild,
    const FVoxelBuildPanelCard* MaterialRow)
{
    if(!Grid)return;
    const float Scale=ColdSteelUI::PixelScale(this);
    // Shapes reuse the material row's block mesh and surface, so the thumbnail shows the same stone /
    // wood / marble the player would place; pieces bring their own mesh.
    FVoxelBuildIconRequest Request;
    if(Entry.bComponent)
    {
        Request.Key=UVoxelBuildIcons::KeyForPiece(Entry.Id);
        Request.Mesh=Entry.IconMesh;Request.Surface=Entry.IconSurface;
        Request.ActorClass=Entry.IconActorClass;
        Request.PivotOffsetCm=Entry.IconPivotOffsetCm;
    }
    else
    {
        Request.Key=UVoxelBuildIcons::KeyForShape(MaterialId,Entry.ShapeMode);
        Request.Cells=Entry.IconCells;
        if(MaterialRow){Request.Mesh=MaterialRow->IconMesh;Request.Surface=MaterialRow->IconSurface;}
    }
    Request.Key=UVoxelBuildIcons::ContentKey(Request);
    if(bDrawerOpen)if(auto* Icons=IconsFor())Icons->Request(Request);

    auto* Proxy=NewObject<UVoxelBuildCardProxy>(this);
    // 形状卡由所属材质行代持（点它 = 选该材质的这个形状）；构件卡必须始终用构件自己的 ID：
    // 之前这里对 bChild 的构件也写了材质 ID，结果「点材质栏下的门」等于选了材质并清空构件，
    // 看上去就像仍停在之前选择的构件上（2026-09-17 用户反馈）。
    Proxy->CardId=Entry.bComponent?Entry.Id:(bChild?MaterialId:Entry.Id);
    Proxy->bComponentCard=Entry.bComponent;
    Proxy->ShapeMode=bChild?Entry.ShapeMode:INDEX_NONE;
    Proxy->Panel=this;Proxy->CardIndex=Cards.Num();
    CardProxies.Add(Proxy);

    auto* Button=WidgetTree->ConstructWidget<UButton>();
    Button->SetStyle(FButtonStyle()
        .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
        .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale))
        .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Accent,1/Scale)));
    Button->OnClicked.AddDynamic(Proxy,&UVoxelBuildCardProxy::Clicked);
    Button->OnHovered.AddDynamic(Proxy,&UVoxelBuildCardProxy::Hovered);
    Button->OnUnhovered.AddDynamic(Proxy,&UVoxelBuildCardProxy::Unhovered);
    auto* Box=WidgetTree->ConstructWidget<USizeBox>();
    Box->SetWidthOverride(GridCardWidth/Scale);Box->SetMinDesiredHeight(GridCardMinHeight/Scale);
    Button->SetContent(Box);
    auto* CardContentSlot=Cast<UButtonSlot>(Box->Slot);
    CardContentSlot->SetPadding(FMargin(0));
    CardContentSlot->SetHorizontalAlignment(HAlign_Fill);CardContentSlot->SetVerticalAlignment(VAlign_Fill);
    auto* SurfaceCard=WidgetTree->ConstructWidget<UBorder>();
    SurfaceCard->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::CardRadius/Scale));
    SurfaceCard->SetPadding(FMargin(GridCardPadding/Scale));Box->SetContent(SurfaceCard);
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();SurfaceCard->SetContent(Column);
    auto* IconBox=WidgetTree->ConstructWidget<USizeBox>();
    IconBox->SetWidthOverride(GridIconPixels/Scale);IconBox->SetHeightOverride(GridIconPixels/Scale);
    auto* Picture=WidgetTree->ConstructWidget<UImage>();
    Picture->SetColorAndOpacity(FLinearColor::White);Picture->SetVisibility(ESlateVisibility::HitTestInvisible);
    Picture->SetDesiredSizeOverride(FVector2D(256.f,256.f));
    auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();
    Fit->SetStretch(EStretch::ScaleToFit);Fit->SetContent(Picture);
    auto* FitSlot=Cast<UScaleBoxSlot>(Picture->Slot);
    FitSlot->SetHorizontalAlignment(HAlign_Center);FitSlot->SetVerticalAlignment(VAlign_Center);
    auto* Preview=WidgetTree->ConstructWidget<UOverlay>();IconBox->SetContent(Preview);
    auto* PreviewSlot=Preview->AddChildToOverlay(Fit);
    PreviewSlot->SetHorizontalAlignment(HAlign_Fill);PreviewSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Placeholder=Text(TEXT("加载中"),12);Placeholder->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    auto* PlaceholderSlot=Preview->AddChildToOverlay(Placeholder);
    PlaceholderSlot->SetHorizontalAlignment(HAlign_Center);PlaceholderSlot->SetVerticalAlignment(VAlign_Center);
    Picture->SetVisibility(ESlateVisibility::Hidden);
    if(Proxy->CardIndex<9)
    {
        auto* Shortcut=Text(FString::FromInt(Proxy->CardIndex+1),12,true);
        Shortcut->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        Preview->AddChildToOverlay(Shortcut)->SetHorizontalAlignment(HAlign_Left);
    }
    auto* PictureSlot=Column->AddChildToVerticalBox(IconBox);
    PictureSlot->SetHorizontalAlignment(HAlign_Center);PictureSlot->SetVerticalAlignment(VAlign_Center);
    // Parenthesized operation/size details remain in the full tooltip title.
    FString ShortCaption=Entry.Caption;int32 DetailStart=INDEX_NONE;
    if(ShortCaption.FindChar(TEXT('（'),DetailStart)&&DetailStart>0)ShortCaption.LeftInline(DetailStart);
    ShortCaption.ReplaceInline(TEXT("\r"),TEXT(" "));ShortCaption.ReplaceInline(TEXT("\n"),TEXT(" "));
    auto* Label=Text(ShortCaption.TrimStartAndEnd(),14);Label->SetJustification(ETextJustify::Center);
    // Explicit full-width wrapping avoids AutoWrap's narrow desired size under a centered slot.
    Label->SetAutoWrapText(false);Label->SetWrapTextAt(GridNameWidth/Scale);
    auto* LabelBox=WidgetTree->ConstructWidget<USizeBox>();
    LabelBox->SetWidthOverride(GridNameWidth/Scale);LabelBox->SetMinDesiredHeight(44/Scale);LabelBox->SetContent(Label);
    if(auto* ContentSlot=Cast<USizeBoxSlot>(Label->Slot))
    {ContentSlot->SetHorizontalAlignment(HAlign_Fill);ContentSlot->SetVerticalAlignment(VAlign_Top);}
    auto* LabelSlot=Column->AddChildToVerticalBox(LabelBox);
    LabelSlot->SetHorizontalAlignment(HAlign_Fill);
    LabelSlot->SetPadding(FMargin(GridNameInset/Scale,4/Scale,GridNameInset/Scale,0));
    Cards.Add({Proxy->CardId,Entry.bComponent,Proxy->ShapeMode,bChild,Request.Key,Request,Button,SurfaceCard,Picture,Box,IconBox,true,Placeholder});
    VisibleCards.Add(Entry);
    if(auto* WrapSlot=Grid->AddChildToWrapBox(Button))
    {WrapSlot->SetHorizontalAlignment(HAlign_Center);WrapSlot->SetVerticalAlignment(VAlign_Top);}
}

void UVoxelBuildWidget::AddMaterialRow(const FVoxelBuildPanelCard& Entry)
{
    const float Scale=ColdSteelUI::PixelScale(this);
    const bool bExpanded=ExpandedMaterials.Contains(Entry.Id);
    auto* RowSurface=WidgetTree->ConstructWidget<UBorder>();
    RowSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale));
    RowSurface->SetPadding(FMargin(4/Scale));
    auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();RowSurface->SetContent(Row);
    auto* Proxy=NewObject<UVoxelBuildCardProxy>(this);
    Proxy->CardId=Entry.Id;Proxy->bComponentCard=false;Proxy->Panel=this;Proxy->CardIndex=Cards.Num();
    CardProxies.Add(Proxy);
    // Pick button and 其他构造 button are siblings: expanding a material never also selects it.
    auto* Button=WidgetTree->ConstructWidget<UButton>();
    Button->SetStyle(FButtonStyle()
        .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
        .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale))
        .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale)));
    Button->OnClicked.AddDynamic(Proxy,&UVoxelBuildCardProxy::Clicked);
    Button->OnHovered.AddDynamic(Proxy,&UVoxelBuildCardProxy::Hovered);
    Button->OnUnhovered.AddDynamic(Proxy,&UVoxelBuildCardProxy::Unhovered);
    auto* Size=WidgetTree->ConstructWidget<USizeBox>();
    Size->SetHeightOverride((CardHeight-8.f)/Scale);Button->SetContent(Size);
    auto* Line=WidgetTree->ConstructWidget<UHorizontalBox>();Size->SetContent(Line);
    if(Proxy->CardIndex<9)
    {
        auto* Shortcut=Text(FString::FromInt(Proxy->CardIndex+1),12,true);
        Shortcut->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        auto* ShortcutSlot=Line->AddChildToHorizontalBox(Shortcut);
        ShortcutSlot->SetVerticalAlignment(VAlign_Center);ShortcutSlot->SetPadding(FMargin(0,0,8/Scale,0));
    }
    // 材质行也带缩略图：用该材质自己的体素方块网格，和「其他构造」的卡片同一套取景。
    // 注意：这里只往 Line 里插图标，行本身的挂载与 FCard 登记一律走函数末尾的同一条路径，
    // 否则会出现"材质行变空行"（2026-09-16 的一次回退，就是因为在这里提前 return）。
    FString IconKey;UImage* Picture=nullptr;USizeBox* IconBox=nullptr;
    FVoxelBuildIconRequest IconRequest;
    if(!Entry.IconMesh.IsNull())
    {
        IconRequest.Key=UVoxelBuildIcons::KeyForShape(Entry.Id,-1);
        IconRequest.Mesh=Entry.IconMesh;IconRequest.Surface=Entry.IconSurface;
        IconRequest.Cells.Add(FIntVector(0,0,0));
        IconRequest.Key=UVoxelBuildIcons::ContentKey(IconRequest);
        if(bDrawerOpen)if(auto* Icons=IconsFor())Icons->Request(IconRequest);
        IconKey=IconRequest.Key;
        IconBox=WidgetTree->ConstructWidget<USizeBox>();
        IconBox->SetWidthOverride(MaterialThumbPixels/Scale);IconBox->SetHeightOverride(MaterialThumbPixels/Scale);
        Picture=WidgetTree->ConstructWidget<UImage>();
        Picture->SetVisibility(ESlateVisibility::HitTestInvisible);
        Picture->SetDesiredSizeOverride(FVector2D(256.f,256.f));
        auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();
        Fit->SetStretch(EStretch::ScaleToFit);Fit->SetContent(Picture);
        auto* FitSlot=Cast<UScaleBoxSlot>(Picture->Slot);
        FitSlot->SetHorizontalAlignment(HAlign_Center);FitSlot->SetVerticalAlignment(VAlign_Center);
        IconBox->SetContent(Fit);
        auto* IconSlot=Line->AddChildToHorizontalBox(IconBox);
        IconSlot->SetVerticalAlignment(VAlign_Center);IconSlot->SetPadding(FMargin(0,0,8/Scale,0));
    }
    auto* Caption=Text(Entry.Caption,14,false,false);
    auto* CaptionSlot=Line->AddChildToHorizontalBox(Caption);
    CaptionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CaptionSlot->SetVerticalAlignment(VAlign_Center);
    auto* Detail=Text(Entry.Detail,12,true);Detail->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Line->AddChildToHorizontalBox(Detail)->SetVerticalAlignment(VAlign_Center);
    auto* MainSlot=Row->AddChildToHorizontalBox(Button);
    MainSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));MainSlot->SetVerticalAlignment(VAlign_Center);
    if(Entry.bExpandable)
    {
        auto* DisclosureSlot=Row->AddChildToHorizontalBox(DisclosureButton(Entry.Id,bExpanded));
        DisclosureSlot->SetVerticalAlignment(VAlign_Center);
        DisclosureSlot->SetPadding(FMargin(6/Scale,0,0,0));
    }
    // IconKey/Picture/IconBox 在没图标时是空的，RefreshIcons 会跳过它们。
    // 材质行是行式卡片：DPI 重排只重算行高／28px 缩略图，不套网格卡尺寸（bGridCard=false）。
    Cards.Add({Entry.Id,false,INDEX_NONE,false,IconKey,IconRequest,Button,RowSurface,Picture,Size,IconBox,false});
    VisibleCards.Add(Entry);
    CardList->AddChildToVerticalBox(RowSurface)->SetPadding(FMargin(0,0,0,CardGap/Scale));
}

void UVoxelBuildWidget::RebuildCards()
{
    if(!CardList)return;
    HideTooltip(true);
    const float Scale=ColdSteelUI::PixelScale(this);
    CardList->ClearChildren();Cards.Reset();CardProxies.Reset();VisibleCards.Reset();Grids.Reset();
    // 旧卡片随 ClearChildren 脱离控件树；只留下仍在树上的标签，避免 Labels 每次重建都堆积死引用。
    Labels.RemoveAll([this](const FLabel& Label)
    {
        UWidget* Widget=Label.Widget.Get();
        while(Widget&&Widget!=WidgetTree->RootWidget)Widget=Widget->GetParent();
        return !Widget;
    });
    // 卡片重来一遍：缩略图键集合跟着换，旧键失去"正在显示"的保护后随淘汰回收。
    bIconPinsDirty=true;
    if(!bComponentCategory)
    {
        if(MaterialCards.IsEmpty())
        {
            auto* Empty=Text(TEXT("暂无可用材质"),12);
            Empty->SetColorAndOpacity(ColdSteelUI::TextTertiary);
            CardList->AddChildToVerticalBox(Empty)->SetPadding(FMargin(2/Scale,6/Scale));
            return;
        }
        for(const FVoxelBuildPanelCard& Material:MaterialCards)
        {
            AddMaterialRow(Material);
            if(!ExpandedMaterials.Contains(Material.Id))continue;
            // 其他构造 = the shared voxel construction shapes plus this material's own components,
            // all as identical cards that wrap once the row is full.
            auto* Grid=WidgetTree->ConstructWidget<UWrapBox>();
            CardList->AddChildToVerticalBox(Grid);
            ConfigureBuildGrid(Grid,DrawerWidth,Scale,true);
            Grids.Add(Grid);
            for(const FVoxelBuildPanelCard& Shape:ShapeCards)AddGridCard(Grid,Shape,Material.Id,true,&Material);
            for(const FVoxelBuildPanelCard& Entry:ComponentCards)
                if(Entry.MaterialId==Material.Id)AddGridCard(Grid,Entry,Material.Id,true,nullptr);
        }
        RefreshIcons();
        return;
    }
    // 「其他」分类只列**未归类**的构件（调色板 Material 留空）；归到某栏材质的构件只在该材质的
    // 「其他构造」里出现，同一个门不会在两处重复（2026-09-17 用户要求）。
    TArray<const FVoxelBuildPanelCard*> Unclassified;
    for(const FVoxelBuildPanelCard& Entry:ComponentCards)
        if(Entry.MaterialId.IsNone())Unclassified.Add(&Entry);
    if(Unclassified.IsEmpty())
    {
        auto* Empty=Text(TEXT("暂无其他构件 · 已分类构件可在对应材质的「其他构造」中选择"),14);
        Empty->SetAutoWrapText(true);
        Empty->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        CardList->AddChildToVerticalBox(Empty)->SetPadding(FMargin(2/Scale,6/Scale));
        return;
    }
    auto* Grid=WidgetTree->ConstructWidget<UWrapBox>();
    CardList->AddChildToVerticalBox(Grid);
    ConfigureBuildGrid(Grid,DrawerWidth,Scale,false);
    Grids.Add(Grid);
    for(const FVoxelBuildPanelCard* Entry:Unclassified)AddGridCard(Grid,*Entry,NAME_None,false,nullptr);
    RefreshIcons();
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
    if(Risk)
    {
        // 85% warns, 100% means a joint is breaking: same semantic colours as the rest of the HUD.
        const bool bDanger=StructureRisk>=1.f;
        const bool bWarn=StructureRisk>=.85f;
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
    const FString SelectionText=FString::Printf(TEXT("%s\n%s\n%s"),*Headline,*Brush,bSnapEnabled?TEXT("体素吸附已开启 · F 自由放置"):TEXT("自由位置 · F 开启体素吸附"));
    const FString Signature=SelectionText+Message+(bValid?TEXT("1"):TEXT("0"));
    if(Signature!=LastState)
    {
        LastState=Signature;
        Selection->SetText(FText::FromString(Brush));
        Status->SetText(FText::FromString(Headline));
        Status->SetColorAndOpacity(bValid?ColdSteelUI::TextPrimary:ColdSteelUI::Warning);
        const FString Snap=bSnapEnabled?TEXT("体素吸附已开启 · F 自由放置"):TEXT("自由位置 · F 开启体素吸附");
        Structure->SetText(FText::FromString(Snap+TEXT("\n")+Message));
    }
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
