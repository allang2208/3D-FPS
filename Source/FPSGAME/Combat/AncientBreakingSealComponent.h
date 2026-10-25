#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AncientBreakingSealComponent.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class USoundBase;
struct FStreamableHandle;

/** One target-owned, refreshable seal. Damage remains authoritative. */
UCLASS(ClassGroup=(Combat))
class FPSGAME_API UAncientBreakingSealComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UAncientBreakingSealComponent();
    static UAncientBreakingSealComponent* Apply(AActor* Target,AActor* Source,const FVector& Point,float Seconds);
    float Remaining() const;
    void Clear();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UFUNCTION() void OnRep_State();
    double Clock() const;
    void RequestVisuals();
    void CreateVisual();
    void UpdateVisuals();
    void HideVisuals();
    static void PulseSeat(AActor* Source);
    UPROPERTY(ReplicatedUsing=OnRep_State) double ExpiresAt=0.;
    UPROPERTY(ReplicatedUsing=OnRep_State) uint32 Revision=0;
    UPROPERTY(Replicated) FVector LocalPoint=FVector::ZeroVector;
    UPROPERTY(Replicated) TObjectPtr<AActor> SourceActor;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Mark;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MarkMID;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> OverheadMark;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> OverheadMID;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> MarkMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> MarkMaterial;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    TSharedPtr<FStreamableHandle> AssetLoad;
    FTimerHandle ExpireTimer;
    uint32 ShownRevision=0;
    float VisualAge=0.f;
    FVector FallbackLocalTop=FVector::ZeroVector;
    float OverheadScale=1.f;
    float OverheadHalfHeight=15.f;
    bool bRequested=false,bPlayedSound=false;
};
