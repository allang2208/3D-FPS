#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarhammerSlamFXSubsystem.generated.h"

class UInstancedStaticMeshComponent;
class UDecalComponent;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

/** Eight reusable cosmetic impacts. The replicated wave alone owns damage. */
UCLASS()
class FPSGAME_API UWarhammerSlamFXSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
    virtual void Tick(float Delta) override;
    virtual bool IsTickable() const override { return ActiveCount>0; }
    virtual TStatId GetStatId() const override;
    void Emit(const FVector& Point,const FQuat& Rotation,float Radius,float Age);
    bool PrepareBackground();
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    struct FPuff { FVector Direction; float Travel=0,Size=0,Seed=0,Delay=0,Life=0; };
    struct FStone { FVector Velocity; FQuat Rotation; FVector Axis; float Spin=0,Size=0; };
    struct FImpact
    {
        FVector Point=FVector::ZeroVector;
        FQuat Rotation=FQuat::Identity;
        TArray<FPuff> Puffs;
        TArray<FStone> Stones;
        float Age=6.f;
    };
    TArray<FImpact> Impacts;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Dust;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Debris;
    UPROPERTY(Transient) TArray<TObjectPtr<UDecalComponent>> Cracks;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> CrackMaterials;
    TSharedPtr<FStreamableHandle> Assets;
    int32 ActiveCount=0;
    bool PrepareSlot(int32 Index);
};
