#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;
class UMaterialInstanceDynamic;

/** Bounded samples of the rendered skirt; no CPU skinned-mesh conversion. */
struct FFPSRobeHemEnvelope
{
    // Shared layout with hem_materials.py / hem_conform.hlsl, bottom to waist.
    static constexpr int32 RingCount=4, RingPoints=16, PointCount=RingCount*RingPoints;
    struct FInfluence { int32 Bone=INDEX_NONE; float Weight=0; FVector Position=FVector::ZeroVector; };
    struct FSample { int32 Particle=INDEX_NONE; TArray<FInfluence> Influences; };
    TWeakObjectPtr<USkeletalMeshComponent> Garment;
    TArray<FSample> Samples;
    FVector Points[PointCount]{};
    FVector SimulationResidual[PointCount]{};
    float Scale=1.f,AnkleCut=16.f,Strength=0.f;
    float StairBlend=0.f;
    float SimulationAge=1.f;
    int32 ClothIndex=INDEX_NONE;
    bool bReady=false;
    void Initialize(USkeletalMeshComponent* Robe);
    void Update(bool bOnStairs,float Delta);
};

/** Continuous inner layers: hide obsolete ankle caps, tuck covered surfaces. */
struct FFPSRobeStairSections
{
    struct FSection
    {
        int32 Material=INDEX_NONE;
        bool bStairOnly=false;
        bool bCovered=false;
    };
    struct FMaterial
    {
        TWeakObjectPtr<UMaterialInstanceDynamic> Instance;
        TArray<int32> Points;
        int32 Strength=INDEX_NONE,Shape=INDEX_NONE;
        float LastStrength=0.f;
    };
    TWeakObjectPtr<USkeletalMeshComponent> Mesh;
    TArray<FSection> Sections;
    TArray<FMaterial> Materials;
    int32 LODCount=0;
    bool bApplied=false,bLastHidden=false;
    void Initialize(USkeletalMeshComponent* Part,const TArray<int32>& Covered);
    void Apply(bool bOnStairs);
    void Conform(const FFPSRobeHemEnvelope& Hem);
};
