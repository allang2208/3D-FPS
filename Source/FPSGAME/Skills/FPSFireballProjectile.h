#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FireballTypes.h"
#include "FPSFireballProjectile.generated.h"
class APawn;
class UFPSFireballComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USphereComponent;
class USoundBase;
class UMaterialInterface;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInstanceDynamic;

UCLASS()
class FPSGAME_API AFPSFireballProjectile : public AActor
{
    GENERATED_BODY()
    friend class UFPSFireballComponent;
public:
    AFPSFireballProjectile();
    void Prepare(UFPSFireballComponent* Ability,APawn* Caster,const FFireballCast& Snapshot,UNiagaraSystem* CoreFX,UNiagaraSystem* TrailFX,UNiagaraSystem* ImpactFX,UMaterialInterface* WaveMaterial,USoundBase* HitSound);
    void Launch();
    /** 联机服务端入口：按客户端上报的瞄准点直接发射（等价锁定预览后 Launch）。 */
    void LaunchAt(const FVector& AimPoint);
    bool IsFlying() const { return bFlying; }
    const FFireballCast& Snapshot() const {return Cast;}
    /** Hold-to-preview: red segment from the hovering orb to its predicted contact. */
    void SetAimPreviewActive(bool bActive);
    /** Key release commits the aim target; the orb follows until gesture contact. */
    void CommitAimPreview();
    bool IsAimPreviewActive() const {return bAimPreview;}
    static FVector HoverPosition(APawn* Caster);
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UFUNCTION() void OnRep_Finished();
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Core;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Trail;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> Explosion;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> Wave;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    TWeakObjectPtr<UFPSFireballComponent> Source;
    /** 联机：射手随 actor 复制；远端副本据此懒解析 Source 组件与施法者归属。 */
    UPROPERTY(Replicated) TObjectPtr<APawn> Shooter;
    FFireballCast Cast;
    /** 联机：FFireballCast 非 USTRUCT，客户副本只需表现/弹道相关的这几个字段。 */
    UPROPERTY(Replicated) float NetHoverDuration=30.f;
    UPROPERTY(Replicated) float NetGravity=400.f;
    UPROPERTY(Replicated) float NetRange=1800.f;
    UPROPERTY(Replicated) float NetRadius=200.f;
    /** 爆炸事件复制：位置/法线先于标志位落定，远端 OnRep 直接播同款表现。 */
    UPROPERTY(Replicated) FVector_NetQuantize NetExplodePoint=FVector::ZeroVector;
    UPROPERTY(Replicated) FVector_NetQuantize NetExplodeNormal=FVector::UpVector;
    UPROPERTY(Replicated) uint8 bNetSurfaceHit=0;
    FVector Velocity=FVector::ZeroVector;
    /** Ballistic launch state: the flight and the preview share this integration exactly. */
    FVector LaunchPosition=FVector::ZeroVector,LaunchVelocity=FVector::ZeroVector;
    TArray<FVector> PreviewPoints;
    UPROPERTY(Transient) FVector PreviewAimPoint=FVector::ZeroVector;
    bool bWaterContact=false;
    float Age=0,Distance=0,FlightAge=0,ImpactAge=0,ImpactLightPeak=0;
    /** 联机：飞行/爆散相位随 actor 复制，远端副本据此演同一条表现链。 */
    UPROPERTY(Replicated) bool bFlying=false;
    UPROPERTY(ReplicatedUsing=OnRep_Finished) bool bFinished=false;
    bool bAimPreview=false;
    bool bPreviewLaunchLocked=false;
    UPROPERTY(Transient) TObjectPtr<class ULineBatchComponent> AimPreviewLines;
    /** 爆炸表现是否已在本地播过（服务端 Explode 与远端 OnRep 共用一条表现路径）。 */
    uint8 bExplosionPresented=0;
    void UpdateHover();
    void UpdateFlightFX(const FVector& PreviousPosition);
    void RefreshAimPreview();
    void Explode(const FHitResult* Hit);
    /** 爆炸表现：FX/声音/草压/冲击环——服务端与远端副本共用，不含结算。 */
    void PresentExplosion(const FVector& Contact,const FVector& Normal,bool bSurfaceHit);
    /** 客户副本的施法者侧字段回填（NetXxx→Cast），并懒绑 Source/Active。 */
    void ResolveNetState();
    /** 远端副本不跑 Prepare：FX 资产经 Source 组件侧装载好后回填。 */
    void SetPresentationAssets(UNiagaraSystem* CoreFX,UNiagaraSystem* TrailFX,UNiagaraSystem* ImpactFX,UMaterialInterface* WaveMaterial,USoundBase* HitSound);
    uint8 bAssetsAttached=0;
    FVector ClientPrevPos=FVector::ZeroVector;
};

/** Short, world-depth-tested shockwave. Its visual lifetime is independent of damage. */
UCLASS()
class FPSGAME_API AFireballShockwave : public AActor
{
    GENERATED_BODY()
public:
    AFireballShockwave();
    void Setup(UMaterialInterface* Material,float Radius,bool bSurfaceHit);
    virtual void Tick(float Delta) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Dynamic;
    UPROPERTY() TObjectPtr<UStaticMesh> AirShell;
    float Age=0,MaxRadius=100;
};
