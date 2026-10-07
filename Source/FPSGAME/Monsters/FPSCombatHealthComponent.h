#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSCombatHealthComponent.generated.h"

UCLASS(ClassGroup=(Combat), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSCombatHealthComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Replicated, Category="Combat") float MaxHealth = 100.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing=OnRep_Health, Category="Combat") float Health = 100.f;
    UFUNCTION(BlueprintPure, Category="Combat") bool IsDead() const { return Health <= 0.f; }
    UFUNCTION(BlueprintPure, Category="Combat") bool IsInvulnerable() const;
    float DamageAfterArmor(float Damage,const UDamageType* Type,AActor* Attacker=nullptr) const;
    void ApplySurvivalDamage(float Amount);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    /**
     * 滞延回放位姿查询：服务端按 25Hz 录制本目标的胶囊中轴（中心+头顶）环形历史，
     * 命中校验按客户端上报的服务端时钟时间戳取目标"当时"的位姿做几何复算。
     * 历史不足/过旧时取最近边界帧；无记录返回 false。
     */
    bool GetLagPose(double ServerTime, FVector& OutCenter, FVector& OutTop) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    UFUNCTION() void OnRep_Health();
    UFUNCTION() void OnDamage(AActor* Actor, float Damage, const UDamageType* Type, AController* Instigator, AActor* Causer);
    UFUNCTION(Client,Reliable) void ClientApplyM10HowlCripple(double ServerExpiresAt);
    UFUNCTION(Client,Reliable) void ClientApplyM27HitStatus(AActor* Source, bool bPounce, bool bBleeding, double ServerHitAt);
    void Respawn();
    void RecordLagPose();
    struct FFPSLagPose { double Time; FVector Center; FVector Top; };
    /** 队首最旧；24 帧 × 40ms ≈ 0.96s，覆盖常规 RTT + 客户端插值延迟。 */
    TArray<FFPSLagPose> LagPoses;
    static constexpr int32 MaxLagPoseEntries = 24;
    static constexpr float LagPoseInterval = 0.04f;
    FTimerHandle RespawnTimer;
};
