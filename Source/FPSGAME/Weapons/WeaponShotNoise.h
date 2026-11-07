#pragma once
#include "GameFramework/Pawn.h"
#include "Perception/AISense_Hearing.h"
#include "SniperSuppressorAssets.h"

namespace WeaponShotNoise
{
inline void Report(APawn* Shooter,const FString& Definition,const FString& Muzzle,bool Suppressed)
{
    if(SniperSuppressorAssets::Supports(Definition)&&Muzzle==SniperSuppressorAssets::Part)return;
    UAISense_Hearing::ReportNoiseEvent(Shooter,Shooter->GetActorLocation(),1.f,Shooter,Suppressed?1000.f:3600.f,
        Suppressed?TEXT("GunshotSuppressed"):TEXT("Gunshot"));
}
}
