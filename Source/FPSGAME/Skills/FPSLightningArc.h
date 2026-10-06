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
class UStaticMeshComponent;
class UMaterialInterface;

/** An owned, finite VFX instance. It never deals damage or chooses targets. */
UCLASS(NotBlueprintable,Transient)
class FPSGAME_API AFPSLightningArc : public AActor
{
    GENERATED_BODY()
public:
    AFPSLightningArc();
    void InitializeArc(UNiagaraSystem* System,const FVector& Start,const FVector& End,const FLightningCast& Spell,float Width=1.f,bool bContactLight=true,float Brightness=50.f);
    /** 雷枪柱：悬钟射线同款交叉 ribbon + 首尾虹膜光斑；环绕闪电由组件侧电弧承载。 */
    void InitializeColumn(UStaticMesh* RibbonMesh,UStaticMesh* IrisMesh,UMaterialInterface* BeamMaterial,UMaterialInterface* IrisMaterial,const FVector& Start,const FVector& End,const FLightningCast& Spell,float ChargeRatio=1.f,float WidthScale=1.f);
    void InitializeBladeArc(UNiagaraSystem* System,USceneComponent* BladeAnchor,float Length,int32 Seed);
    float BladeFlash() const;
    void SetBladeLightVisible(bool bVisible);
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY() TObjectPtr<USplineComponent> Path;
    UPROPERTY() TObjectPtr<UNiagaraComponent> FX;
    UPROPERTY() TObjectPtr<UPointLightComponent> ImpactLight;
    float Age=0,Hold=.5f,Fade=.25f,BaseLight=0;
    float BaseBrightness=50.f,BladeLength=1.f;
    TWeakObjectPtr<USceneComponent> BoundBlade;
    bool bBladeAttached=false;
    // ── 联机复制态：服务端生成电弧/雷柱，远端副本自载素材重演表现 ──
    UPROPERTY(Replicated) uint8 NetKind=0; // 0=链式电弧 1=雷枪柱
    UPROPERTY(Replicated) FVector_NetQuantize NetStart;
    UPROPERTY(Replicated) FVector_NetQuantize NetEnd;
    UPROPERTY(Replicated) FLightningCast NetSpell;
    UPROPERTY(Replicated) float NetWidth=1.f,NetBrightness=50.f,NetChargeRatio=1.f;
    UPROPERTY(Replicated) bool NetContactLight=true;
    bool bNetInit=false;
    // 本地生成（蓄力汇聚弧等）的弧不再等复制字段，直接走本地 Tick。
    bool bInitialized=false;
    void NetInit();
};
