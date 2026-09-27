#pragma once

#include "CoreMinimal.h"

namespace MonsterReactionTiming
{
    // Reuse the authored impact and recovery poses. Skip an authored static hold
    // whose endpoints are the same pose, then continuously unload the body.
    // This samples animation only: it never changes control, damage or root motion.
    inline float StaggerSample(float Elapsed,float Remaining,float ClipLength,float ImpactEnd,float RecoveryStart)
    {
        const float Duration=FMath::Max(0.f,Elapsed+Remaining);
        if(Duration<=SMALL_NUMBER || Remaining<=0.f)return ClipLength;
        ImpactEnd=FMath::Clamp(ImpactEnd,0.f,ClipLength);
        RecoveryStart=FMath::Clamp(RecoveryStart,ImpactEnd,ClipLength);
        const float ImpactSeconds=FMath::Min(ImpactEnd,Duration*.3f);
        const float RecoverySeconds=FMath::Min(.3f,Duration*.4f);
        const float SettleSeconds=FMath::Max(SMALL_NUMBER,Duration-ImpactSeconds-RecoverySeconds);
        if(Elapsed<ImpactSeconds)
            return ImpactEnd*FMath::Clamp(Elapsed/FMath::Max(SMALL_NUMBER,ImpactSeconds),0.f,1.f);
        const float MidPose=FMath::Lerp(RecoveryStart,ClipLength,.45f);
        if(Remaining>RecoverySeconds)
        {
            const float T=FMath::Clamp((Elapsed-ImpactSeconds)/SettleSeconds,0.f,1.f);
            return FMath::Lerp(RecoveryStart,MidPose,T*T*(3.f-2.f*T));
        }
        const float T=1.f-FMath::Clamp(Remaining/FMath::Max(SMALL_NUMBER,RecoverySeconds),0.f,1.f);
        return FMath::Lerp(MidPose,ClipLength,T*T*(3.f-2.f*T));
    }
}
