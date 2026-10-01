#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "IceWallTypes.h"
#include "FPSIceWall.generated.h"

class UBoxComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;
class UParticleSystem;
class USoundBase;
class UFPSIceWallComponent;
class UNiagaraComponent;

/** A seed, placement ghost or temporary wall. Geometry never owns gameplay collision. */
UCLASS()
class FPSGAME_API AFPSIceWall : public AActor
{
    GENERATED_BODY()
public:
    AFPSIceWall();
    void Initialize(UFPSIceWallComponent* Ability,const FIceWallCast& Cast,
        const TArray<TObjectPtr<UStaticMesh>>& Meshes,UMaterialInterface* Ice,
        UMaterialInterface* Preview,UParticleSystem* Shatter,USoundBase* Sound,bool bGhost);
    void Gather(float Fraction,const FVector& Origin);
    void PreviewAt(const FIceWallPlacement& Placement);
    void Launch(const FVector& Origin,const FIceWallPlacement& Placement);
    const FIceWallCast& Snapshot() const { return Tuning; }
    bool IsSolid() const;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="IceWall") float MaxHealth=300;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="IceWall") float Health=0;
    void Shatter();
protected:
    virtual void Tick(float Delta) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Scene;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> Barrier;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Blocks;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GhostMaterial;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> BreakFX;
    UPROPERTY(Transient) TObjectPtr<USoundBase> BreakSound;
    TWeakObjectPtr<UFPSIceWallComponent> Component;
    enum class EState : uint8 { Seed, Preview, Rising, Falling, Solid, Shattered };
    EState State=EState::Seed;
    FIceWallCast Tuning;
    FIceWallPlacement Plan;
    FVector ReleaseOrigin=FVector::ZeroVector;
    float Age=0,DropHeight=0,AuraAge=0;
    int32 LayoutShape=-1;
    void BuildLayout(EIceWallShape Shape);
    void Land();
    void BeginDrop();
    void UpdateDrop();
    void EmitLandingFX();
    void ShakeNearbyPlayers();
    void UpdateColdMist(float Delta);
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> ColdMist;
    FVector PreviousMistPosition=FVector::ZeroVector;
    float MistEnvironmentAge=.2f;
    void EnableTerrainBarriers();
    void ExtrudeMonsters();
    void RetryExtrusion();
    void RestoreMonsterIgnores();
    TArray<TWeakObjectPtr<AActor>> PendingMonsters;
    float ExtrusionAge=0;
    int32 ExtrusionCursor=0;
    UPROPERTY(Transient) TArray<TObjectPtr<UBoxComponent>> TerrainBarriers;
};
