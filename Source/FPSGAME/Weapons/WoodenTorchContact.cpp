#include "WoodenTorchComponent.h"
#include "WoodenTorchItem.h"
#include "FPSImpactFXSubsystem.h"
#include "MeleeSmallTargetQuery.h"
#include "../Combat/FPSAttackQuery.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"

#include "../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"

namespace
{
    FVector ContactNormal(const FHitResult& Hit)
    {
        return Hit.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER,
            (Hit.TraceStart-Hit.TraceEnd).GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector));
    }
}

UCameraComponent* UWoodenTorchComponent::LocalEmberCamera() const
{
    auto* World=GetWorld();
    const auto* Game=World?World->GetGameInstance():nullptr;
    const auto* PC=Game?Game->GetFirstLocalPlayerController(World):nullptr;
    const auto* View=PC?PC->GetViewTarget():nullptr;
    return View?View->FindComponentByClass<UCameraComponent>():nullptr;
}

void UWoodenTorchComponent::DrawEmbers(const FVector& Point,const FVector& Normal) const
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(auto* Camera=LocalEmberCamera())
        if(auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())FX->SpawnTorchEmbers(Point,Normal,Camera);
}

void UWoodenTorchComponent::EnemyContact(const FHitResult& Hit)
{
    if(!GetOwner()->HasAuthority())return;
    const auto* Victim=Cast<ACharacter>(Hit.GetActor());
    const FVector Normal=ContactNormal(Hit);
    if(Victim&&Victim->GetMesh()&&(Hit.bStartPenetrating||Hit.GetComponent()==Victim->GetCapsuleComponent()))
    {
        const FVector Outward=(GetOwner()->GetActorLocation()-Hit.ImpactPoint).GetSafeNormal(UE_SMALL_NUMBER,Normal);
        FHitResult Skin;
        if(Victim->GetMesh()->LineTraceComponent(Skin,Hit.ImpactPoint+Outward*35.,Hit.ImpactPoint-Outward*35.,
            FCollisionQueryParams(SCENE_QUERY_STAT(TorchContactSkin),false)))
        {
            MulticastEmbers(Skin.ImpactPoint,ContactNormal(Skin),false);
            return;
        }
    }
    MulticastEmbers(Hit.ImpactPoint,Normal,false);
}

void UWoodenTorchComponent::SurfaceContact(const FHitResult& Hit,uint32 OrdinarySwingSerial)
{
    auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled())return;
    const FVector Normal=ContactNormal(Hit);
    DrawEmbers(Hit.ImpactPoint,Normal);
    if(GetNetMode()==NM_Standalone)return;
    if(Pawn->HasAuthority())MulticastEmbers(Hit.ImpactPoint,Normal,true);
    else if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())PS->RequestTorchEmbers(Pawn,OrdinarySwingSerial,Hit.ImpactPoint,Normal);
}


bool UWoodenTorchComponent::PublishSurfaceContact(const FVector& Point,const FVector& Normal,float Reach)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||Point.ContainsNaN()||Normal.ContainsNaN()||Normal.IsNearlyZero())return false;
    const auto Now=GetWorld()->GetTimeSeconds();
    if(Now-LastSurfaceReport<.075)return false;
    LastSurfaceReport=Now;
    const FVector Eye=Pawn->GetMeleeAimTransform().GetLocation();
    if(FVector::DistSquared(Eye,Point)>FMath::Square(Reach))return false;
    FHitResult Contact,Blocker;
    if(!MeleeSmallTargets::BladeScenery(GetWorld(),Pawn,Point+Normal*12.,Point-Normal*12.,Contact))return false;
    FFPSAttackQuery Query(SCENE_QUERY_STAT(TorchEmberCover),false,Pawn);
    if(GetWorld()->LineTraceSingleByChannel(Blocker,Eye,Contact.ImpactPoint+Contact.ImpactNormal*2.,ECC_Visibility,Query)
        &&FVector::DistSquared(Blocker.ImpactPoint,Contact.ImpactPoint)>FMath::Square(10.))return false;
    MulticastEmbers(Contact.ImpactPoint,ContactNormal(Contact),true);
    return true;
}

void UWoodenTorchComponent::MulticastEmbers_Implementation(FVector_NetQuantize10 Point,FVector_NetQuantizeNormal Normal,bool bOwnerPresented)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(bOwnerPresented&&Pawn&&Pawn->IsLocallyControlled())return;
    DrawEmbers(Point,Normal);
}
