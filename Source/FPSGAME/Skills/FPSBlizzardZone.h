#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BlizzardTypes.h"
#include "FPSBlizzardZone.generated.h"
class UNiagaraComponent;
class UDecalComponent;
class UMaterialInstanceDynamic;
class UInstancedStaticMeshComponent;
class USoundBase;
struct FStreamableHandle;

USTRUCT()
struct FBlizzardVisualLayer
{
    GENERATED_BODY()
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Cloud;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Snow;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Mist;
    UPROPERTY(Transient) TObjectPtr<UDecalComponent> Frost;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FrostMaterial;
    bool bActive=false;
};

UCLASS()
class FPSGAME_API AFPSBlizzardZone : public AActor
{
    GENERATED_BODY()
public:
    AFPSBlizzardZone();
    bool InitializeZone(APawn* Shooter,const FBlizzardCast& Spell,const FVector& Point,const FVector& Normal,const FVector& LongAxis,const TArray<TObjectPtr<UObject>>& Assets);
    void ActivateZone();
    /** 15 件资产路径表：组件预热与远端副本自载共用同一张清单。 */
    static const TCHAR* const* ZoneAssetPaths();
    static bool HasBasicAssets(const TArray<TObjectPtr<UObject>>& Assets);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void Tick(float Delta) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TArray<FBlizzardVisualLayer> VisualLayers;
    TArray<FVector> CloudRoomCells;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Hail;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Spikes;
    struct FChunk{FVector Position=FVector::ZeroVector,Velocity=FVector::ZeroVector;float Age=0,Size=0,FloorZ=0;int32 Layer=0;bool bActive=false,bFragment=false;float Roll=0;};
    FChunk Chunks[48];
    TWeakObjectPtr<APawn> Caster;
    FBlizzardCast CastSnapshot;
    FBlizzardRewards Rewards;
    FVector Center=FVector::ZeroVector,SurfaceNormal=FVector::UpVector,AxisX=FVector::ForwardVector,AxisY=FVector::RightVector,Wind=FVector::ZeroVector;
    FRandomStream Random;
    float Age=0,NextDamage=0,CloudHeight=0,CloudThickness=0,NextCloudProbe=0,CosmeticClock=0,SpawnClock=0,Detail=1,NextLandingSound=0;
    bool bActivated=false,bFinished=false,bRoomGridDirty=true,bHasIce=false;
    void DamageTick();
    void Finish();
    void UpdatePresentation(float Delta);
    void UpdateCloudClearance(bool bForce=false);
    void SpawnChunk();
    void ScatterFragments(const FVector& Point,const FVector& Normal,int32 Layer);
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> LandingSound;
    void PlayLandingSound(const FVector& Point,bool bSnowball);
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> SpikeHearts;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> SpikeShells;
    // ── 联机复制态：服务端权威结算伤害；远端副本只演风暴表现 ──
    UPROPERTY(Replicated) TObjectPtr<APawn> NetCaster;
    UPROPERTY(Replicated) FBlizzardCast NetCast;
    UPROPERTY(Replicated) FVector_NetQuantize NetCenter;
    UPROPERTY(Replicated) FVector_NetQuantizeNormal NetNormal;
    UPROPERTY(Replicated) FVector_NetQuantizeNormal NetAxis;
    UPROPERTY(Replicated) float NetCloudHeight=0;
    UPROPERTY(Replicated) float NetCloudThickness=0;
    UPROPERTY(ReplicatedUsing=OnRep_RoomCells) TArray<FVector> NetRoomCells;
    UFUNCTION() void OnRep_RoomCells(){bRoomGridDirty=true;}
    UPROPERTY(Replicated) double NetStartedAt=0;
    UPROPERTY(Replicated) bool bNetFinished=false;
    UPROPERTY(Replicated) bool bNetActivated=false;
    bool bNetInit=false;
    bool bNetAssetsRequested=false,bNetAssetsReady=false;
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> NetAssets;
    TSharedPtr<FStreamableHandle> NetAssetLoad;
    void NetInit();
};
