#include "FPSAttackQuery.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"

FFPSAttackQuery::FFPSAttackQuery(FName Tag,const TStatId& Stat,bool Complex,const AActor* Attacker)
    : FCollisionQueryParams(Tag,Stat,Complex,Attacker)
{
    if(Attacker)
        if(const auto* Ride=Attacker->FindComponentByClass<UHorseRiderComponent>();Ride&&Ride->Active())
            AddIgnoredActor(Ride->GetMount());
}
