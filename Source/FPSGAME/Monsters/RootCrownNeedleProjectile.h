#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RootCrownNeedleProjectile.generated.h"
class ARootCrownRigPreview;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class USoundBase;

/** Visible nonhoming bone needle; server sweeps every travelled segment. */
UCLASS()
class FPSGAME_API ARootCrownNeedleProjectile : public AActor
{
    GENERATED_BODY()
public:
    ARootCrownNeedleProjectile();
    void Launch(ARootCrownRigPreview* Source,const FVector& Direction,uint32 Salvo,int32 Wave);
    virtual void Tick(float Dt) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Visual;
    UPROPERTY(ReplicatedUsing=OnRep_Visual) TObjectPtr<UStaticMesh> NeedleMesh;
    UPROPERTY(ReplicatedUsing=OnRep_Visual) TObjectPtr<UMaterialInterface> NeedleMaterial;
    UPROPERTY(Replicated) TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(ReplicatedUsing=OnRep_Stopped) bool bStopped=false;
    UFUNCTION() void OnRep_Visual();
    UFUNCTION() void OnRep_Stopped();
    UFUNCTION(NetMulticast,Unreliable) void PlayImpact(FVector_NetQuantize Position);
    TWeakObjectPtr<ARootCrownRigPreview> Shooter;
    FVector Velocity=FVector::ZeroVector;
    float Remaining=0.f,Damage=0.f;
    uint32 SalvoId=0;
    int32 WaveIndex=0;
};
