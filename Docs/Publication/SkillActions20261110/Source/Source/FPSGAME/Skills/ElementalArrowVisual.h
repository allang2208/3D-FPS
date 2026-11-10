#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ElementalArrowTypes.h"
#include "ElementalArrowVisual.generated.h"
class UNiagaraComponent;
class USplineComponent;
class UStaticMeshComponent;
class UStaticMesh;
class USceneComponent;
struct FStreamableHandle;

/** Existing elemental assets, fitted to the real held/flying arrow endpoints. */
UCLASS()
class FPSGAME_API UElementalArrowVisual : public UActorComponent
{
    GENERATED_BODY()
public:
    void Update(EArrowElement Element,const FVector& Tail,const FVector& Tip,float Delta,bool bFlying,bool bWorldPresentation=false,USceneComponent* ArrowSource=nullptr);
    void Clear();
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
private:
    EArrowElement Current=EArrowElement::None;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> Effects;
    UPROPERTY(Transient) TArray<TObjectPtr<USplineComponent>> Paths;
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> Assets;
    TSharedPtr<FStreamableHandle> Load;
    FVector Previous=FVector::ZeroVector,Wind=FVector::ZeroVector;
    float Age=0,EnvironmentAge=0,FluidDetail=1;
    bool bReady=false,bBuilt=false;
    FVector FireBase=FVector::ZeroVector,FireTip=FVector::ZeroVector;
    FVector FireBaseFlow=FVector::ZeroVector,FireTipFlow=FVector::ZeroVector;
    FVector FireSourceScale=FVector::OneVector;
    TWeakObjectPtr<UStaticMesh> FireGeometry;
    bool bFireHistory=false;
    void Build(const FVector& Tail,const FVector& Tip);
    void UpdateWarmFire(const FVector& Tail,const FVector& Tip,float Delta,bool bFlying,bool bWorldPresentation,float Detail,USceneComponent* ArrowSource);
    void UpdateColdMist(const FVector& Tail,const FVector& Tip,float Delta,bool bFlying,bool bWorldPresentation,float Detail,USceneComponent* ArrowSource);
};
