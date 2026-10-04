#pragma once
#include "CoreMinimal.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Combat/MonsterToughnessTypes.h"
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
    // 普通怪显示累积值；精英以上显示剩余韧性。阈值 0 视为无韧性栏。
    float Toughness = 0.f;
    float ToughnessThreshold = 0.f;
    float Opacity = 0.f;
    bool bKilled = false;
    EMonsterToughnessPhase ToughnessPhase=EMonsterToughnessPhase::Legacy;
    float ToughnessPhaseRemaining=0.f;
};
