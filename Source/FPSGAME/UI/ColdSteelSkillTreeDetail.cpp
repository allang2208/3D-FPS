// Right detail column of the skill tree screen (DetailWidth, 480–760 px): skill detail, specialization node detail, spec effect table.
#include "ColdSteelSkillTreeScreen.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "ColdSteelSkillPage.h"
#include "ColdSteelMagicQuickCast.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelScrollBar.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelQuickBarTypes.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/ElementalArrowTypes.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"


TSharedRef<SWidget> UColdSteelSkillTreeScreen::Label(const FString& Text, float Px, const FLinearColor& Color, bool bMedium, bool bWrap) const
{
    return ColdSteelTreePanel::Label(Text, Px, Color, bMedium, bWrap);
}
TSharedRef<SWidget> UColdSteelSkillTreeScreen::Section(const FString& Title, const FString& Count, TSharedRef<SWidget> Body) const
{
    return ColdSteelTreePanel::Section(Title, Count, Body);
}
TSharedRef<SWidget> UColdSteelSkillTreeScreen::Requirement(const ColdSteelSkillTree::FRequirement& R, bool bSpecPage)
{ using namespace ColdSteelUI; using namespace ColdSteelSkillTree;
    const FColdSteelProfile& P = Model->ProfileView();
    const bool bMet = bSpecPage ? SpecRequirementMet(P, SpecSkill, R) : RequirementMet(P, R);
    int32 Have = 0;
    switch(R.Kind)
    {
    case EReqKind::CharacterLevel: Have = P.Level; break;
    case EReqKind::PointsInvested: Have = SpecPointsSpent(P, SpecSkill); break;
    case EReqKind::AnyOf: for(FName Id : R.Skills) Have = FMath::Max(Have, bSpecPage ? SpecRank(P, SpecSkill, Id) : SkillLevel(P, Id)); break;
    default: Have = bSpecPage ? SpecRank(P, SpecSkill, R.Skills[0]) : SkillLevel(P, R.Skills[0]);
    }
    const FName Target = R.Kind == EReqKind::Skill ? R.Skills[0] : NAME_None;
    const FSlateBrush* Img = !bSpecPage && R.Skills.Num() ? Icon(Model->DevelopmentSkillDefinition(R.Skills[0]).Icon) : nullptr;
    FString Sub = R.Kind == EReqKind::CharacterLevel ? FString::Printf(TEXT("当前角色等级 %d"), P.Level)
        : R.Kind == EReqKind::PointsInvested ? FString::Printf(TEXT("当前已投入 %d 点"), Have)
        : Have > 0 ? (bSpecPage ? FString::Printf(TEXT("当前 %d 级"), Have) : FString::Printf(TEXT("当前 Lv %d"), Have)) : FString(bSpecPage ? TEXT("尚未投入") : TEXT("尚未习得"));
    if(R.bCrossBranch) Sub = TEXT("跨系前置 · ") + Sub;
    auto Row = SNew(SBorder).BorderImage(bMet ? &TreeStyle.RowMetBrush : &TreeStyle.RowBrush).Padding(FMargin(10, 7, 12, 7))
    [
        SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)[Label(bMet ? TEXT("√") : TEXT("×"), 14, bMet ? HUDGoldLight : TextTertiary, true)]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)
            [SNew(SBox).WidthOverride(28).HeightOverride(28).Visibility(Img ? EVisibility::HitTestInvisible : EVisibility::Collapsed)[SNew(SImage).Image(Img)]]
        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[Label(RequirementText(R, bSpecPage), 14, TextPrimary, false, true)]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 0)[Label(Sub, 12, TextTertiary)]]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0, 0, 0)
            [SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%d / %d"), Have, R.Level))).Font(NumberFont(14 * .75f, true)).ColorAndOpacity(bMet ? HUDGoldLight : TextSecondary)]
    ];
    if(Target.IsNone()) return Row;
    return SNew(SButton).ButtonStyle(&TreeStyle.Quiet).ContentPadding(0).OnClicked_Lambda([this, Target, bSpecPage] { if(bSpecPage) SelectSpecNode(Target); else Select(Target); return FReply::Handled(); })[Row];
}

float UColdSteelSkillTreeScreen::DetailWidth() const
{
    return ColdSteelTreePanel::DetailWidth(this);
}

TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildSkillDetail()
{ using namespace ColdSteelUI; using namespace ColdSteelSkillTree;
    if(!Model) return SNullWidget::NullWidget;
    const FNode* N = Get().Find(Selected); if(!N) return SNullWidget::NullWidget;
    const FColdSteelProfile& P = Model->ProfileView();
    const auto& D = Model->DevelopmentSkillDefinition(Selected);
    const SColdSteelSkillTreeCanvas::EStatus St = SkillStatus(Selected);
    const int32 Level = SkillLevel(P, Selected);
    int32 Met = 0; for(const auto& R : N->Requires) Met += RequirementMet(P, R) ? 1 : 0;
    const FBranch* B = Get().FindBranch(N->Branch);
    static const TCHAR* Tier[] = { TEXT("根基"), TEXT("初级 I"), TEXT("中级 II"), TEXT("高级 III"), TEXT("终极 IV") };
    static const TMap<FString, FString> Kinds = { { TEXT("magic"), TEXT("魔法") }, { TEXT("martial"), TEXT("武技") }, { TEXT("mastery"), TEXT("精通") }, { TEXT("general"), TEXT("通用") } };
    const bool bLearned = St == SColdSteelSkillTreeCanvas::EStatus::Learned || St == SColdSteelSkillTreeCanvas::EStatus::Maxed;
    const bool bTrainer = Selected==TEXT("holyLight")&&!bLearned;
    const FString StatusText = bTrainer ? TEXT("修女传授") : St == SColdSteelSkillTreeCanvas::EStatus::Locked ? TEXT("未解锁") : St == SColdSteelSkillTreeCanvas::EStatus::Available ? TEXT("可免费习得")
        : St == SColdSteelSkillTreeCanvas::EStatus::Maxed ? TEXT("已满级") : TEXT("已习得");
    const FRequirement* FirstUnmet = N->Requires.FindByPredicate([&](const ColdSteelSkillTree::FRequirement& R) { return !RequirementMet(P, R); });
    float Bar = 0; FString Value, Note;
    if(bLearned)
    {
        const int32 Need = ColdSteelSkills::ExperienceRequired(D, Level), Xp = P.Skills.Contains(Selected) ? P.Skills[Selected].Experience : 0;
        Bar = St == SColdSteelSkillTreeCanvas::EStatus::Maxed ? 1.f : Need > 0 ? float(Xp) / Need : 0.f;
        Value = FString::Printf(TEXT("Lv %d / %d"), Level, D.MaxLevel);
        Note = St == SColdSteelSkillTreeCanvas::EStatus::Maxed ? TEXT("已达到等级上限，停止积累修炼经验") : FString::Printf(TEXT("修炼经验 %d / %d"), Xp, Need);
    }
    else
    {
        Bar = N->Requires.Num() ? float(Met) / N->Requires.Num() : 1.f;
        Value = FString::Printf(TEXT("%d / %d 项条件"), Met, N->Requires.Num());
        Note = FirstUnmet ? RequirementText(*FirstUnmet, false) + TEXT("后可以免费习得") : TEXT("条件已满足，习得不消耗资源，从 Lv 1 开始修炼");
        if(bTrainer) Note=TEXT("角色达到 Lv15 后，前往教堂与修女交谈学习圣光");
    }
    // 2026-11-17 wide column (DetailWidth, 28 px gutters): head + description + state card, then the sections
    // in reading order — learned: 专精, 技能详情, 解锁条件 | 后续技能; not learned: 解锁条件 | 后续技能 first.
    const float Inner = DetailWidth() - 56 - 10; // gutters + room for the scroll bar
    const bool bTwoColumn = Inner >= 600;
    auto Body = SNew(SVerticalBox);
    Body->AddSlot().AutoHeight()[ColdSteelTreePanel::DetailHead(TreeStyle,
        SNew(SImage).Image(Icon(D.Icon)).ColorAndOpacity(St == SColdSteelSkillTreeCanvas::EStatus::Locked ? FLinearColor(.45f, .45f, .45f) : FLinearColor::White),
        FString::Printf(TEXT("%s · %s"), B ? *B->Name : TEXT(""), Tier[FMath::Clamp(N->Tier, 0, 4)]), D.Name,
        (N->bActive ? TEXT("主动") : TEXT("被动")) + Kinds.FindRef(N->Kind))];
    // what the skill does (rules and formulas stay on the old full page)
    if(!D.Description.IsEmpty())
        Body->AddSlot().AutoHeight().Padding(0, 18, 0, 0)[Label(D.Description, 14, TextSecondary, false, true)];
    Body->AddSlot().AutoHeight().Padding(0, 22, 0, 0)[ColdSteelTreePanel::Progress(TreeStyle, StatusText, Value, Note, Bar,
        bLearned ? HUDGoldLight : St == SColdSteelSkillTreeCanvas::EStatus::Available ? TextPrimary : TextSecondary,
        bLearned ? HUDGold : St == SColdSteelSkillTreeCanvas::EStatus::Available ? Accent : Gray(222, 90))];
    // requirements
    auto Reqs = SNew(SVerticalBox);
    if(N->Requires.IsEmpty()) Reqs->AddSlot().AutoHeight()[SNew(SBorder).BorderImage(&TreeStyle.RowMetBrush).Padding(FMargin(12, 9))
        [Label(N->Tier == 0 ? TEXT("根基技能，默认习得，所有路线共用") : TEXT("初级技能，没有前置条件，是本系的起点"), 14, TextSecondary, false, true)]];
    for(const auto& R : N->Requires) Reqs->AddSlot().AutoHeight().Padding(0, 0, 0, 6)[Requirement(R, false)];
    const TSharedRef<SWidget> ReqSection = Section(TEXT("解锁条件"), FString::Printf(TEXT("%d / %d"), Met, N->Requires.Num()), Reqs);
    // specialization entry
    TSharedPtr<SWidget> SpecSection;
    if(const FSpec* Spec = FindSpec(Selected))
    {
        FString Rows; for(const auto& R : Spec->Rows) Rows += (Rows.IsEmpty() ? TEXT("") : TEXT(" / ")) + R.Name;
        const FName Id = Selected;
        auto SpecBox = SNew(SVerticalBox) + SVerticalBox::Slot().AutoHeight()[
            SNew(SButton).ButtonStyle(&TreeStyle.Muted).IsEnabled(bLearned).ContentPadding(FMargin(12, 10)).OnClicked_Lambda([this, Id] { OpenSpec(Id); return FReply::Handled(); })
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)
                    [SNew(STextBlock).Text(FText::AsNumber(Model->SpecPointsFree(Id))).Font(NumberFont(20 * .75f, true)).ColorAndOpacity(HUDGoldLight)]
                + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight()[Label(FString::Printf(TEXT("打开%s专精"), *D.Name), 14, TextPrimary, true)]
                    + SVerticalBox::Slot().AutoHeight()[Label(FString::Printf(TEXT("可用点数 · 已投入 %d / 获得 %d · %s"), SpecPointsSpent(P, Id), SpecPointsEarned(P, Id), *Rows), 12, TextTertiary, false, true)]]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Label(TEXT("›"), 22, HUDGold)]]];
        if(Selected == TEXT("elementalArrow"))
            SpecBox->AddSlot().AutoHeight().Padding(0, 10, 0, 0)[Label(TEXT("火焰元素箭另按 50% 继承火球专精的爆破与灼烧效果。"), 12, TextTertiary, false, true)];
        SpecSection = Section(TEXT("专精"), TEXT("每级 1 点"), SpecBox);
    }
    // follow-up skills
    auto Kids = SNew(SVerticalBox); int32 KidCount = 0;
    for(const FNode& Other : Get().Nodes)
        for(const auto& R : Other.Requires)
            if((R.Kind == EReqKind::Skill || R.Kind == EReqKind::AnyOf) && R.Skills.Contains(Selected))
            {
                ++KidCount; const FName Kid = Other.Id; const auto KidStatus = SkillStatus(Kid);
                const auto& KD = Model->DevelopmentSkillDefinition(Kid);
                const FString Chip = KidStatus == SColdSteelSkillTreeCanvas::EStatus::Locked ? TEXT("未解锁") : KidStatus == SColdSteelSkillTreeCanvas::EStatus::Available ? TEXT("可免费习得") : TEXT("已习得");
                Kids->AddSlot().AutoHeight().Padding(0, 0, 0, 6)[SNew(SButton).ButtonStyle(&TreeStyle.Quiet).ContentPadding(0).OnClicked_Lambda([this, Kid] { Select(Kid); return FReply::Handled(); })
                    [SNew(SBorder).BorderImage(&TreeStyle.RowBrush).Padding(FMargin(10, 7, 12, 7))[SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)[SNew(SBox).WidthOverride(28).HeightOverride(28)[SNew(SImage).Image(Icon(KD.Icon))]]
                        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
                            + SVerticalBox::Slot().AutoHeight()[Label(KD.Name, 14, TextPrimary)]
                            + SVerticalBox::Slot().AutoHeight()[Label(FString::Printf(TEXT("需本技能 Lv%d%s"), R.Level, R.Kind == EReqKind::AnyOf ? TEXT("（任一）") : TEXT("")), 12, TextTertiary)]]
                        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBorder).BorderImage(&TreeStyle.ChipBrush).Padding(FMargin(8, 2))
                            [Label(Chip, 12, KidStatus == SColdSteelSkillTreeCanvas::EStatus::Locked ? TextTertiary : KidStatus == SColdSteelSkillTreeCanvas::EStatus::Available ? TextPrimary : HUDGoldLight)]]]]];
            }
    TSharedPtr<SWidget> KidSection;
    if(KidCount) KidSection = Section(TEXT("后续技能"), FString::Printf(TEXT("%d 项"), KidCount), Kids);

    auto AddSection = [&Body](const TSharedPtr<SWidget>& Widget) { if(Widget) Body->AddSlot().AutoHeight().Padding(0, 32, 0, 0)[Widget.ToSharedRef()]; };
    auto AddConditions = [&]
    {
        if(!bTwoColumn || !KidSection) { AddSection(ReqSection); AddSection(KidSection); return; }
        Body->AddSlot().AutoHeight().Padding(0, 32, 0, 0)[SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 12, 0)[ReqSection]
            + SHorizontalBox::Slot().FillWidth(1).Padding(12, 0, 0, 0)[KidSection.ToSharedRef()]];
    };
    // Restored per-skill values from the former skill page (2026-11-17): 技能收益 current / next level, growth
    // tables, 修炼方式. It lays out in UMG units, hence the nested scaler; -16 cancels its side padding.
    auto AddValues = [&]
    {
        if(!DetailPage) return;
        DetailPage->ShowEmbeddedDetail(Selected, Inner + 32);
        Body->AddSlot().AutoHeight().Padding(FMargin(-16, 32, -16, 0))
            [SNew(SDPIScaler).DPIScale_Lambda([this] { return FMath::Max(.1f, PixelScale(this)); })[DetailPage->TakeWidget()]];
    };
    if(bLearned) { AddSection(SpecSection); AddValues(); AddConditions(); }
    else { AddConditions(); AddSection(SpecSection); AddValues(); }

    // footer: free learn / jump to unmet / quickbar
    const FName Id = Selected;
    auto Button = [this](const FString& Caption, const FButtonStyle* Style, bool bEnabled, TFunction<void()> Action, const FLinearColor& Color)
    {
        return ColdSteelTreePanel::Action(Caption, Style, bEnabled, Action, Color, Style == &TreeStyle.Primary);
    };
    auto Actions = SNew(SHorizontalBox);
    FString Reason;
    if(bTrainer)
    {
        Actions->AddSlot().FillWidth(1)[Button(TEXT("前往教堂向修女学习"), &TreeStyle.Muted, false, [] {}, TextPrimary)];
        Reason=TEXT("圣光仅由修女传授；习得后可在此修炼与绑定快捷栏");
    }
    else if(St == SColdSteelSkillTreeCanvas::EStatus::Available)
    {
        // Success rebuilds through OnChanged; a refused commit (sync pending, save failure) has no change event.
        Actions->AddSlot().FillWidth(1)[Button(TEXT("免费习得"), &TreeStyle.Primary, true, [this, Id]
            {
                ActionError.Reset();
                if(Model->LearnSkill(Id)) return;
                ActionError = Model->ResultMessage().IsEmpty() ? FString(TEXT("习得失败，请稍后再试")) : Model->ResultMessage();
                ShowDetail();
            }, Gray(20))];
        Reason = TEXT("不消耗资源；习得后按修炼方式积累经验");
    }
    else if(St == SColdSteelSkillTreeCanvas::EStatus::Locked)
    {
        Actions->AddSlot().FillWidth(1).Padding(0, 0, 4, 0)[Button(TEXT("免费习得"), &TreeStyle.Primary, false, [] {}, Gray(20))];
        FName Jump = NAME_None;
        if(FirstUnmet && FirstUnmet->Skills.Num())
        {
            Jump = FirstUnmet->Skills[0];
            for(FName S : FirstUnmet->Skills) if(SkillLevel(P, S) > SkillLevel(P, Jump)) Jump = S;
        }
        Actions->AddSlot().FillWidth(1).Padding(4, 0, 0, 0)[Button(TEXT("查看未满足条件"), &TreeStyle.Muted, !Jump.IsNone(), [this, Jump] { Select(Jump); }, TextPrimary)];
        Reason = FirstUnmet ? TEXT("还需：") + RequirementText(*FirstUnmet, false) : FString();
    }
    else
    {
        Reason = !Model->CanBindQuickSkill(Id) ? TEXT("被动技能常驻生效，不需要快捷键")
            : Model->CanBindMagic(Id) ? TEXT("把卡片拖到底部快捷栏绑定数字键，或拖进魔法轮盘") : TEXT("把卡片拖到底部快捷栏绑定数字键");
    }
    const bool bError = !ActionError.IsEmpty();
    if(bError) Reason = ActionError;
    return ColdSteelTreePanel::DetailPage(Body, Actions,
        Label(Reason, 12, bError || St == SColdSteelSkillTreeCanvas::EStatus::Locked ? Warning : TextTertiary, false, true), Actions->NumSlots() ? 8.f : 0.f);
}

TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildSpecDetail()
{ using namespace ColdSteelUI; using namespace ColdSteelSkillTree;
    const FSpec* Spec = FindSpec(SpecSkill); const FSpecNode* N = Spec ? Spec->Find(SpecNode) : nullptr;
    if(!Model || !N) return SNullWidget::NullWidget;
    const FColdSteelProfile& P = Model->ProfileView();
    const int32 Rank = SpecRank(P, SpecSkill, SpecNode);
    const FSpecRow* Row = Spec->Rows.FindByPredicate([N](const FSpecRow& R) { return R.Id == N->Row; });
    FString Reason; const bool bCan = Model->CanInvestSpec(SpecSkill, SpecNode, &Reason);
    const FLinearColor Tone = ToneColor(N->Tone);
    auto Body = SNew(SVerticalBox);
    Body->AddSlot().AutoHeight().Padding(0, 0, 0, 22)[SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 14, 0)[SNew(SBox).WidthOverride(84).HeightOverride(84)[SNew(SBorder).BorderImage(&TreeStyle.GlyphBrush).HAlign(HAlign_Center).VAlign(VAlign_Center)
            [SNew(STextBlock).Text(FText::FromString(N->Name.Left(1))).Font(TextFont(38 * .75f, true)).ColorAndOpacity(Rank > 0 || bCan ? Tone : Gray(120))]]]
        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[Label(FString::Printf(TEXT("%s专精 · %s · %s"), *SkillName(SpecSkill), Row ? *Row->Name : TEXT(""), Spec->Columns.IsValidIndex(N->Column) ? *Spec->Columns[N->Column] : TEXT("")), 12, HUDGold)]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 6)[Label(N->Name, 20, TextPrimary, true)]
            + SVerticalBox::Slot().AutoHeight()[Label(FString::Printf(TEXT("每级 %d 点　·　上限 %d 级%s"), N->Cost, N->MaxRank, N->bImplemented ? TEXT("") : TEXT("　·　开发中")), 12, TextSecondary)]]];
    Body->AddSlot().AutoHeight().Padding(0, 0, 0, 28)[SNew(SBorder).BorderImage(&TreeStyle.CardBrush).Padding(FMargin(14, 12))[SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1)[Label(Rank >= N->MaxRank ? TEXT("已满级") : Rank > 0 ? TEXT("已投入") : bCan ? TEXT("可投入") : TEXT("未解锁"), 16, Rank > 0 ? HUDGoldLight : TextPrimary, true)]
            + SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%d / %d 级"), Rank, N->MaxRank))).Font(NumberFont(14 * .75f, true)).ColorAndOpacity(TextPrimary)]]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)[Label(FString::Printf(TEXT("可用专精点 %d，已投入 %d / 获得 %d"), Model->SpecPointsFree(SpecSkill), SpecPointsSpent(P, SpecSkill), SpecPointsEarned(P, SpecSkill)), 12, TextTertiary)]]];
    Body->AddSlot().AutoHeight().Padding(0, 0, 0, 28)[Section(TEXT("效果"), N->MaxRank > 1 ? TEXT("每级") : FString(), Label(N->Text, 13, TextSecondary, false, true))];
    if(!N->bImplemented)
        Body->AddSlot().AutoHeight().Padding(0, 0, 0, 28)[Label(TEXT("该专精的玩法效果仍在开发中，暂时不能投入点数。"), 12, Warning, false, true)];
    auto Reqs = SNew(SVerticalBox);
    if(N->Requires.IsEmpty()) Reqs->AddSlot().AutoHeight()[SNew(SBorder).BorderImage(&TreeStyle.RowMetBrush).Padding(FMargin(12, 9))[Label(TEXT("第一层专精，没有前置；技能习得后即可投入"), 14, TextSecondary, false, true)]];
    for(const auto& R : N->Requires) Reqs->AddSlot().AutoHeight().Padding(0, 0, 0, 6)[Requirement(R, true)];
    Body->AddSlot().AutoHeight()[Section(TEXT("前置条件"), FString(), Reqs)];
    const FName Skill = SpecSkill, Node = SpecNode;
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().FillHeight(1)[ColdSteelUI::ApplyGoldScroll(SNew(SScrollBox) + SScrollBox::Slot().Padding(FMargin(28, 26, 28, 24))[Body], FVector2D(5.5f, 5.5f), FMargin(4, 0, 0, 0), true)]
        + SVerticalBox::Slot().AutoHeight()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gray(18, 160)).Padding(FMargin(28, 14, 28, 18))
            [SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[SNew(SButton).ButtonStyle(&TreeStyle.Primary).IsEnabled(bCan).HAlign(HAlign_Center).OnClicked_Lambda([this, Skill, Node]
                    {
                        // Same as 免费习得: only a refused commit needs an explicit rebuild to show why.
                        ActionError.Reset();
                        if(!Model->InvestSpec(Skill, Node))
                        {
                            ActionError = Model->ResultMessage().IsEmpty() ? FString(TEXT("投入失败，请稍后再试")) : Model->ResultMessage();
                            ShowDetail();
                        }
                        return FReply::Handled();
                    })
                    [SNew(SBox).HeightOverride(ActionHeight).VAlign(VAlign_Center)[Label(FString::Printf(TEXT("投入 %d 点"), N->Cost), 14, bCan ? Gray(20) : TextTertiary, true)]]]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)[Label(!ActionError.IsEmpty() ? ActionError : bCan ? TEXT("撤回与重置：F6 交互开发面板 · 基本调参") : Reason, 12, bCan && ActionError.IsEmpty() ? TextTertiary : Warning, false, true)]]];
}

TSharedRef<SWidget> UColdSteelSkillTreeScreen::BuildSpecPreview()
{ using namespace ColdSteelUI; using namespace ColdSteelSkillTree;
    if(!Model) return SNullWidget::NullWidget;
    struct FRowData { FString Name, Base, Now; bool bGain; };
    TArray<FRowData> Rows;
    auto Num = [](float V, const TCHAR* Unit) { return FString::Printf(TEXT("%s %s"), *FString::SanitizeFloat(FMath::RoundToFloat(V * 100) / 100, 0), Unit); };
    if(SpecSkill == TEXT("fireball"))
    {
        const auto Base = Model->FireballStats(-1, false), Now = Model->FireballStats();
        Rows.Add({ TEXT("爆炸半径"), Num(Base.Radius / 100, TEXT("m")), Num(Now.Radius / 100, TEXT("m")), Now.Radius > Base.Radius + .5f });
        Rows.Add({ TEXT("最大射程"), Num(Base.Range / 100, TEXT("m")), Num(Now.Range / 100, TEXT("m")), Now.Range > Base.Range + .5f });
        Rows.Add({ TEXT("下坠开始时间"), TEXT("0 s"), Num(Now.DropDelay, TEXT("s")), Now.DropDelay > 0 });
        Rows.Add({ TEXT("引燃灼烧"), TEXT("无"), Now.SpecBurnStacks ? FString::Printf(TEXT("%d 层 · %s s"), Now.SpecBurnStacks, *FString::SanitizeFloat(Now.SpecBurnSeconds, 0)) : FString(TEXT("无")), Now.SpecBurnStacks > 0 });
    }
    else if(SpecSkill == TEXT("elementalArrow"))
    {
        const auto& T = Model->DevelopmentSkillDefinition(TEXT("elementalArrow")).ElementalArrow;
        const int32 L = FMath::Max(1, ColdSteelSkillTree::SkillLevel(Model->ProfileView(), SpecSkill));
        const float Fire = ElementalArrow::DamageMultiplier(T, EArrowElement::Fire, L);
        auto S = [this](const TCHAR* Stat) { return Model->SpecStat(TEXT("elementalArrow"), Stat); };
        Rows.Add({ TEXT("火焰箭伤害倍率"), FString::Printf(TEXT("%.2f×"), Fire), FString::Printf(TEXT("%.2f×"), Fire + S(TEXT("fireMultiplier"))), S(TEXT("fireMultiplier")) > 0 });
        Rows.Add({ TEXT("寒冰箭寒冷"), Num(T.ChillSeconds, TEXT("s")), Num(T.ChillSeconds + S(TEXT("chillSeconds")), TEXT("s")), S(TEXT("chillSeconds")) > 0 });
        Rows.Add({ TEXT("闪电箭眩晕"), Num(T.StunSeconds, TEXT("s")), Num(T.StunSeconds + S(TEXT("stunSeconds")), TEXT("s")), S(TEXT("stunSeconds")) > 0 });
        Rows.Add({ TEXT("射出蓝耗倍率"), FString::Printf(TEXT("%.2f×"), T.ManaCostMultiplier), FString::Printf(TEXT("%.2f×"), FMath::Max(.1f, T.ManaCostMultiplier + S(TEXT("manaMultiplier")))), S(TEXT("manaMultiplier")) < 0 });
        Rows.Add({ TEXT("持续拉弓耗蓝"), Num(T.ManaPerSecond, TEXT("/s")), Num(T.ManaPerSecond * FMath::Max(0.f, 1 + S(TEXT("drawManaPercent")) / 100), TEXT("/s")), S(TEXT("drawManaPercent")) < 0 });
        const float Inherit = Model->InheritedFireSpecStat(TEXT("radiusPercent"));
        Rows.Add({ TEXT("继承火球 · 火焰箭爆炸半径"), TEXT("+0%"), FString::Printf(TEXT("+%s%%"), *FString::SanitizeFloat(Inherit, 0)), Inherit > 0 });
        const int32 Stacks = FMath::RoundToInt(Model->SpecStat(TEXT("fireball"), TEXT("burnStacks")));
        Rows.Add({ TEXT("继承火球 · 火焰箭灼烧"), TEXT("无"), Stacks ? FString::Printf(TEXT("%d 层 · 伤害倍率减半"), Stacks) : FString(TEXT("无")), Stacks > 0 });
    }
    auto Table = SNew(SVerticalBox);
    auto Line = [&](const FString& A, const FString& B, const FString& C, const FLinearColor& CColor, bool bHead)
    {
        const FSlateFontInfo Head = TextFont(12 * .75f, true), Value = NumberFont(14 * .75f);
        Table->AddSlot().AutoHeight()[SNew(SBorder).BorderImage(&TreeStyle.RowBrush).Padding(FMargin(12, 7))[SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1.4f)[SNew(STextBlock).Text(FText::FromString(A)).Font(bHead ? Head : TextFont(14 * .75f)).ColorAndOpacity(bHead ? HUDGold : TextSecondary)]
            + SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(B)).Font(bHead ? Head : Value).ColorAndOpacity(bHead ? HUDGold : TextTertiary)]
            + SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(C)).Font(bHead ? Head : Value).ColorAndOpacity(bHead ? HUDGold : CColor)]]];
    };
    Line(TEXT("属性"), TEXT("基础"), TEXT("专精后"), HUDGold, true);
    for(const auto& R : Rows) Line(R.Name, R.Base, R.Now, R.bGain ? Success : TextTertiary, false);
    return SNew(SBox).MaxDesiredWidth(760)[Section(TEXT("当前效果"), FString(), Table)];
}

