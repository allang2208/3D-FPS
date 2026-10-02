#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FPSPracticeTarget.generated.h"

class UStaticMeshComponent;
class UTextRenderComponent;
class UStaticMesh;

/** 主神空间训练靶（2026-10-02）：圆环靶面 + 木质三脚架道具，承接所有武器命中。
 *  伤害从武器侧统一经 UGameplayStatics::ApplyPointDamage/ApplyRadialDamage 收口，
 *  本靶只监听 OnTakePointDamage/OnTakeRadialDamage/OnTakeAnyDamage：
 *  - 命中点浮出伤害数字（上浮渐隐）；
 *  - 头顶牌显示滚动窗口 DPS、累计伤害与击数（5s 窗口、4s 无命中重开一节）。
 *  同一次 TakeDamage 会先广播 Point/Radial 再广播 Any——按帧去重，Any 只兜底
 *  非点/径向的通用伤害路径（持续伤害、直接 ApplyDamage 等）。
 *  Hub（DayNight_Lighting）为单机会话，不做属性复制。 */
UCLASS()
class FPSGAME_API AFPSPracticeTarget : public AActor
{
    GENERATED_BODY()
public:
    AFPSPracticeTarget();
    /** 清空累计/窗口统计与浮空数字。 */
    void ResetSession();
    /** 要害判定入口（ColdSteelSkills::IsCriticalHit 调用）：命中点落在靶心正面
     *  （网格本地 y=0/z=150、半径 BullseyeRadius、x>=BullseyeMinX）视为暴击区；
     *  武器侧要害/暴击倍率照常生效，浮空数字走暴击配色。 */
    bool IsBullseyeHit(const FHitResult& Hit) const;
protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaTime) override;
private:
    UFUNCTION() void OnPointDamage(AActor* DamagedActor,float Damage,class AController* InstigatedBy,FVector HitLocation,class UPrimitiveComponent* HitComponent,FName BoneName,FVector ShotFromDirection,const UDamageType* DamageType,AActor* DamageCauser);
    UFUNCTION() void OnRadialDamage(AActor* DamagedActor,float Damage,const UDamageType* DamageType,FVector Origin,const FHitResult& HitInfo,class AController* InstigatedBy,AActor* DamageCauser);
    UFUNCTION() void OnAnyDamage(AActor* DamagedActor,float Damage,const UDamageType* DamageType,class AController* InstigatedBy,AActor* DamageCauser);
    bool IsBullseyeLocation(const FVector& WorldPoint) const;
    void RecordHit(float Damage,const FVector& Point,bool bBullseye);
    void SpawnDamageText(float Damage,const FVector& Point,bool bBullseye);
    void UpdateSign();
    void FaceCamera(USceneComponent* Component) const;

    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> TargetMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UTextRenderComponent> DpsSign;

    UPROPERTY(EditAnywhere,Category="PracticeTarget") TObjectPtr<UStaticMesh> MeshOverride;
    UPROPERTY(EditAnywhere,Category="PracticeTarget") float WindowSeconds=5.f;
    UPROPERTY(EditAnywhere,Category="PracticeTarget") float IdleResetSeconds=4.f;
    UPROPERTY(EditAnywhere,Category="PracticeTarget") int32 MaxFloatingTexts=24;
    UPROPERTY(EditAnywhere,Category="PracticeTarget") float FloatingLifeSeconds=1.1f;
    /** 靶心暴击区（与 build_mesh.py 几何同步：靶心圆盘 r=9 占 x 7.8..9.0，面心 y=0/z=150）。 */
    UPROPERTY(EditAnywhere,Category="PracticeTarget") float BullseyeCenterZ=150.f;
    UPROPERTY(EditAnywhere,Category="PracticeTarget") float BullseyeRadius=10.5f;
    UPROPERTY(EditAnywhere,Category="PracticeTarget") float BullseyeMinX=7.f;

    struct FPracticeHit { double Time; float Damage; };
    struct FFloatingText { TObjectPtr<UTextRenderComponent> Text; FVector Base; double SpawnTime; float Drift; };
    TArray<FPracticeHit> RecentHits;
    TArray<FFloatingText> Floating;
    double SessionStart=-1.;
    double LastHitTime=-1.;
    float TotalDamage=0.f;
    int32 HitCount=0;
    float RockAmplitude=0.f;
    float RockPhase=0.f;
    float RockSign=1.f;
    float SignAccum=0.f;
    uint64 LastTypedDamageFrame=0;
};
