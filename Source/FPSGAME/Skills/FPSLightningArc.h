#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LightningTypes.h"
#include "FPSLightningArc.generated.h"
class USplineComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USceneComponent;
class UStaticMesh;
class UMaterialInterface;

/** An owned, finite VFX instance. It never deals damage or chooses targets. */
UCLASS(NotBlueprintable,Transient)
class FPSGAME_API AFPSLightningArc : public AActor
{
    GENERATED_BODY()
public:
    AFPSLightningArc();
    void InitializeArc(UNiagaraSystem* System,const FVector& Start,const FVector& End,const FLightningCast& Spell,float Width=1.f,bool bContactLight=true,float Brightness=50.f);
    void InitializeColumn(UStaticMesh* Tube,UMaterialInterface* BodyMaterial,UMaterialInterface* FilamentMaterial,const FVector& Start,const FVector& End,const FLightningCast& Spell);
    void InitializeBladeArc(UNiagaraSystem* System,USceneComponent* BladeAnchor,float Length,int32 Seed);
    float BladeFlash() const;
    void SetBladeLightVisible(bool bVisible);
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<USplineComponent> Path;
    UPROPERTY() TObjectPtr<UNiagaraComponent> FX;
    UPROPERTY() TObjectPtr<UPointLightComponent> ImpactLight;
    float Age=0,Hold=.5f,Fade=.25f,BaseLight=0;
    float BaseBrightness=50.f,BladeLength=1.f;
    TWeakObjectPtr<USceneComponent> BoundBlade;
    bool bBladeAttached=false;
};
