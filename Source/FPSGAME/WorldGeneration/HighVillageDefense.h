#pragma once

#include "VillageDefenseSection.h"
#include "HighVillageDefense.generated.h"

enum class EHighGateUse : uint8 { None, Repair, Release };

UCLASS()
class FPSGAME_API AHighVillageWall : public AVillageDefenseSection
{
    GENERATED_BODY()
public:
    void InitializeHighWall(ATemperateHillsWorld* Hills,int32 Id,const FGuid& BuiltId={});
    static const FSoftObjectPath& WallMeshPath();
    static void AddHighAssetPaths(TArray<FSoftObjectPath>& Paths);
protected:
    virtual void PresentCollapse(const FVector& Direction,int32 NoiseSeed,float LiftCm) override;
};

/** Masonry is the moving portcullis. Its stone housing remains after a breach. */
UCLASS()
class FPSGAME_API AHighVillageGate : public AVillageDefenseSection
{
    GENERATED_BODY()
public:
    AHighVillageGate();
    void InitializeHighGate(ATemperateHillsWorld* Hills,int32 Id,bool bWest,const FGuid& BuiltId={});
    static const FSoftObjectPath& PlacedPortalMeshPath();
    static const FSoftObjectPath& PlacedPortalMeshPath(bool bWest);
    static const FSoftObjectPath& PlacedGrilleMeshPath();
    static const FSoftObjectPath& PlacedGrilleMeshPath(bool bWest);
    UFUNCTION(BlueprintCallable) void ToggleDoor();
    EHighGateUse ResolveUse(const FHitResult& Hit) const;
    bool IsOpening() const { return bWantsOpen; }
    virtual bool NeedsRepair() const override { return Health < MaximumHealth; }
    static const FSoftObjectPath& ReleaseMeshPath();
    static FTransform ReleasePose(bool bWest,float OpenFraction=0.f);
    virtual bool BlocksPassage() const override { return Health>0.f && LiftCm<220.f; }
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UStaticMeshComponent* GetStonePortal() const { return Portal; }
protected:
    virtual void PostNetInit() override;
    virtual void OnRep_Setup() override;
    virtual void ApplyHealth() override;
    virtual void MulticastClearRepairedDebris_Implementation() override;
    virtual float GateTravelAtCollapse() const override { return LiftCm; }
    virtual void PresentCollapse(const FVector& Direction,int32 NoiseSeed,float StartHeight) override;
private:
    UPROPERTY() TObjectPtr<class UVillageGateMotionAudio> MotionAudio;
    UPROPERTY(Transient) TObjectPtr<class UVillagePortcullisHoist> Hoist;
    TSharedPtr<FStreamableHandle> HoistLoad;
    void SetupHoist();
    float TravelCm() const;
    bool CanLower(float NewHeight) const;
    void Pose(float Height);
    UFUNCTION() void OnRep_Lift();
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Portal;
    UPROPERTY(ReplicatedUsing=OnRep_Lift) float LiftCm=0.f;
    float DisplayLift=0.f;
    UPROPERTY(Replicated) bool bWantsOpen=false;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> ReleaseHandle;
    UPROPERTY(Transient) TObjectPtr<class UChildActorComponent> ControlTorch;
    TSharedPtr<FStreamableHandle> PortalLoad;
};
