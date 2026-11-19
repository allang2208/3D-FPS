// Canvas data for the skill tree screen: rows, card views, edge/gate states, selected path.
#include "ColdSteelSkillTreeScreen.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Skills/ColdSteelSkillTree.h"


FString UColdSteelSkillTreeScreen::SkillName(FName Id) const { using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge; return Model ? Model->DevelopmentSkillDefinition(Id).Name : Id.ToString(); }
FLinearColor UColdSteelSkillTreeScreen::ToneColor(const FString& Tone) const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    if(Tone == TEXT("ice")) return FLinearColor::FromSRGBColor(FColor(143, 208, 255));
    if(Tone == TEXT("storm")) return FLinearColor::FromSRGBColor(FColor(185, 178, 255));
    if(Tone == TEXT("steel")) return ColdSteelUI::Gray(222);
    return FLinearColor::FromSRGBColor(FColor(255, 138, 76));
}
FString UColdSteelSkillTreeScreen::RequirementText(const ColdSteelSkillTree::FRequirement& R, bool bSpecPage) const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    const FSpec* Spec = bSpecPage ? FindSpec(SpecSkill) : nullptr;
    auto Name = [&](FName Id) { if(Spec) if(const auto* N = Spec->Find(Id)) return N->Name; return SkillName(Id); };
    switch(R.Kind)
    {
    case EReqKind::CharacterLevel: return FString::Printf(TEXT("角色等级达到 %d"), R.Level);
    case EReqKind::PointsInvested: return FString::Printf(TEXT("已投入 %d 点专精点"), R.Level);
    case EReqKind::AnyOf: { FString S; for(FName Id : R.Skills) S += (S.IsEmpty() ? TEXT("") : TEXT(" / ")) + Name(Id); return bSpecPage ? FString::Printf(TEXT("%s 任一达到 %d 级"), *S, R.Level) : FString::Printf(TEXT("%s 任一达到 Lv%d"), *S, R.Level); }
    default: return bSpecPage ? FString::Printf(TEXT("%s 达到 %d 级"), *Name(R.Skills[0]), R.Level) : FString::Printf(TEXT("%s 达到 Lv%d"), *Name(R.Skills[0]), R.Level);
    }
}

TArray<ColdSteelSkillTreeLayout::FRow> UColdSteelSkillTreeScreen::TreeRows() const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    TArray<ColdSteelSkillTreeLayout::FRow> Rows;
    const FTree& T = Get();
    for(const FGroup& G : T.Groups)
    {
        if(!Group.IsNone() && G.Id != Group) continue;
        for(FName BranchId : G.Branches)
        {
            const FBranch* B = T.FindBranch(BranchId); if(!B) continue;
            ColdSteelSkillTreeLayout::FRow Row; Row.Key = B->Id; Row.Name = B->Name; Row.Note = B->Note; Row.Group = G.Name; Row.Lanes = B->Lanes;
            for(const FNode& N : T.Nodes) if(N.Branch == BranchId) Row.Items.Add({ N.Id, N.Lane, N.Column, N.Requires });
            Rows.Add(MoveTemp(Row));
        }
    }
    return Rows;
}
TArray<ColdSteelSkillTreeLayout::FRow> UColdSteelSkillTreeScreen::SpecRows(FName Skill) const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    TArray<ColdSteelSkillTreeLayout::FRow> Rows;
    if(const FSpec* S = FindSpec(Skill))
        for(const FSpecRow& R : S->Rows)
        {
            ColdSteelSkillTreeLayout::FRow Row; Row.Key = R.Id; Row.Name = R.Name; Row.Note = R.Note;
            for(const FSpecNode& N : S->Nodes) if(N.Row == R.Id) Row.Items.Add({ N.Id, 0, N.Column, N.Requires });
            Rows.Add(MoveTemp(Row));
        }
    return Rows;
}
SColdSteelSkillTreeCanvas::EStatus UColdSteelSkillTreeScreen::SkillStatus(FName Id) const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    if(!Model) return EStatus::Locked;
    if(Model->IsSkillLearned(Id)) return SkillLevel(Model->ProfileView(), Id) >= Model->DevelopmentSkillDefinition(Id).MaxLevel ? EStatus::Maxed : EStatus::Learned;
    return Model->CanLearnSkill(Id) ? EStatus::Available : EStatus::Locked;
}
TSet<FName> UColdSteelSkillTreeScreen::TreePath(FName Id) const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    TSet<FName> Out; TArray<FName> Stack = { Id };
    while(Stack.Num())
    {
        const FName Cur = Stack.Pop(); if(Out.Contains(Cur)) continue; Out.Add(Cur);
        if(const FNode* N = Get().Find(Cur))
            for(const ColdSteelSkillTree::FRequirement& R : N->Requires)
                if(R.Kind == EReqKind::Skill || (R.Kind == EReqKind::AnyOf && !R.bCrossBranch)) Stack.Append(R.Skills);
    }
    return Out;
}

SColdSteelSkillTreeCanvas::FSource UColdSteelSkillTreeScreen::TreeSource() const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    SColdSteelSkillTreeCanvas::FSource S;
    S.Columns = Get().Columns; S.Selected = Selected; S.Path = TreePath(Selected);
    UColdSteelSkillTreeScreen* Mutable = const_cast<UColdSteelSkillTreeScreen*>(this);
    const FColdSteelProfile* P = Model ? &Model->ProfileView() : nullptr;
    S.Card = [this, Mutable, P](FName Id)
    {
        SColdSteelSkillTreeCanvas::FCardView V;
        const FNode* N = Get().Find(Id); if(!N || !P || !Model) return V;
        const auto& D = Model->DevelopmentSkillDefinition(Id);
        V.Name = D.Name; V.Status = SkillStatus(Id); V.Icon = Mutable->Icon(D.Icon);
        int32 Met = 0; for(const auto& R : N->Requires) Met += RequirementMet(*P, R) ? 1 : 0;
        const int32 Level = SkillLevel(*P, Id);
        static const TMap<FString, FString> Kinds = { { TEXT("magic"), TEXT("魔法") }, { TEXT("martial"), TEXT("武技") }, { TEXT("mastery"), TEXT("精通") }, { TEXT("general"), TEXT("通用") } };
        const FString Kind = (N->bActive ? TEXT("主动") : TEXT("被动")) + Kinds.FindRef(N->Kind);
        switch(V.Status)
        {
        case EStatus::Locked: V.State = FString::Printf(TEXT("条件 %d/%d"), Met, N->Requires.Num()); V.Progress = N->Requires.Num() ? float(Met) / N->Requires.Num() : 0.f; break;
        case EStatus::Available: V.State = TEXT("可免费习得"); V.bStateHighlight = true; V.Progress = 1.f; break;
        default:
            V.Progress = float(Level) / FMath::Max(1, D.MaxLevel);
            V.Side = V.Status == EStatus::Maxed ? TEXT("MAX") : FString::FromInt(Level);
            if(V.Status == EStatus::Learned) V.SideSmall = FString::Printf(TEXT("/%d"), D.MaxLevel);
            if(FindSpec(Id) && Model->SpecPointsFree(Id) > 0) { V.State = FString::Printf(TEXT("专精点 %d 可用"), Model->SpecPointsFree(Id)); V.bStateHighlight = V.bStateGold = true; }
            else V.State = V.Status == EStatus::Maxed ? TEXT("已满级") : Kind;
        }
        if(Id==TEXT("holyLight")&&!Model->IsSkillLearned(Id)) V.State=TEXT("教堂修女传授");
        if(N->Requires.Num() > 1) V.TabRight = FString::Printf(TEXT("全部 %d/%d"), Met, N->Requires.Num());
        for(const auto& R : N->Requires)
        {
            if(R.Kind == EReqKind::CharacterLevel) { V.TabLeft = FString::Printf(TEXT("角色 Lv%d"), R.Level); V.bTabLeftMet = RequirementMet(*P, R); }
            if(R.Kind == EReqKind::AnyOf && R.bCrossBranch)
            {
                V.TabLeft = FString::Printf(TEXT("跨系 · %s%s · Lv%d"), *SkillName(R.Skills[0]), R.Skills.Num() > 1 ? *FString::Printf(TEXT(" +%d"), R.Skills.Num() - 1) : TEXT(""), R.Level);
                V.bTabLeftMet = RequirementMet(*P, R);
            }
        }
        if(!Query.IsEmpty()) { const bool bHit = D.Name.Contains(Query) || D.Description.Contains(Query); V.bDim = !bHit; V.bMatch = bHit; }
        return V;
    };
    auto EntryEdge = [this, P](const ColdSteelSkillTreeLayout::FEntry& E, int32 RequiredLevel)
    {
        if(!P) return EEdge::Unmet;
        if(SkillLevel(*P, E.From) < RequiredLevel) return EEdge::Unmet;
        return Model->IsSkillLearned(E.To) ? EEdge::Lit : EEdge::Met;
    };
    auto Required = [](const ColdSteelSkillTreeLayout::FEntry& E) { const FNode* N = Get().Find(E.To); return N && N->Requires.IsValidIndex(E.Requirement) ? N->Requires[E.Requirement].Level : 1; };
    S.Edge = [this, EntryEdge, Required](int32 I) { const auto& E = TreeCanvas->GetLayout().Entries[I]; return EntryEdge(E, Required(E)); };
    S.EdgeLabel = [this, P, Required](int32 I) -> FString
    {
        const auto& E = TreeCanvas->GetLayout().Entries[I];
        if(!P || (Model->IsSkillLearned(E.To) && E.To != Selected)) return FString();
        const int32 Need = Required(E), Have = SkillLevel(*P, E.From);
        return Have >= Need ? FString::Printf(TEXT("Lv%d"), Need) : FString::Printf(TEXT("Lv%d/%d"), Have, Need);
    };
    S.Gate = [this, P](int32 I)
    {
        const auto& G = TreeCanvas->GetLayout().Gates[I]; const FNode* N = Get().Find(G.To);
        if(!P || !N || !N->Requires.IsValidIndex(G.Requirement) || !RequirementMet(*P, N->Requires[G.Requirement])) return EEdge::Unmet;
        return Model->IsSkillLearned(G.To) ? EEdge::Lit : EEdge::Met;
    };
    S.GateLabel = [this](int32 I) { const auto& G = TreeCanvas->GetLayout().Gates[I]; const FNode* N = Get().Find(G.To);
        return N && N->Requires.IsValidIndex(G.Requirement) ? FString::Printf(TEXT("Lv%d"), N->Requires[G.Requirement].Level) : FString(); };
    S.BandNote = [this](const ColdSteelSkillTreeLayout::FBand& B)
    {
        if(!B.Note.IsEmpty() || !Model) return B.Note;
        int32 Learned = 0; for(FName Id : B.Items) Learned += Model->IsSkillLearned(Id) ? 1 : 0;
        return FString::Printf(TEXT("%d / %d"), Learned, B.Items.Num());
    };
    return S;
}

SColdSteelSkillTreeCanvas::FSource UColdSteelSkillTreeScreen::SpecSource() const
{ using namespace ColdSteelSkillTree; using EStatus = SColdSteelSkillTreeCanvas::EStatus; using EEdge = SColdSteelSkillTreeCanvas::EEdge;
    SColdSteelSkillTreeCanvas::FSource S;
    const FSpec* Spec = FindSpec(SpecSkill); if(!Spec || !Model) return S;
    const FColdSteelProfile* P = &Model->ProfileView(); const FName Skill = SpecSkill;
    S.Columns = Spec->Columns; S.Selected = SpecNode;
    TArray<FName> Stack = { SpecNode };
    while(Stack.Num())
    {
        const FName Cur = Stack.Pop(); if(S.Path.Contains(Cur)) continue; S.Path.Add(Cur);
        if(const FSpecNode* N = Spec->Find(Cur)) for(const auto& R : N->Requires) if(R.Kind == EReqKind::Skill) Stack.Append(R.Skills);
    }
    S.Card = [this, Spec, P, Skill](FName Id)
    {
        SColdSteelSkillTreeCanvas::FCardView V; const FSpecNode* N = Spec->Find(Id); if(!N) return V;
        const int32 Rank = SpecRank(*P, Skill, Id);
        bool bReq = true; int32 Met = 0; for(const auto& R : N->Requires) { const bool bOk = SpecRequirementMet(*P, Skill, R); bReq &= bOk; Met += bOk; }
        V.Name = N->Name; V.Glyph = N->Name.Left(1); V.GlyphColor = ToneColor(N->Tone); V.bLockedIcon = false;
        V.Status = Rank >= N->MaxRank ? EStatus::Maxed : Rank > 0 ? EStatus::Learned : bReq && N->bImplemented ? EStatus::Available : EStatus::Locked;
        V.Side = FString::FromInt(Rank); V.SideSmall = FString::Printf(TEXT("/%d"), N->MaxRank);
        V.Progress = float(Rank) / N->MaxRank;
        if(!N->bImplemented) V.State = TEXT("开发中");
        else if(Rank > 0) V.State = Rank >= N->MaxRank ? TEXT("已满级") : FString::Printf(TEXT("已投入 %d 级"), Rank);
        else if(bReq) { V.State = FString::Printf(TEXT("可投入 · %d 点"), N->Cost); V.bStateHighlight = true; }
        else V.State = TEXT("前置未满足");
        if(N->Requires.Num() > 1) V.TabRight = FString::Printf(TEXT("全部 %d/%d"), Met, N->Requires.Num());
        for(const auto& R : N->Requires) if(R.Kind == EReqKind::PointsInvested)
        { V.TabLeft = FString::Printf(TEXT("已投入 %d/%d 点"), SpecPointsSpent(*P, Skill), R.Level); V.bTabLeftMet = SpecRequirementMet(*P, Skill, R); }
        return V;
    };
    auto Need = [Spec](const ColdSteelSkillTreeLayout::FEntry& E) { const FSpecNode* N = Spec->Find(E.To); return N && N->Requires.IsValidIndex(E.Requirement) ? N->Requires[E.Requirement].Level : 1; };
    S.Edge = [this, P, Skill, Need](int32 I)
    {
        const auto& E = SpecCanvas->GetLayout().Entries[I];
        if(SpecRank(*P, Skill, E.From) < Need(E)) return EEdge::Unmet;
        return SpecRank(*P, Skill, E.To) > 0 ? EEdge::Lit : EEdge::Met;
    };
    S.EdgeLabel = [this, P, Skill, Need](int32 I) -> FString
    {
        const auto& E = SpecCanvas->GetLayout().Entries[I]; const int32 Have = SpecRank(*P, Skill, E.From), Req = Need(E);
        return Have >= Req ? FString::Printf(TEXT("%d 级"), Req) : FString::Printf(TEXT("%d/%d 级"), Have, Req);
    };
    S.Gate = [this, Spec, P, Skill](int32 I)
    {
        const auto& G = SpecCanvas->GetLayout().Gates[I]; const FSpecNode* N = Spec->Find(G.To);
        if(!N || !N->Requires.IsValidIndex(G.Requirement) || !SpecRequirementMet(*P, Skill, N->Requires[G.Requirement])) return EEdge::Unmet;
        return SpecRank(*P, Skill, G.To) > 0 ? EEdge::Lit : EEdge::Met;
    };
    S.GateLabel = [this, Spec](int32 I) { const auto& G = SpecCanvas->GetLayout().Gates[I]; const FSpecNode* N = Spec->Find(G.To);
        return N && N->Requires.IsValidIndex(G.Requirement) ? FString::Printf(TEXT("%d 级"), N->Requires[G.Requirement].Level) : FString(); };
    S.BandNote = [](const ColdSteelSkillTreeLayout::FBand& B) { return B.Note; };
    return S;
}
