#pragma once
#include "CoreMinimal.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Components/ActorComponent.h"
#include "GameFramework/PlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"

/**
 * 法术联机通道的共享小助手（客户端→服务端施法意图）：
 * - Send：把相位/瞄准上下文包进 FColdSteelNetCastRequest 经 ServerCastSpell 上行。
 * - AuthorityModel：服务端结算远端玩家技能时用影子档案，主机/单机回退 GI 单例。
 */
namespace NetCast
{
// Component-local selection keeps its original GI fallback; authority requests
// continue to use AuthorityModel and its remote-player shadow profile.
inline UColdSteelStatusModel* LocalModel(const UActorComponent& Component)
{
    return UnknownSpell::IsCaster(Component.GetOwner())?
        UnknownSpell::Model(Cast<APawn>(Component.GetOwner())):
        (Component.GetWorld()&&Component.GetWorld()->GetGameInstance()?
            Component.GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr);
}

// Receipt owners keep revision checks and clock reads; preserve the float subtraction.
inline float RemainingCooldown(float Cooldown,double ServerAt,double Now)
{
    return FMath::Max(0.f,Cooldown-float(FMath::Max(0.,Now-ServerAt)));
}

inline AColdSteelPlayerState* StateFor(const APawn* Pawn)
{
    const auto* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    return PC ? Cast<AColdSteelPlayerState>(PC->PlayerState) : nullptr;
}

inline uint32 Send(AActor* Owner, FName SkillId, uint8 Phase,
    const FVector& AimPoint = FVector::ZeroVector,
    const FVector& AimNormal = FVector::UpVector,
    uint8 Variant = 0, AActor* Target = nullptr, float Charge = 0.f,
    const FVector& AimAxis = FVector::ForwardVector, uint32 CastId = 0)
{
    auto* State = StateFor(Cast<APawn>(Owner));
    if (!State) return 0;
    FColdSteelNetCastRequest Request;
    Request.SkillId = SkillId; Request.Phase = Phase;
    Request.AimPoint = AimPoint; Request.AimNormal = AimNormal; Request.AimAxis = AimAxis;
    Request.Variant = Variant; Request.Target = Target; Request.Charge = Charge;
    Request.CastId=CastId;
    return State->RequestCastSpell(Request);
}

/** 服务端上远端 pawn 的权威模型（影子档）；主机/本地回退 GI 单例。 */
inline UColdSteelStatusModel* AuthorityModel(APawn* Pawn, UGameInstance* GI)
{
    if (UnknownSpell::IsCaster(Pawn)) return UnknownSpell::Model(Pawn);
    if (auto* Character = Cast<AFPSGAMECharacter>(Pawn))
        if (auto* Shadow = Character->GetNetShadowProfile()) return Shadow;
    return GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
}
}
