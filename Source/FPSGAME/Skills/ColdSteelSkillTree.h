#pragma once
#include "CoreMinimal.h"
struct FColdSteelProfile;

/** Skill tree + specializations (2026-11-15). Data: Content/ColdSteelData/skill-tree.json, exported from
    Work/SkillTreeMockup20261115 (user-approved V3). Plan: Docs/UI/skill-tree-plan-20261115.md. */
namespace ColdSteelSkillTree
{
    enum class EReqKind : uint8 { Skill, AnyOf, CharacterLevel, PointsInvested };
    struct FRequirement
    {
        EReqKind Kind = EReqKind::Skill;
        TArray<FName> Skills;   // Skill: one id; AnyOf: candidates
        int32 Level = 1;        // skill level, character level or invested points
        bool bCrossBranch = false;
    };
    struct FNode
    {
        FName Id, Branch;
        int32 Lane = 0, Column = 0, Tier = 1; // Tier 0 = 根基 (general), 1..4 = 初级..终极
        FString Kind;                          // magic / martial / mastery / general
        bool bActive = true;
        TArray<FRequirement> Requires;
    };
    struct FBranch { FName Id; FString Name, Note; int32 Lanes = 1; };
    struct FGroup { FName Id; FString Name; TArray<FName> Branches; };

    struct FSpecNode
    {
        FName Id, Row;
        int32 Column = 0, MaxRank = 1, Cost = 1;
        FString Name, Glyph, Tone, Text;
        TArray<FRequirement> Requires;
        FString Stat;          // declarative effect id (radiusPercent, burnStacks, ...); empty for mechanics
        float PerRank = 0.f;
        bool bImplemented = false;
        TMap<FName,float> Params; // every numeric effect field (burnSeconds, burnMultiplier, ...)
        float Param(const TCHAR* Key, float Default) const { const float* V = Params.Find(Key); return V ? *V : Default; }
    };
    struct FSpecRow { FName Id; FString Name, Note; };
    struct FSpec
    {
        FName Skill; FString Title;
        TArray<FString> Columns;
        TArray<FSpecRow> Rows;
        TArray<FSpecNode> Nodes;
        // Fire elemental arrows inherit these fireball nodes at InheritScale.
        FName InheritFrom; float InheritScale = 0.f; TArray<FName> InheritNodes;
        int32 TotalCost() const;
        const FSpecNode* Find(FName Node) const;
    };
    struct FTree
    {
        TArray<FString> Columns;
        TArray<FGroup> Groups;
        TArray<FBranch> Branches;
        TArray<FNode> Nodes;
        TMap<FName,FSpec> Specs;
        bool bLoaded = false;
        const FNode* Find(FName Id) const;
        const FBranch* FindBranch(FName Id) const;
    };

    /** Parsed once per process; returns an empty tree when the file is missing (then nothing is gated). */
    FPSGAME_API const FTree& Get();
    FPSGAME_API bool InTree(FName Skill);

    /** Not in the tree (rune blades, staff light...) or listed in LearnedSkills. */
    FPSGAME_API bool IsLearned(const FColdSteelProfile& Profile, FName Skill);
    FPSGAME_API int32 SkillLevel(const FColdSteelProfile& Profile, FName Skill); // 0 when not learned
    FPSGAME_API bool RequirementMet(const FColdSteelProfile& Profile, const FRequirement& Requirement);
    FPSGAME_API bool CanLearn(const FColdSteelProfile& Profile, FName Skill, FString* Reason = nullptr);
    FPSGAME_API FString RequirementText(const FRequirement& Requirement);

    /** SkillTreeVersion 0 -> 1. Legacy saves: every tree skill learned. Fresh profiles: roots and tier-I starts. */
    FPSGAME_API bool Migrate(FColdSteelProfile& Profile);
    FPSGAME_API bool Validate(const FColdSteelProfile& Profile, FString& Reason);
    /** Host-side sanitizing of a guest upload: drops learned skills whose requirements are unmet and
        spec ranks that are unknown, over cap, unimplemented or exceed the earned points. */
    FPSGAME_API void Sanitize(FColdSteelProfile& Profile);

    // ---- specializations: 1 point per skill level ----
    FPSGAME_API const FSpec* FindSpec(FName Skill);
    FPSGAME_API int32 SpecRank(const FColdSteelProfile& Profile, FName Skill, FName Node);
    FPSGAME_API int32 SpecPointsSpent(const FColdSteelProfile& Profile, FName Skill);
    FPSGAME_API int32 SpecPointsEarned(const FColdSteelProfile& Profile, FName Skill);
    FPSGAME_API bool SpecRequirementMet(const FColdSteelProfile& Profile, FName Skill, const FRequirement& Requirement);
    FPSGAME_API bool CanInvest(const FColdSteelProfile& Profile, FName Skill, FName Node, FString* Reason = nullptr);
    /** Sum of PerRank x rank over implemented nodes with this stat; ScaleInherited applies the fire-arrow share. */
    FPSGAME_API float SpecStat(const FColdSteelProfile& Profile, FName Skill, const TCHAR* Stat);
    /** Fireball spec stat as seen by fire elemental arrows (InheritScale x fireball stat, inherited nodes only). */
    FPSGAME_API float InheritedFireStat(const FColdSteelProfile& Profile, const TCHAR* Stat);
}
