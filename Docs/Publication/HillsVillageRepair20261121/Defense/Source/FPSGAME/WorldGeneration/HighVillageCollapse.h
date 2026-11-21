#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HighVillageCollapse.generated.h"

class AVillageDefenseSection;
class UStaticMeshComponent;
class UStaticMesh;

/** Short-lived local presentation. The destroyed section remains the sole authority for the breach. */
UCLASS(Transient,NotBlueprintable)
class AHighVillageCollapse : public AActor
{
    GENERATED_BODY()
public:
    AHighVillageCollapse();
    static void Wall(AVillageDefenseSection& Section,const FVector& Direction,int32 Seed);
    static void Gate(AVillageDefenseSection& Section,const FVector& Direction,float StartHeight);
    static void Stairs(AActor& Section,const FVector& Direction,int32 Seed);
    static void AddAssetPaths(TArray<FSoftObjectPath>& Paths);
    virtual void Tick(float DeltaSeconds) override;
private:
    static AHighVillageCollapse* Begin(AActor& Section);
    void Dust(FVector LocalPosition,float Scale);
    void AddFragment(UStaticMesh* Mesh,const FTransform& LocalPose,float ReleaseTime,const FVector& Velocity,const FVector& Spin);
    void AnimateGrille();
    void ReleaseGuideStones(const UStaticMesh& Mesh);
    void ReleaseStairBays(const FVector& Direction,int32 Seed);
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Grille;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WaitingStair;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Rubble;
    TArray<float> ReleaseTimes;
    TArray<FVector> LaunchSpeeds,AngularSpeeds,FragmentScales;
    float Age=0.f,InitialLift=0.f,TipSide=1.f;
    bool bGroundImpact=false,bSawBreach=false,bStairs=false;
};
