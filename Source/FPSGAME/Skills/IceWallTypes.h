#pragma once
#include "CoreMinimal.h"
#include "IceWallTypes.generated.h"

UENUM()
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
USTRUCT()
struct FIceWallCast
{
    GENERATED_BODY()
    UPROPERTY() float Damage=0; UPROPERTY() float FixedDamage=0; UPROPERTY() float IntelligenceContribution=0; UPROPERTY() float WisdomContribution=0;
    UPROPERTY() float ManaCost=100; UPROPERTY() float Cooldown=30; UPROPERTY() float Range=750; UPROPERTY() float Duration=10; UPROPERTY() float CastSpeed=1; UPROPERTY() float MaxHealth=300;
    UPROPERTY() float SegmentSpacing=42; UPROPERTY() float HighHeight=260; UPROPERTY() float LowHeight=100; UPROPERTY() float Thickness=62;
    UPROPERTY() float HoverDuration=30; UPROPERTY() float RiseSeconds=.08f; UPROPERTY() float RiseHeight=160; UPROPERTY() float DropSeconds=.06f; UPROPERTY() float DropHeight=360;
    UPROPERTY() float Knockback=75; UPROPERTY() float PushDistanceMultiplier=2;
    UPROPERTY() float ChillRadius=150; UPROPERTY() float ChillInterval=1; UPROPERTY() float ChillDuration=2.5f; UPROPERTY() float ChillSlow=.035f;
    UPROPERTY() int32 Count=5; UPROPERTY() int32 ChillStacks=1; UPROPERTY() int32 CastHasteStacks=0;
    UPROPERTY() float CastHasteDuration=5;
    UPROPERTY() bool bGrantChain=false;
    UPROPERTY() float PendantChillSlow=0;
    UPROPERTY() float PendantChillSeconds=3;
    float Width() const { return Count*SegmentSpacing; }
    float Height(EIceWallShape Shape) const { return Shape==EIceWallShape::Low?LowHeight:HighHeight; }
};

/** Upright column over a sampled ground patch; offsets are relative to the locked aim point. */
USTRUCT()
struct FIceWallSection
{
    GENERATED_BODY()
    UPROPERTY() float MinAlong=0; UPROPERTY() float MaxAlong=0; UPROPERTY() float Ground=0; UPROPERTY() float MinGround=0; UPROPERTY() float MaxGround=0;
    UPROPERTY() float SlopeAcross=0; UPROPERTY() float SlopeAlong=0; UPROPERTY() float Bottom=0; UPROPERTY() float Top=0;
    float Center() const { return (MinAlong+MaxAlong)*.5f; }
    float Floor(float Across,float Along) const { return Ground+SlopeAcross*Across+SlopeAlong*(Along-Center()); }
};

USTRUCT()
struct FIceWallPlacement
{
    GENERATED_BODY()
    UPROPERTY() FVector Location=FVector::ZeroVector;
    UPROPERTY() FRotator Rotation=FRotator::ZeroRotator;
    UPROPERTY() EIceWallShape Shape=EIceWallShape::High;
    UPROPERTY() bool bValid=false;
    FString Reason;
    UPROPERTY() TArray<FIceWallSection> Sections;
    UPROPERTY() bool bTrimmed=false;
    float MinAlong() const { return Sections.IsEmpty()?0.f:Sections[0].MinAlong; }
    float MaxAlong() const { return Sections.IsEmpty()?0.f:Sections.Last().MaxAlong; }
    float Width() const { return MaxAlong()-MinAlong(); }
    float CenterAlong() const { return (MinAlong()+MaxAlong())*.5f; }
    float Bottom() const { float Z=0;for(const auto& S:Sections)Z=FMath::Min(Z,S.Bottom);return Z; }
    float Top() const { float Z=0;for(const auto& S:Sections)Z=FMath::Max(Z,S.Top);return Z; }
    float GroundMin() const { float Z=0;for(const auto& S:Sections)Z=FMath::Min(Z,S.MinGround);return Z; }
    float GroundMax() const { float Z=0;for(const auto& S:Sections)Z=FMath::Max(Z,S.MaxGround);return Z; }
};
