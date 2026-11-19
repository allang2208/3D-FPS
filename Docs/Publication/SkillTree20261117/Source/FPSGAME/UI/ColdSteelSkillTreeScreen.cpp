#include "ColdSteelSkillTreeScreen.h"
#include "ColdSteelSkillPage.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelQuickBarTypes.h"
#include "ColdSteelMagicQuickCast.h"
#include "ColdSteelMagicWheel.h"
#include "ColdSteelQuickSlot.h"
#include "ColdSteelProgressNotification.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"


TSharedRef<SWidget> UColdSteelSkillTreeScreen::RebuildWidget()
{ using namespace ColdSteelUI;
    Model = GetGameInstance() ? GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    SetIsFocusable(true);
    TreeStyle.Initialize();
    SlotBrush = RoundedBrush(Content, 7, Border, 1);
    KeyChip = RoundedBrush(Gray(200, 9), 5, Gray(222, 26), 1);
    KeyChipEmpty = RoundedBrush(FLinearColor::Transparent, 5, Gray(222, 18), 1);
    KeyChipOn = RoundedBrush(FLinearColor(HUDGold.R, HUDGold.G, HUDGold.B, .18f), 5, HUDGoldLight, 1.2f);
    GoldDot = RoundedBrush(HUDGoldLight, 3, FLinearColor::Transparent, 0);
    SAssignNew(TreeCanvas, SColdSteelSkillTreeCanvas).OnCardClicked_Lambda([this](FName Id) { Select(Id); });
    SAssignNew(SpecCanvas, SColdSteelSkillTreeCanvas).bFitWidth(false).bPannable(false).OnCardClicked_Lambda([this](FName Id) { SelectSpecNode(Id); });
    Relayout();
    if(!Notices) Notices = CreateWidget<UColdSteelProgressNotification>(GetOwningPlayer());
    if(StripSlots.IsEmpty() && HUD.IsValid())
        for(int32 I = ColdSteelQuickBar::ItemOffset; I < ColdSteelQuickBar::Count; ++I)   // number keys 1-0 only
        { auto* QuickSlot = CreateWidget<UColdSteelQuickSlot>(GetOwningPlayer()); QuickSlot->Configure(HUD.Get(), I); StripSlots.Add(QuickSlot); }
    if(!DetailPage) { DetailPage = CreateWidget<UColdSteelSkillPage>(GetOwningPlayer()); if(DetailPage && HUD.IsValid()) DetailPage->SetHUD(HUD.Get()); }
    if(!WheelConfig && HUD.IsValid()) { WheelConfig = CreateWidget<UColdSteelMagicWheel>(GetOwningPlayer()); WheelConfig->Configure(HUD.Get()); }
    WheelPanel.Reset();
    auto Main = SNew(SVerticalBox)
        + SVerticalBox::Slot().FillHeight(1)[SNew(SOverlay)
            + SOverlay::Slot()[SAssignNew(TreePage, SBox)[SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[BuildLegend()]
                + SVerticalBox::Slot().FillHeight(1)[TreeCanvas.ToSharedRef()]]]
            + SOverlay::Slot()[SAssignNew(SpecPage, SBox).Visibility(EVisibility::Collapsed)[BuildSpecPage()]]]
        + SVerticalBox::Slot().AutoHeight()[BuildQuickStrip()];
    SAssignNew(DetailHost, SBox);
    // Notices already convert their own pixel scale and remain outside the common frame.
    return SNew(SOverlay)
        + SOverlay::Slot()[ColdSteelTreePanel::Frame(this, TreeStyle, BuildHeader(), Main, DetailHost.ToSharedRef())]
        + SOverlay::Slot()[Notices ? Notices->TakeWidget() : SNullWidget::NullWidget];
}

void UColdSteelSkillTreeScreen::NativeConstruct()
{ using namespace ColdSteelUI;
    Super::NativeConstruct();
    if(Model) ChangedHandle = Model->OnChanged.AddUObject(this, &ThisClass::RefreshAll);
    RefreshAll();
}
void UColdSteelSkillTreeScreen::NativeDestruct()
{ using namespace ColdSteelUI;
    if(Model) Model->OnChanged.Remove(ChangedHandle);
    Super::NativeDestruct();
}
void UColdSteelSkillTreeScreen::NativeTick(const FGeometry& Geometry, float Delta)
{ using namespace ColdSteelUI;
    Super::NativeTick(Geometry, Delta);
    // Text wrap widths and the embedded skill page are built for one column width; rebuild after a resize.
    if(DetailHost && !bWheelOpen && !FMath::IsNearlyEqual(DetailWidth(), BuiltDetailWidth, .5f)) ShowDetail();
}
void UColdSteelSkillTreeScreen::ReleaseSlateResources(bool bReleaseChildren)
{ using namespace ColdSteelUI;
    Super::ReleaseSlateResources(bReleaseChildren);
    TreeCanvas.Reset(); SpecCanvas.Reset(); TreePage.Reset(); SpecPage.Reset(); DetailHost.Reset(); SpecPreview.Reset(); WheelPanel.Reset();
    if(bReleaseChildren && Notices) static_cast<UVisual*>(Notices.Get())->ReleaseSlateResources(true);
    if(bReleaseChildren && DetailPage) static_cast<UVisual*>(DetailPage.Get())->ReleaseSlateResources(true);
}
FReply UColdSteelSkillTreeScreen::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{ using namespace ColdSteelUI;
    const FKey Key = Event.GetKey();
    if(Key == EKeys::Escape && bWheelOpen) { ToggleWheel(false); return FReply::Handled(); }
    if(Key == EKeys::Escape && bSpec) { CloseSpec(); return FReply::Handled(); }
    if(Key == EKeys::Escape || Key == EKeys::P || Key == EKeys::Tab) { Close(); return FReply::Handled(); }
    return Super::NativeOnKeyDown(Geometry, Event);
}
void UColdSteelSkillTreeScreen::SetHUD(UColdSteelHUDWidget* Owner) { using namespace ColdSteelUI; HUD = Owner; }
void UColdSteelSkillTreeScreen::Close() { using namespace ColdSteelUI; if(auto* Owner = HUD.Get()) Owner->CloseSkillTree(); else RemoveFromParent(); }

void UColdSteelSkillTreeScreen::Select(FName Skill)
{ using namespace ColdSteelUI;
    if(!ColdSteelSkillTree::InTree(Skill)) return;
    if(Selected != Skill) ActionError.Reset();
    Selected = Skill;
    if(TreeCanvas && !TreeCanvas->GetLayout().Card(Skill)) { Group = NAME_None; Relayout(); }
    if(TreeCanvas) TreeCanvas->Reveal(Skill);
    RefreshAll();
}
void UColdSteelSkillTreeScreen::Relayout()
{ using namespace ColdSteelUI;
    if(!TreeCanvas) return;
    ColdSteelSkillTreeLayout::FConfig Config;
    TreeCanvas->SetLayout(ColdSteelSkillTreeLayout::Build(TreeRows(), Config));
    RefreshAll();
}
void UColdSteelSkillTreeScreen::RefreshAll()
{ using namespace ColdSteelUI;
    if(TreeCanvas) TreeCanvas->SetSource(TreeSource());
    if(SpecCanvas && bSpec) SpecCanvas->SetSource(SpecSource());
    if(SpecPreview && bSpec) SpecPreview->SetContent(BuildSpecPreview());
    // The wheel panel is built once; its UMG wheel repaints itself from the model.
    if(DetailHost && !bWheelOpen) ShowDetail();
    for(const auto& QuickSlot : StripSlots) if(QuickSlot) QuickSlot->Refresh();
}
void UColdSteelSkillTreeScreen::OpenSpec(FName Skill)
{ using namespace ColdSteelUI;
    const auto* Spec = ColdSteelSkillTree::FindSpec(Skill);
    if(!Spec || Spec->Nodes.IsEmpty() || !SpecCanvas) return;
    bSpec = true; bWheelOpen = false; SpecSkill = Skill; SpecNode = Spec->Nodes[0].Id; ActionError.Reset();
    ColdSteelSkillTreeLayout::FConfig Config; Config.W = 196; Config.Gap = 112; Config.OX = 132; Config.OY = 56; Config.Columns = Spec->Columns.Num();
    const auto Layout = ColdSteelSkillTreeLayout::Build(SpecRows(Skill), Config);
    SpecCanvas->SetLayout(Layout);
    if(TreePage) TreePage->SetVisibility(EVisibility::Collapsed);
    if(SpecPage) SpecPage->SetVisibility(EVisibility::Visible);
    RefreshAll();
}
void UColdSteelSkillTreeScreen::CloseSpec()
{ using namespace ColdSteelUI;
    bSpec = false; ActionError.Reset();
    if(TreePage) TreePage->SetVisibility(EVisibility::Visible);
    if(SpecPage) SpecPage->SetVisibility(EVisibility::Collapsed);
    RefreshAll();
}
void UColdSteelSkillTreeScreen::SelectSpecNode(FName Node) { using namespace ColdSteelUI; if(SpecNode != Node) ActionError.Reset(); SpecNode = Node; RefreshAll(); }

const FSlateBrush* UColdSteelSkillTreeScreen::Icon(const FString& Path)
{ using namespace ColdSteelUI;
    if(Path.IsEmpty()) return nullptr;
    if(const TSharedPtr<FSlateBrush>* Found = IconBrushes.Find(Path)) return Found->Get();
    UTexture2D* Texture = FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir() / TEXT("ColdSteelData") / Path);
    TSharedPtr<FSlateBrush> Brush = MakeShared<FSlateBrush>();
    if(Texture) { IconTextures.Add(Path, Texture); Brush->SetResourceObject(Texture); Brush->DrawAs = ESlateBrushDrawType::Image; Brush->ImageSize = FVector2D(64); }
    else Brush->DrawAs = ESlateBrushDrawType::NoDrawType;
    IconBrushes.Add(Path, Brush);
    return Brush.Get();
}

TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildHeader()
{ using namespace ColdSteelUI;
    const TArray<ColdSteelTreePanel::FTab> Items = {{NAME_None, TEXT("全部")}, {TEXT("magic"), TEXT("魔法")},
        {TEXT("ranged"), TEXT("远程")}, {TEXT("melee"), TEXT("近战")}, {TEXT("general"), TEXT("通用")}};
    auto TabRow = ColdSteelTreePanel::Tabs(TreeStyle, Items,
        TAttribute<FName>::CreateLambda([this] { return Group; }), TAttribute<bool>::CreateLambda([this] { return !bSpec; }),
        [this](FName G) { Group = G; if(bSpec) CloseSpec(); Relayout(); });
    ColdSteelTreePanel::FHeader Header;
    Header.Title = TEXT("技能"); Header.SearchHint = TEXT("搜索技能"); Header.CloseKey = TEXT("P");
    Header.Breadcrumb = TAttribute<FText>::CreateLambda([this] { return FText::FromString(bSpec ? TEXT("技能树  /  ") + SkillName(SpecSkill) + TEXT("专精") : TEXT("技能树")); });
    Header.Summary = TAttribute<FText>::CreateLambda([this]
    {
        int32 Learned = 0, Ready = 0, Total = 0;
        if(Model) for(const auto& N : ColdSteelSkillTree::Get().Nodes)
        { ++Total; if(Model->IsSkillLearned(N.Id)) ++Learned; else if(Model->CanLearnSkill(N.Id)) ++Ready; }
        return FText::FromString(FString::Printf(TEXT("角色等级 %d　·　已习得 %d / %d　·　可免费习得 %d"), Model ? Model->ProfileView().Level : 1, Learned, Total, Ready));
    });
    Header.OnSearch = [this](const FText& T) { Query = T.ToString().TrimStartAndEnd(); RefreshAll(); };
    Header.OnClose = [this] { Close(); };
    auto Wheel = SNew(SButton).ButtonStyle(&TreeStyle.Muted).ContentPadding(FMargin(12, 0)).OnClicked_Lambda([this] { ToggleWheel(!bWheelOpen); return FReply::Handled(); })
        [SNew(SBox).HeightOverride(ActionHeight).VAlign(VAlign_Center)[SNew(STextBlock).Text(FText::FromString(TEXT("魔法轮盘")))
            .Font_Lambda([this] { return TextFont(14 * .75f, bWheelOpen); }).ColorAndOpacity_Lambda([this] { return FSlateColor(bWheelOpen ? HUDGoldLight : TextPrimary); })]];
    return ColdSteelTreePanel::Header(TreeStyle, Header, TabRow, Wheel);
}

TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildLegend()
{
    return ColdSteelTreePanel::Legend(TreeStyle, TreeCanvas, TEXT("技能"));
}

TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildSpecPage()
{ using namespace ColdSteelUI;
    auto Points = [this]
    {
        if(!Model || SpecSkill.IsNone()) return FText::GetEmpty();
        const auto& P = Model->ProfileView();
        return FText::FromString(FString::Printf(TEXT("可用专精点 %d　·　已投入 %d / 获得 %d"), Model->SpecPointsFree(SpecSkill),
            ColdSteelSkillTree::SpecPointsSpent(P, SpecSkill), ColdSteelSkillTree::SpecPointsEarned(P, SpecSkill)));
    };
    return SNew(SScrollBox)
    + SScrollBox::Slot()
    [
        SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()
        [
            SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gray(18, 184)).Padding(FMargin(18, 10))
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 18, 0)
                    [SNew(SButton).ButtonStyle(&TreeStyle.Muted).ContentPadding(FMargin(12, 0)).OnClicked_Lambda([this] { CloseSpec(); return FReply::Handled(); })
                        [SNew(SBox).HeightOverride(ActionHeight).VAlign(VAlign_Center)[Label(TEXT("返回技能树"), 14, TextPrimary)]]]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)
                    [SNew(SBox).WidthOverride(44).HeightOverride(44)[SNew(SImage).Image_Lambda([this] { return Icon(Model ? Model->DevelopmentSkillDefinition(SpecSkill).Icon : FString()); })]]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this] { return FText::FromString(SkillName(SpecSkill) + TEXT(" · 专精")); }).Font(TextFont(18 * .75f, true)).ColorAndOpacity(TextPrimary)]
                        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Font(TextFont(12 * .75f)).ColorAndOpacity(TextTertiary).Text_Lambda([this]
                        {
                            const auto* Spec = ColdSteelSkillTree::FindSpec(SpecSkill);
                            return FText::FromString(FString::Printf(TEXT("%s Lv %d · 每级获得 1 点，点满全部需要 %d 点 · 重置：F6 开发面板 · 基本调参"),
                                *SkillName(SpecSkill), Model ? ColdSteelSkillTree::SkillLevel(Model->ProfileView(), SpecSkill) : 0, Spec ? Spec->TotalCost() : 0));
                        })]]
                + SHorizontalBox::Slot().FillWidth(1)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(STextBlock).Text_Lambda(Points).Font(TextFont(14 * .75f, true)).ColorAndOpacity(HUDGoldLight)]
            ]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 8)[SpecCanvas.ToSharedRef()]
        + SVerticalBox::Slot().AutoHeight().Padding(FMargin(18, 0, 18, 20))[SAssignNew(SpecPreview, SBox)]
    ];
}

// ---- quickbar strip + staff magic wheel (2026-11-16, user picked layout A without a detail tab) ----
TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildQuickStrip()
{ using namespace ColdSteelUI;
    const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");
    auto Row = SNew(SHorizontalBox);
    Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 14, 0)[Label(TEXT("快捷栏"), 12, HUDGold, true)];
    for(int32 I = 0; I < StripSlots.Num(); ++I)
    {
        // UColdSteelQuickSlot sizes itself in UMG units (px / PixelScale); undo this screen's raw-pixel scaler.
        Row->AddSlot().AutoWidth().Padding(3, 0)
        [
            SNew(SBorder).BorderImage(&SlotBrush).Padding(0)
            [SNew(SBox).WidthOverride(52).HeightOverride(52)
                [SNew(SDPIScaler).DPIScale_Lambda([this] { return FMath::Max(.1f, PixelScale(this)); })[StripSlots[I]->TakeWidget()]]]
        ];
    }
    Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(16, 0, 0, 0)[Label(TEXT("拖入卡片绑定 · 格间拖动交换 · 拖出或右键清除"), 12, TextTertiary)];
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(1)[SNew(SBorder).BorderImage(White).BorderBackgroundColor(Border)]]
        + SVerticalBox::Slot().AutoHeight()[SNew(SBorder).BorderImage(White).BorderBackgroundColor(Gray(18, 235)).Padding(FMargin(16, 8)).HAlign(HAlign_Center)[Row]];
}

TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildWheelPanel()
{ using namespace ColdSteelUI;
    const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");
    auto Used = [this]
    {
        int32 N = 0; if(Model) for(FName Skill : Model->MagicBindings()) N += Skill.IsNone() ? 0 : 1;
        return FText::FromString(FString::Printf(TEXT("法杖专用 · 已登记 %d / %d"), N, ColdSteelMagicQuickCast::Count));
    };
    auto Help = [this](const TCHAR* Key, const TCHAR* Text)
    {
        return SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 10, 0)[SNew(SBox).WidthOverride(52)[Label(Key, 12, HUDGold, true)]]
            + SHorizontalBox::Slot().FillWidth(1)[Label(Text, 12, TextSecondary, false, true)];
    };
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(FMargin(28, 22, 28, 8))
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1)[SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[Label(TEXT("魔法轮盘"), 20, TextPrimary, true)]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 0)[SNew(STextBlock).Text_Lambda(Used).Font(TextFont(12 * .75f)).ColorAndOpacity(HUDGold)]]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                [SNew(SButton).ButtonStyle(&TreeStyle.Muted).ContentPadding(FMargin(12, 0)).OnClicked_Lambda([this] { ToggleWheel(false); return FReply::Handled(); })
                    [SNew(SBox).HeightOverride(32).VAlign(VAlign_Center)[Label(TEXT("收起"), 14, TextPrimary)]]]
        ]
        // The configuration wheel paints its own sectors, centre and footer hints (ColdSteelMagicWheel.cpp).
        + SVerticalBox::Slot().FillHeight(1).Padding(FMargin(10, 0)).VAlign(VAlign_Top)
            [SNew(SBox).HeightOverride_Lambda([this] { return FOptionalSize(FMath::Clamp(DetailWidth() - 140, 460.f, 620.f)); })[SNew(SDPIScaler).DPIScale_Lambda([this] { return FMath::Max(.1f, PixelScale(this)); })
                [WheelConfig ? WheelConfig->TakeWidget() : SNullWidget::NullWidget]]]
        + SVerticalBox::Slot().AutoHeight().Padding(FMargin(28, 0))[SNew(SBox).HeightOverride(1)[SNew(SBorder).BorderImage(White).BorderBackgroundColor(Border)]]
        + SVerticalBox::Slot().AutoHeight().Padding(FMargin(28, 14, 28, 0))[Help(TEXT("登记"), TEXT("把已习得的魔法卡片拖进扇区，同一魔法再拖会移位或交换"))]
        + SVerticalBox::Slot().AutoHeight().Padding(FMargin(28, 10, 28, 0))[Help(TEXT("战斗中"), TEXT("装备法杖，长按 R 打开轮盘，松开选择；左键施放当前魔法"))]
        + SVerticalBox::Slot().AutoHeight().Padding(FMargin(28, 12, 28, 22))
            [Label(TEXT("轮盘只放魔法；武技、被动和物品请用快捷栏。两者互不影响，同一魔法可以同时在两处。"), 12, TextTertiary, false, true)];
}

// Detach first: the embedded skill page widget must leave its old container before it is placed again.
void UColdSteelSkillTreeScreen::ShowDetail()
{ using namespace ColdSteelUI;
    if(!DetailHost) return;
    BuiltDetailWidth = DetailWidth();
    DetailHost->SetContent(SNullWidget::NullWidget);
    DetailHost->SetContent(bSpec ? BuildSpecDetail() : BuildSkillDetail());
}

void UColdSteelSkillTreeScreen::ToggleWheel(bool bOpen)
{ using namespace ColdSteelUI;
    if(bOpen && bSpec) CloseSpec();
    bWheelOpen = bOpen;
    if(!DetailHost) return;
    if(bOpen)
    {
        if(!WheelPanel) WheelPanel = BuildWheelPanel();
        DetailHost->SetContent(WheelPanel.ToSharedRef());
    }
    else ShowDetail();
}

// Learned active cards drag to the quickbar strip or the wheel through the HUD's quick drag (same
// operation, visual and drop rules as the old skill page). Other cards and empty canvas keep panning.
FReply UColdSteelSkillTreeScreen::NativeOnPreviewMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event)
{ using namespace ColdSteelUI;
    PendingDrag = NAME_None;
    const FVector2D At = Event.GetScreenSpacePosition();
    if(Event.GetEffectingButton() == EKeys::RightMouseButton && Model)
        for(int32 I = 0; I < StripSlots.Num(); ++I)
            if(StripSlots[I] && StripSlots[I]->GetCachedGeometry().IsUnderLocation(At))
            { const int32 Index = ColdSteelQuickBar::ItemOffset + I; if(!Model->QuickBinding(Index).IsEmpty()) Model->ClearQuickBinding(Index); return FReply::Handled(); }
    if(Event.GetEffectingButton() == EKeys::LeftMouseButton && !bSpec && Model && TreeCanvas && TreeCanvas->GetTickSpaceGeometry().IsUnderLocation(At))
    {
        const FName Id = TreeCanvas->CardAtScreen(At);
        if(!Id.IsNone() && Model->CanBindQuickSkill(Id))
        { PendingDrag = Id; return FReply::Handled().CaptureMouse(TakeWidget()).DetectDrag(TakeWidget(), EKeys::LeftMouseButton); }
    }
    return Super::NativeOnPreviewMouseButtonDown(Geometry, Event);
}
FReply UColdSteelSkillTreeScreen::NativeOnMouseButtonUp(const FGeometry& Geometry, const FPointerEvent& Event)
{ using namespace ColdSteelUI;
    if(!PendingDrag.IsNone() && Event.GetEffectingButton() == EKeys::LeftMouseButton)
    { const FName Id = PendingDrag; PendingDrag = NAME_None; Select(Id); return FReply::Handled().ReleaseMouseCapture(); }
    return Super::NativeOnMouseButtonUp(Geometry, Event);
}
// Same rule as the HUD hotbar (ColdSteelHotbarDrag.cpp NativeOnDrop): a quick-drag released outside every
// slot clears its source slot (card drags have no source and just end); over the open wheel panel it cancels.
bool UColdSteelSkillTreeScreen::NativeOnDrop(const FGeometry& Geometry, const FDragDropEvent& Event, UDragDropOperation* Operation)
{ using namespace ColdSteelUI;
    auto* Quick = Cast<UColdSteelQuickDrag>(Operation);
    if(!Quick || !HUD.IsValid()) return Super::NativeOnDrop(Geometry, Event, Operation);
    if(bWheelOpen && DetailHost && DetailHost->GetTickSpaceGeometry().IsUnderLocation(Event.GetScreenSpacePosition()))
        return HUD->DropMagicDrag(Quick, INDEX_NONE);
    return HUD->DropQuickDrag(Quick, INDEX_NONE);
}
void UColdSteelSkillTreeScreen::NativeOnDragDetected(const FGeometry& Geometry, const FPointerEvent& Event, UDragDropOperation*& Out)
{ using namespace ColdSteelUI;
    const FName Id = PendingDrag; PendingDrag = NAME_None;
    if(Id.IsNone() || !HUD.IsValid() || !Model) return;
    Out = HUD->StartQuickDrag(Id, INDEX_NONE, Icon(Model->DevelopmentSkillDefinition(Id).Icon), Event.GetScreenSpacePosition());
}
