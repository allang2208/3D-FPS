#include "ColdSteelSkillTree.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace ColdSteelSkillTree
{
namespace
{
    TArray<FRequirement> ParseRequirements(const TSharedPtr<FJsonObject>& Owner)
    {
        TArray<FRequirement> Out;
        const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
        if(!Owner->TryGetArrayField(TEXT("requires"), List)) return Out;
        for(const auto& Value : *List)
        {
            const auto Object = Value->AsObject(); if(!Object) continue;
            FRequirement R; double Number = 0; FString Text;
            if(Object->TryGetStringField(TEXT("skill"), Text)) { R.Kind = EReqKind::Skill; R.Skills.Add(*Text); }
            else if(const TArray<TSharedPtr<FJsonValue>>* Any = nullptr; Object->TryGetArrayField(TEXT("anyOf"), Any))
            { R.Kind = EReqKind::AnyOf; for(const auto& Id : *Any) R.Skills.Add(*Id->AsString()); }
            else if(Object->TryGetNumberField(TEXT("characterLevel"), Number)) { R.Kind = EReqKind::CharacterLevel; R.Level = FMath::Max(1, int32(Number)); Out.Add(R); continue; }
            else if(Object->TryGetNumberField(TEXT("pointsInvested"), Number)) { R.Kind = EReqKind::PointsInvested; R.Level = FMath::Max(0, int32(Number)); Out.Add(R); continue; }
            else continue;
            if(Object->TryGetNumberField(TEXT("level"), Number)) R.Level = FMath::Max(1, int32(Number));
            Object->TryGetBoolField(TEXT("crossBranch"), R.bCrossBranch);
            if(R.Skills.Num()) Out.Add(MoveTemp(R));
        }
        return Out;
    }
    FTree Load()
    {
        FTree T; FString Json; TSharedPtr<FJsonObject> Root;
        if(!FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir() / TEXT("ColdSteelData/skill-tree.json"))) ||
           !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root) return T;
        const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
        if(Root->TryGetArrayField(TEXT("columns"), Array)) for(const auto& V : *Array) T.Columns.Add(V->AsString());
        if(Root->TryGetArrayField(TEXT("groups"), Array)) for(const auto& V : *Array)
        {
            const auto O = V->AsObject(); if(!O) continue;
            FGroup G; G.Id = *O->GetStringField(TEXT("id")); G.Name = O->GetStringField(TEXT("name"));
            const TArray<TSharedPtr<FJsonValue>>* B = nullptr;
            if(O->TryGetArrayField(TEXT("branches"), B)) for(const auto& Id : *B) G.Branches.Add(*Id->AsString());
            T.Groups.Add(MoveTemp(G));
        }
        const TSharedPtr<FJsonObject>* Object = nullptr;
        if(Root->TryGetObjectField(TEXT("branches"), Object))
            for(const auto& Pair : (*Object)->Values)
            {
                const auto O = Pair.Value->AsObject(); if(!O) continue;
                FBranch B; B.Id = *Pair.Key; B.Name = O->GetStringField(TEXT("name"));
                O->TryGetStringField(TEXT("note"), B.Note); double Lanes = 1; O->TryGetNumberField(TEXT("lanes"), Lanes); B.Lanes = FMath::Clamp(int32(Lanes), 1, 8);
                T.Branches.Add(MoveTemp(B));
            }
        if(Root->TryGetObjectField(TEXT("skills"), Object))
            for(const auto& Pair : (*Object)->Values)
            {
                const auto O = Pair.Value->AsObject(); if(!O) continue;
                FNode N; N.Id = *Pair.Key; N.Branch = *O->GetStringField(TEXT("branch"));
                double V = 0; O->TryGetNumberField(TEXT("lane"), V); N.Lane = FMath::Clamp(int32(V), 0, 8);
                V = 0; O->TryGetNumberField(TEXT("column"), V); N.Column = FMath::Clamp(int32(V), 0, 3);
                N.Tier = N.Branch == TEXT("general") ? 0 : N.Column + 1;
                O->TryGetStringField(TEXT("kind"), N.Kind); O->TryGetBoolField(TEXT("active"), N.bActive);
                N.Requires = ParseRequirements(O);
                T.Nodes.Add(MoveTemp(N));
            }
        if(Root->TryGetObjectField(TEXT("specializations"), Object))
            for(const auto& Pair : (*Object)->Values)
            {
                const auto O = Pair.Value->AsObject(); if(!O) continue;
                FSpec S; S.Skill = *Pair.Key; O->TryGetStringField(TEXT("title"), S.Title);
                if(O->TryGetArrayField(TEXT("columns"), Array)) for(const auto& V : *Array) S.Columns.Add(V->AsString());
                if(O->TryGetArrayField(TEXT("rows"), Array)) for(const auto& V : *Array)
                { const auto R = V->AsObject(); if(!R) continue; FSpecRow Row; Row.Id = *R->GetStringField(TEXT("id")); Row.Name = R->GetStringField(TEXT("name")); R->TryGetStringField(TEXT("note"), Row.Note); S.Rows.Add(MoveTemp(Row)); }
                const TSharedPtr<FJsonObject>* Inherit = nullptr;
                if(O->TryGetObjectField(TEXT("inherit"), Inherit))
                {
                    S.InheritFrom = *(*Inherit)->GetStringField(TEXT("from")); double Scale = 0; (*Inherit)->TryGetNumberField(TEXT("scale"), Scale); S.InheritScale = FMath::Clamp(float(Scale), 0.f, 1.f);
                    const TArray<TSharedPtr<FJsonValue>>* Ids = nullptr; if((*Inherit)->TryGetArrayField(TEXT("nodes"), Ids)) for(const auto& Id : *Ids) S.InheritNodes.Add(*Id->AsString());
                }
                if(O->TryGetArrayField(TEXT("nodes"), Array)) for(const auto& V : *Array)
                {
                    const auto N = V->AsObject(); if(!N) continue;
                    FSpecNode Node; Node.Id = *N->GetStringField(TEXT("id")); Node.Row = *N->GetStringField(TEXT("row"));
                    double D = 0; N->TryGetNumberField(TEXT("column"), D); Node.Column = FMath::Clamp(int32(D), 0, 3);
                    D = 1; N->TryGetNumberField(TEXT("maxRank"), D); Node.MaxRank = FMath::Clamp(int32(D), 1, 20);
                    D = 1; N->TryGetNumberField(TEXT("cost"), D); Node.Cost = FMath::Clamp(int32(D), 1, 20);
                    N->TryGetStringField(TEXT("name"), Node.Name); N->TryGetStringField(TEXT("glyph"), Node.Glyph);
                    N->TryGetStringField(TEXT("tone"), Node.Tone); N->TryGetStringField(TEXT("text"), Node.Text);
                    Node.Requires = ParseRequirements(N);
                    const TSharedPtr<FJsonObject>* Effect = nullptr;
                    if(N->TryGetObjectField(TEXT("effect"), Effect))
                    {
                        (*Effect)->TryGetStringField(TEXT("stat"), Node.Stat);
                        double Per = 0; (*Effect)->TryGetNumberField(TEXT("perRank"), Per); Node.PerRank = FMath::IsFinite(Per) ? float(Per) : 0.f;
                        (*Effect)->TryGetBoolField(TEXT("implemented"), Node.bImplemented);
                        for(const auto& Field : (*Effect)->Values) if(Field.Value.IsValid() && Field.Value->Type == EJson::Number) Node.Params.Add(*Field.Key, float(Field.Value->AsNumber()));
                    }
                    S.Nodes.Add(MoveTemp(Node));
                }
                const FName Key = S.Skill; T.Specs.Add(Key, MoveTemp(S));
            }
        T.bLoaded = T.Nodes.Num() > 0;
        return T;
    }
    bool IsFreshProfile(const FColdSteelProfile& P)
    {
        if(P.Level > 1 || P.Experience > 0 || P.Kills > 0) return false;
        for(const auto& Pair : P.Skills) if(Pair.Value.Level > 1 || Pair.Value.Experience > 0) return false;
        return true;
    }
}

int32 FSpec::TotalCost() const { int32 Sum = 0; for(const auto& N : Nodes) Sum += N.MaxRank * N.Cost; return Sum; }
const FSpecNode* FSpec::Find(FName Node) const { return Nodes.FindByPredicate([Node](const FSpecNode& N) { return N.Id == Node; }); }
const FNode* FTree::Find(FName Id) const { return Nodes.FindByPredicate([Id](const FNode& N) { return N.Id == Id; }); }
const FBranch* FTree::FindBranch(FName Id) const { return Branches.FindByPredicate([Id](const FBranch& B) { return B.Id == Id; }); }

const FTree& Get() { static const FTree Tree = Load(); return Tree; }
bool InTree(FName Skill) { return Get().Find(Skill) != nullptr; }

bool IsLearned(const FColdSteelProfile& P, FName Skill)
{
    if(!InTree(Skill)) return true;
    // Before the one-time migration runs (e.g. a profile still being loaded) nothing is revoked.
    return P.SkillTreeVersion < 1 || P.LearnedSkills.Contains(Skill);
}
int32 SkillLevel(const FColdSteelProfile& P, FName Skill)
{
    if(!IsLearned(P, Skill)) return 0;
    const auto* Progress = P.Skills.Find(Skill); return Progress ? Progress->Level : 0;
}
bool RequirementMet(const FColdSteelProfile& P, const FRequirement& R)
{
    switch(R.Kind)
    {
    case EReqKind::CharacterLevel: return P.Level >= R.Level;
    case EReqKind::Skill: return R.Skills.Num() && SkillLevel(P, R.Skills[0]) >= R.Level;
    case EReqKind::AnyOf: for(FName Id : R.Skills) if(SkillLevel(P, Id) >= R.Level) return true; return false;
    default: return false;
    }
}
FString RequirementText(const FRequirement& R)
{
    auto Name = [](FName Id) { return Id.ToString(); };
    switch(R.Kind)
    {
    case EReqKind::CharacterLevel: return FString::Printf(TEXT("角色等级 %d"), R.Level);
    case EReqKind::PointsInvested: return FString::Printf(TEXT("已投入 %d 点"), R.Level);
    case EReqKind::AnyOf: { FString S; for(FName Id : R.Skills) S += (S.IsEmpty() ? TEXT("") : TEXT(" / ")) + Name(Id); return FString::Printf(TEXT("%s 任一 Lv%d"), *S, R.Level); }
    default: return FString::Printf(TEXT("%s Lv%d"), R.Skills.Num() ? *Name(R.Skills[0]) : TEXT("?"), R.Level);
    }
}
bool CanLearn(const FColdSteelProfile& P, FName Skill, FString* Reason)
{
    const FNode* N = Get().Find(Skill);
    if(!N) { if(Reason) *Reason = TEXT("不在技能树中"); return false; }
    if(IsLearned(P, Skill)) { if(Reason) *Reason = TEXT("已习得"); return false; }
    if(Skill==TEXT("holyLight")) { if(Reason) *Reason=TEXT("前往教堂，向修女学习圣光"); return false; }
    for(const auto& R : N->Requires) if(!RequirementMet(P, R)) { if(Reason) *Reason = TEXT("前置条件未满足"); return false; }
    return true;
}

bool Migrate(FColdSteelProfile& P)
{
    if(P.SkillTreeVersion >= 1 || !Get().bLoaded) return false;
    const bool bFresh = IsFreshProfile(P);
    for(const auto& N : Get().Nodes)
        if(!bFresh || (N.Id!=TEXT("holyLight")&&N.Requires.IsEmpty())) P.LearnedSkills.AddUnique(N.Id);
    P.SkillTreeVersion = 1;
    return true;
}
bool Validate(const FColdSteelProfile& P, FString& Reason)
{
    if(P.SkillTreeVersion < 0 || P.SkillTreeVersion > 1 || P.LearnedSkills.Num() > 128 || P.SkillSpecs.Num() > 64) { Reason = TEXT("技能树存档无效"); return false; }
    for(const auto& Pair : P.SkillSpecs)
    {
        const FSpec* S = FindSpec(Pair.Key);
        if(!S) continue; // retired spec trees are kept but ignored
        int32 Spent = 0;
        for(const auto& Rank : Pair.Value.Ranks)
        {
            const FSpecNode* Node = S->Find(Rank.Key);
            if(Rank.Value < 0 || (Node && Rank.Value > Node->MaxRank)) { Reason = TEXT("专精等级无效"); return false; }
            Spent += Node ? Rank.Value * Node->Cost : 0;
        }
        const auto* Progress = P.Skills.Find(Pair.Key);
        if(Spent > (Progress ? Progress->Level : 0)) { Reason = TEXT("专精点数超出技能等级"); return false; }
    }
    return true;
}

void Sanitize(FColdSteelProfile& P)
{
    if(!Get().bLoaded) return;
    if(P.SkillTreeVersion < 1) return; // legacy upload: migrated by the shadow's next persist
    P.SkillTreeVersion = 1;
    // A skill that already has training beyond Lv1 counts as learned (same rule as the migration).
    // Otherwise keep it only if every requirement is met; repeat until stable because learning chains.
    TArray<FName> Claimed = MoveTemp(P.LearnedSkills); P.LearnedSkills.Reset();
    for(FName Id : Claimed)
    {
        const FNode* Node = Get().Find(Id); if(!Node) continue;
        const auto* Progress = P.Skills.Find(Id);
        if(Node->Requires.IsEmpty() || (Progress && (Progress->Level > 1 || Progress->Experience > 0))) P.LearnedSkills.AddUnique(Id);
    }
    for(bool bChanged = true; bChanged;)
    {
        bChanged = false;
        for(FName Id : Claimed)
            if(!P.LearnedSkills.Contains(Id) && InTree(Id))
            {
                bool bMet = true; for(const auto& R : Get().Find(Id)->Requires) bMet &= RequirementMet(P, R);
                if(bMet) { P.LearnedSkills.Add(Id); bChanged = true; }
            }
    }
    for(auto It = P.SkillSpecs.CreateIterator(); It; ++It)
    {
        const FSpec* S = FindSpec(It.Key());
        if(!S || !IsLearned(P, It.Key())) { It.RemoveCurrent(); continue; }
        for(auto Rank = It.Value().Ranks.CreateIterator(); Rank; ++Rank)
        {
            const FSpecNode* N = S->Find(Rank.Key());
            if(!N || !N->bImplemented || Rank.Value() <= 0) { Rank.RemoveCurrent(); continue; }
            Rank.Value() = FMath::Min(Rank.Value(), N->MaxRank);
        }
        if(SpecPointsSpent(P, It.Key()) > SpecPointsEarned(P, It.Key())) It.Value().Ranks.Reset();
    }
}

const FSpec* FindSpec(FName Skill) { return Get().Specs.Find(Skill); }
int32 SpecRank(const FColdSteelProfile& P, FName Skill, FName Node)
{
    const auto* Spec = P.SkillSpecs.Find(Skill); if(!Spec) return 0;
    return Spec->Ranks.FindRef(Node);
}
int32 SpecPointsSpent(const FColdSteelProfile& P, FName Skill)
{
    const FSpec* S = FindSpec(Skill); const auto* Spec = P.SkillSpecs.Find(Skill);
    if(!S || !Spec) return 0;
    int32 Sum = 0; for(const auto& Pair : Spec->Ranks) if(const FSpecNode* N = S->Find(Pair.Key)) Sum += Pair.Value * N->Cost;
    return Sum;
}
int32 SpecPointsEarned(const FColdSteelProfile& P, FName Skill) { return SkillLevel(P, Skill); }
bool SpecRequirementMet(const FColdSteelProfile& P, FName Skill, const FRequirement& R)
{
    switch(R.Kind)
    {
    case EReqKind::PointsInvested: return SpecPointsSpent(P, Skill) >= R.Level;
    case EReqKind::Skill: return R.Skills.Num() && SpecRank(P, Skill, R.Skills[0]) >= R.Level;
    case EReqKind::AnyOf: for(FName Id : R.Skills) if(SpecRank(P, Skill, Id) >= R.Level) return true; return false;
    default: return RequirementMet(P, R);
    }
}
bool CanInvest(const FColdSteelProfile& P, FName Skill, FName NodeId, FString* Reason)
{
    auto Fail = [Reason](const TCHAR* Text) { if(Reason) *Reason = Text; return false; };
    const FSpec* S = FindSpec(Skill); const FSpecNode* N = S ? S->Find(NodeId) : nullptr;
    if(!N) return Fail(TEXT("专精不存在"));
    if(!IsLearned(P, Skill)) return Fail(TEXT("技能尚未习得"));
    if(!N->bImplemented) return Fail(TEXT("该专精仍在开发中"));
    if(SpecRank(P, Skill, NodeId) >= N->MaxRank) return Fail(TEXT("已满级"));
    for(const auto& R : N->Requires) if(!SpecRequirementMet(P, Skill, R)) return Fail(TEXT("前置条件未满足"));
    if(SpecPointsEarned(P, Skill) - SpecPointsSpent(P, Skill) < N->Cost) return Fail(TEXT("专精点不足"));
    return true;
}
float SpecStat(const FColdSteelProfile& P, FName Skill, const TCHAR* Stat)
{
    const FSpec* S = FindSpec(Skill); if(!S || !IsLearned(P, Skill)) return 0.f;
    float Sum = 0.f;
    for(const auto& N : S->Nodes) if(N.bImplemented && N.Stat == Stat) Sum += N.PerRank * SpecRank(P, Skill, N.Id);
    return Sum;
}
float InheritedFireStat(const FColdSteelProfile& P, const TCHAR* Stat)
{
    const FSpec* Arrow = FindSpec(TEXT("elementalArrow")); const FSpec* From = Arrow ? FindSpec(Arrow->InheritFrom) : nullptr;
    if(!From || Arrow->InheritScale <= 0.f || !IsLearned(P, From->Skill)) return 0.f;
    float Sum = 0.f;
    for(const auto& N : From->Nodes)
        if(N.bImplemented && N.Stat == Stat && Arrow->InheritNodes.Contains(N.Id)) Sum += N.PerRank * SpecRank(P, From->Skill, N.Id);
    return Sum * Arrow->InheritScale;
}
}
