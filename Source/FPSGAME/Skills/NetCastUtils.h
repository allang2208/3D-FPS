#pragma once
#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
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
inline AColdSteelPlayerState* StateFor(const APawn* Pawn)
{
    const auto* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    return PC ? Cast<AColdSteelPlayerState>(PC->PlayerState) : nullptr;
}

inline void Send(AActor* Owner, FName SkillId, uint8 Phase,
    const FVector& AimPoint = FVector::ZeroVector,
    const FVector& AimNormal = FVector::UpVector,
    uint8 Variant = 0, AActor* Target = nullptr, float Charge = 0.f,
    const FVector& AimAxis = FVector::ForwardVector)
{
    auto* State = StateFor(Cast<APawn>(Owner));
    if (!State) return;
    FColdSteelNetCastRequest Request;
    Request.SkillId = SkillId; Request.Phase = Phase;
    Request.AimPoint = AimPoint; Request.AimNormal = AimNormal; Request.AimAxis = AimAxis;
    Request.Variant = Variant; Request.Target = Target; Request.Charge = Charge;
    State->ServerCastSpell(Request);
}

/** 服务端上远端 pawn 的权威模型（影子档）；主机/本地回退 GI 单例。 */
inline UColdSteelStatusModel* AuthorityModel(APawn* Pawn, UGameInstance* GI)
{
    if (auto* Character = Cast<AFPSGAMECharacter>(Pawn))
        if (auto* Shadow = Character->GetNetShadowProfile()) return Shadow;
    return GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
}
}
