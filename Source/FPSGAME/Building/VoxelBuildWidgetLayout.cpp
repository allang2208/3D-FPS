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
    // Keep build-card captions horizontal; the full name remains available in the tooltip.
    Label->SetAutoWrapText(false);Label->SetWrapTextAt(0);Label->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);Label->SetToolTipText(FText::FromString(Entry.Caption));
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
