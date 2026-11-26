#pragma once

#include "CoreMinimal.h"

class APawn;
struct FColdSteelItem;

namespace RingChainRebound
{
    constexpr double Window = 3.;
    struct FProgress
    {
        uint32 LastSwing = 0;
        double FirstHitAt = -1.;
        double ReadyUntil = -1.;

        // Compare using the same addition as the grant, including its exact first instant.
        bool IsReady(double At) const { return ReadyUntil >= 0. && At+Window >= ReadyUntil && At <= ReadyUntil; }
        bool Hit(uint32 Swing,double Now)
        {
            if(!Swing || (LastSwing && int32(Swing-LastSwing)<=0))return false;
            LastSwing=Swing;
            if(IsReady(Now))return false;
            if(FirstHitAt<0. || Now>FirstHitAt+Window)
            {
                FirstHitAt=Now;
                return false;
            }
            FirstHitAt=-1.;
            ReadyUntil=Now+Window;
            return true;
        }
    };

    // Input timestamps, when supplied, use synchronized server world time.
    bool IsReady(APawn* Pawn,const FColdSteelItem& Item,double StartedAt = -1.);
    bool Consume(APawn* Pawn,const FColdSteelItem& Item,double StartedAt = -1.);
}
