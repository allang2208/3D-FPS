#pragma once
#include "KukriRhythm.h"
#include "../RuneSwordRhythm.h"

namespace KukriAttackTiming
{
    // Evaluate already limits speed relative to each blade's own base interval.
    // Both network peers convert that shared clock without a second animation cap.
    inline float PlayRate(double AttackRate)
    {
        return float(AttackRate*KukriRhythm::AttackSeconds/RuneSwordRhythm::AttackEnd);
    }
    // One simultaneous pose clock, averaging the two independently capped durations.
    inline float PairedPlayRate(float MainRate,float OffhandRate)
    {
        return 2.f/(1.f/MainRate+1.f/OffhandRate);
    }
    inline float DualThrustRecoverySeconds(float MainRate,float OffhandRate)
    {
        return (KukriRhythm::DualThrustSeconds-KukriRhythm::DualThrustLungeStart)/PairedPlayRate(MainRate,OffhandRate);
    }
}
