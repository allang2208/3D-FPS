#pragma once
#include "CoreMinimal.h"
#include "../Combat/WeaponDamageTypes.h"
class AActor;

/** Receipt of accepted damage, separate from stagger/animation presentation. */
struct FMonsterHitFeedback
{
    TWeakObjectPtr<AActor> Target;
    FText Name;
    float Damage = 0.f;
    FWeaponDamageResult DamageResult;
    float Health = 0.f;
    float MaxHealth = 0.f;
    // 韧性（2026-09-29）：当前累积 / 阈值（类别×阶级基准表）。阈值 0 视为无韧性栏。
    float Toughness = 0.f;
    float ToughnessThreshold = 0.f;
    float Opacity = 0.f;
    bool bKilled = false;
};
