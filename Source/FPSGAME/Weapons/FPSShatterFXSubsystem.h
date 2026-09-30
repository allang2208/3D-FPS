#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FPSShatterFXSubsystem.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UStaticMesh;
class UPointLightComponent;
struct FStreamableHandle;

enum class EShatterBurst : uint8 { Hit, Kill, Arrival };

/** Cosmetic, world-owned shards and one-hop traces. No targeting or damage here. */
UCLASS()
class FPSGAME_API UFPSShatterFXSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    void Burst(const FVector& Point,const FVector& Normal,EShatterBurst Kind);
    void Trace(UObject* Source,int32 RoundId,const FVector& Start,const FVector& End,bool bFinished);
    void EndTrace(UObject* Source,int32 RoundId);
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override { return bReady && bActive; }
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    static constexpr int32 BeamCount=96;
    static constexpr int32 ShardCount=144;
    static constexpr int32 FlareCount=48;
    enum { CoreGroup, HaloGroup, ShardGroup, FlareGroup, GroupCount };
    struct FBeam
    {
        TWeakObjectPtr<UObject> Source;
        int32 Id=INDEX_NONE;
        FVector Origin=FVector::ZeroVector,Head=FVector::ZeroVector;
        double Born=0,Ended=0;
        bool Active=false,Finished=false;
    };
    struct FMote
    {
        FVector Origin=FVector::ZeroVector,Velocity=FVector::ZeroVector,Size=FVector::OneVector;
        FRotator Rotation=FRotator::ZeroRotator,Spin=FRotator::ZeroRotator;
        double Born=0;
        float Life=0,Strength=1;
        bool Active=false;
    };
    struct FPulse { FVector Position=FVector::ZeroVector;double Born=-100;float Strength=0; };
    FBeam Beams[BeamCount];
    FMote Shards[ShardCount],Flares[FlareCount];
    FPulse Pulses[2];
    TArray<FTransform> Transforms[GroupCount];
    bool Dirty[GroupCount]={};
    bool bReady=false,bActive=false;
    FRandomStream Random{30092026};
    TSharedPtr<FStreamableHandle> AssetLoad;
    void Prepare();
    void Hide(int32 Group,int32 Index);
    void Write(int32 Group,int32 Index,const FTransform& Transform,float Alpha,float Length=0,float Age=0);
    int32 MoteSlot(FMote* Pool,int32 Count) const;
    void SpawnMote(bool bShard,const FVector& Point,const FVector& Velocity,float Scale,float Life,float Strength);
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Renderers;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> Lights;
    UPROPERTY() TSoftObjectPtr<UMaterialInterface> MaterialAsset{FSoftObjectPath(TEXT("/Game/Weapons/ShatterVFX20260930/M_ShatterVioletV1.M_ShatterVioletV1"))};
    UPROPERTY() TSoftObjectPtr<UStaticMesh> CrystalAsset{FSoftObjectPath(TEXT("/Game/Weapons/ShatterVFX20260930/SM_ShatterCrystal.SM_ShatterCrystal"))};
    UPROPERTY() TSoftObjectPtr<UStaticMesh> CylinderAsset{FSoftObjectPath(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"))};
    UPROPERTY() TSoftObjectPtr<UStaticMesh> PlaneAsset{FSoftObjectPath(TEXT("/Engine/BasicShapes/Plane.Plane"))};
};
