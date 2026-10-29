#pragma once
#include "CoreMinimal.h"

class APawn;
class AActor;
class UColdSteelStatusModel;

/** Server-local receipt. No save state or animation assets are needed by a server. */
struct FKukriAttackReceipt
{
    uint32 Serial=0;
    uint32 MasterySerial=0;
    TWeakObjectPtr<APawn> Pawn;
    TWeakObjectPtr<UColdSteelStatusModel> RewardModel;
    FString Main,Offhand;
    bool Dash=false;
    uint8 Stage=0;
    double Started=0.,Until=0.;
    float ContactStart[2]={},ContactEnd[2]={};
    float ThrustRate=1.f;
    float DashKnockback=0.f;
    int32 Hits=0,Kills=0;
    FVector Direction=FVector::ForwardVector;
    TSet<TWeakObjectPtr<AActor>> Targets[2];
};

namespace KukriAttackReceipt
{
inline bool SupportedMeta(uint8 Meta)
{return Meta==0||Meta==0x10||Meta==0x14||Meta==0x16||Meta==0x20||Meta==0x80;}
// Same author-time tempo and hand-over as AdvanceAttack; computed once at commit.
float Seconds(int32 Stage,bool Dual,float AuthorTime,float MainRate,float OffhandRate);
float Length(int32 Stage,bool Dual);
}
