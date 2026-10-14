#include "NurseZombie.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"

void ANurseZombie::MulticastPounceLanding_Implementation(FVector_NetQuantize Location,
    FVector_NetQuantizeNormal Normal,FVector_NetQuantizeNormal Forward,float Radius,float Angle,
    bool bPlaySound,double StartedAt)
{
    if (GetNetMode()==NM_DedicatedServer) return;
    const auto* GS=GetWorld()->GetGameState();
    const double Now=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    if (Now-StartedAt>.6) return;
    auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>();
    if (!FX) return;
    for (FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();
        if (!PC || !PC->IsLocalController() || !PC->GetPawn()) continue;
        if (auto* Camera=PC->GetPawn()->FindComponentByClass<UCameraComponent>())
        {
            FHitResult Ground;
            Ground.bBlockingHit=true;
            Ground.Location=Ground.ImpactPoint=Location;
            Ground.Normal=Ground.ImpactNormal=Normal;
            FX->SpawnPounceLanding(Ground,Forward,Radius,Angle,Camera,this,bPlaySound);
            break;
        }
    }
}
