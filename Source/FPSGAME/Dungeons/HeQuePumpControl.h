#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HeQuePumpControl.generated.h"

class AHeQueMonster;
class APlayerController;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/** Two physical valves in the pump hall; all activation and boss effects belong to the server. */
UCLASS(NotBlueprintable,Transient)
class FPSGAME_API AHeQuePumpControl : public AActor
{
    GENERATED_BODY()
public:
    AHeQuePumpControl();
    void Configure(AHeQueMonster* InBoss,const FVector& InVentOrigin);
    bool ActivateFrom(APlayerController* Controller);
    FString Prompt() const;
    bool CanActivate() const;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UFUNCTION() void OnRep_State();
    void Present();
    double Clock() const;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Valve;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Warning;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Release;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WarningMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ReleaseMID;
    UPROPERTY(ReplicatedUsing=OnRep_State) TObjectPtr<AHeQueMonster> Boss;
    UPROPERTY(ReplicatedUsing=OnRep_State) FVector VentOrigin=FVector::ZeroVector;
    UPROPERTY(ReplicatedUsing=OnRep_State) double ActivatedAt=-1.;
    UPROPERTY(ReplicatedUsing=OnRep_State) bool bCaught=false;
    bool bSoundPlayed=false;
};
