#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "VillageDefenseSection.generated.h"

class UStaticMeshComponent;
class ATemperateHillsWorld;
struct FStreamableHandle;

/** A dormant, server-owned masonry bay. No AI controller or per-frame work. */
UCLASS()
class FPSGAME_API AVillageDefenseSection : public APawn
{
    GENERATED_BODY()
public:
    AVillageDefenseSection();
    void Initialize(ATemperateHillsWorld* Hills,int32 Id,const FSoftObjectPath& Mesh,float Maximum,const FGuid& BuiltId={});
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual float TakeDamage(float Amount,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
    virtual FVector GetNavAgentLocation() const override;
    virtual FVector TargetPoint(const FVector& From) const;
    virtual bool BlocksPassage() const { return Health>0.f; }
    float GetHealth() const {return Health;}
    float GetMaximumHealth() const {return MaximumHealth;}
    int32 GetSectionId() const {return SectionId;}
    int32 GetRepairSoulCost() const {return RepairSoulCost;}
    /** Briefly cached for the viewer's repair prompt. Purchases always query the current scene. */
    bool HasNearbyRepairEnemy(APawn* Viewer) const;
    bool TryRepair(APawn* Payer,FText& Failure);
    UStaticMeshComponent* GetMasonry() const {return Masonry;}
    static void AddAssetPaths(TArray<FSoftObjectPath>& Paths);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void ApplyHealth();
    virtual bool IsRepairSiteClear() const;
    bool IsRepairMeshClear(const UStaticMeshComponent* Part,const FTransform& Placement) const;
    UFUNCTION() virtual void OnRep_Setup();
    UFUNCTION() void OnRep_FixedScale();
    UPROPERTY(ReplicatedUsing=OnRep_FixedScale) FVector FixedScale=FVector::OneVector;
    UFUNCTION() void OnRep_Health();
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Masonry;
    UPROPERTY(ReplicatedUsing=OnRep_Setup) FSoftObjectPath MeshPath;
    UPROPERTY(Replicated) int32 SectionId=INDEX_NONE;
    UPROPERTY(Replicated) FGuid WorldId;
    UPROPERTY(ReplicatedUsing=OnRep_Setup) FGuid PlacedId;
    UPROPERTY(Replicated) float MaximumHealth=1200.f;
    UPROPERTY(ReplicatedUsing=OnRep_Health) float Health=1200.f;
    UPROPERTY(EditDefaultsOnly,Category="Village Defense",meta=(ClampMin="1")) int32 RepairSoulCost=100;
    /** Gate travel at impact, in the concrete gate's native units (degrees or cm). */
    virtual float GateTravelAtCollapse() const { return 0.f; }
    UFUNCTION(NetMulticast,Reliable) void MulticastCollapse(FVector_NetQuantizeNormal Direction,int32 NoiseSeed,float GateTravel);
    UFUNCTION(NetMulticast,Reliable) void MulticastClearRepairedDebris();
    virtual void PresentCollapse(const FVector& Direction,int32 NoiseSeed,float GateTravel);
    TSharedPtr<FStreamableHandle> MeshLoad;
private:
    bool QueryRepairEnemies(APawn* Viewer) const;
    mutable TWeakObjectPtr<APawn> LastThreatViewer;
    mutable double ThreatSampleTime = -1.;
    mutable bool bSampledThreat = false;
};

/** Two independently hinged leaves, one authoritative gate health/interaction. */
UCLASS()
class FPSGAME_API AVillageDefenseGate : public AVillageDefenseSection
{
    GENERATED_BODY()
public:
    AVillageDefenseGate();
    void InitializeGate(ATemperateHillsWorld* Hills,int32 Id,bool Wide,const FGuid& BuiltId={});
    static constexpr float NarrowHingeOffset=331.f;
    static FSoftObjectPath PlacedPostMeshPath();
    static FTransform PlacedPostTransform(bool Right);
    UFUNCTION(BlueprintCallable) void ToggleDoor();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual FVector TargetPoint(const FVector& From) const override;
    virtual bool BlocksPassage() const override {return Health>0.f&&GateAngle<65.f;}
    float GetGateAngle() const {return GateAngle;}
    UStaticMeshComponent* GetRightLeaf() const {return RightLeaf;}
protected:
    virtual void PostNetInit() override;
    virtual void OnRep_Setup() override;
    virtual void ApplyHealth() override;
    virtual bool IsRepairSiteClear() const override;
    virtual float GateTravelAtCollapse() const override { return GateAngle; }
    virtual void PresentCollapse(const FVector& Direction,int32 NoiseSeed,float AngleAtImpact) override;
private:
    UPROPERTY() TObjectPtr<class UVillageGateMotionAudio> MotionAudio;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RightLeaf;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> LeftMount;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RightMount;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PlacedGatePosts;
    UPROPERTY(ReplicatedUsing=OnRep_Angle) float GateAngle=0.f;
    UFUNCTION() void OnRep_Angle();
    float DisplayAngle=0.f,GoalAngle=0.f;
    void Pose(float Angle);
    bool CanSwingTo(float Angle) const;
};
