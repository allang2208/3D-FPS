#pragma once
#include "CoreMinimal.h"
#include "Components/DynamicMeshComponent.h"
#include "SwiftFalconHookVisual.generated.h"

/** One short-lived owner/observer rendering of a server-confirmed hooked blade. */
UCLASS(Transient)
class USwiftFalconHookVisual : public UDynamicMeshComponent
{
    GENERATED_BODY()
public:
    USwiftFalconHookVisual();
    void Bind(AActor* Victim,FVector HitPoint,FName Bone,const FString& Weapon,float Hold,bool Left);
    void Draw(float SecondsToSnap,bool Shared,bool PlaySnap,bool bTug);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
private:
    void FindHead();
    FVector Anchor() const;
    TWeakObjectPtr<AActor> Target;
    TWeakObjectPtr<class USkeletalMeshComponent> Skin;
    TWeakObjectPtr<class UStaticMeshComponent> Head;
    FName AnchorBone;
    FVector LocalPoint=FVector::ZeroVector;
    FVector LocalNormal=FVector::ForwardVector,LocalAcross=FVector::RightVector;
    FString WeaponInstance;
    float Age=0.f,HoldSeconds=.6f,DrawAge=-1.f,SnapAt=.08f;
    float NextHeadLookup=.08f;
    bool bLeft=false,bShared=false,bPlaySnap=true,bSnapped=false;
    UPROPERTY() TObjectPtr<class UMaterialInterface> Filament;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> Light;
    UPROPERTY() TObjectPtr<class USoundBase> Bite;
    UPROPERTY() TObjectPtr<class USoundBase> Snap;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> Steel;
    UPROPERTY() TObjectPtr<class UMaterialInterface> PreviousSteel;
};
