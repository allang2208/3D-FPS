#pragma once
#include "CoreMinimal.h"

enum class EIceWallShape : uint8 { High, Low };

struct FIceWallTuning
{
    float DamageBase=10, DamagePerLevel=10, IntelligenceBase=1, IntelligencePerLevel=.25f;
    float WisdomBase=1, WisdomPerLevel=.25f, ManaCost=100, Cooldown=30;
    float Range=500, UnitsToCM=1.5f, Duration=10, DurationPerLevel=.5f;
    int32 CountBase=5, CountPerLevel=2, HitExperience=3, KillExperience=10, MultiHitExperience=10;
    float SegmentSpacing=28, HighHeight=260, LowHeight=100, Thickness=62;
    float HoverDuration=30, RiseSeconds=.08f, RiseHeight=160, DropSeconds=.06f, DropHeight=360;
    float MaxHealth=300, MaxHealthPerLevel=50;
    float Knockback=50, PushDistanceMultiplier=2, ChillRadius=100, ChillInterval=1;
    float ChillDuration=2.5f, ChillSlow=.035f;
    int32 ChillStacks=1;
    bool bRequiresStaff=true;
};

/** One immutable gather snapshot shared by the UI, seed and resulting wall. */
struct FIceWallCast
{
    float Damage=0, FixedDamage=0, IntelligenceContribution=0, WisdomContribution=0;
    float ManaCost=100, Cooldown=30, Range=750, Duration=10, CastSpeed=1, MaxHealth=300;
    float SegmentSpacing=42, HighHeight=260, LowHeight=100, Thickness=62;
    float HoverDuration=30, RiseSeconds=.08f, RiseHeight=160, DropSeconds=.06f, DropHeight=360;
    float Knockback=75, PushDistanceMultiplier=2;
    float ChillRadius=150, ChillInterval=1, ChillDuration=2.5f, ChillSlow=.035f;
    int32 Count=5, ChillStacks=1, CastHasteStacks=0;
    float CastHasteDuration=5;
    bool bGrantChain=false;
    float Width() const { return Count*SegmentSpacing; }
    float Height(EIceWallShape Shape) const { return Shape==EIceWallShape::Low?LowHeight:HighHeight; }
};

/** Upright column over a sampled ground patch; offsets are relative to the locked aim point. */
struct FIceWallSection
{
    float MinAlong=0,MaxAlong=0,Ground=0,MinGround=0,MaxGround=0;
    float SlopeAcross=0,SlopeAlong=0,Bottom=0,Top=0;
    float Center() const { return (MinAlong+MaxAlong)*.5f; }
    float Floor(float Across,float Along) const { return Ground+SlopeAcross*Across+SlopeAlong*(Along-Center()); }
};

struct FIceWallPlacement
{
    FVector Location=FVector::ZeroVector;
    FRotator Rotation=FRotator::ZeroRotator;
    EIceWallShape Shape=EIceWallShape::High;
    bool bValid=false;
    FString Reason;
    TArray<FIceWallSection> Sections;
    bool bTrimmed=false;
    float MinAlong() const { return Sections.IsEmpty()?0.f:Sections[0].MinAlong; }
    float MaxAlong() const { return Sections.IsEmpty()?0.f:Sections.Last().MaxAlong; }
    float Width() const { return MaxAlong()-MinAlong(); }
    float CenterAlong() const { return (MinAlong()+MaxAlong())*.5f; }
    float Bottom() const { float Z=0;for(const auto& S:Sections)Z=FMath::Min(Z,S.Bottom);return Z; }
    float Top() const { float Z=0;for(const auto& S:Sections)Z=FMath::Max(Z,S.Top);return Z; }
    float GroundMin() const { float Z=0;for(const auto& S:Sections)Z=FMath::Min(Z,S.MinGround);return Z; }
    float GroundMax() const { float Z=0;for(const auto& S:Sections)Z=FMath::Max(Z,S.MaxGround);return Z; }
};
