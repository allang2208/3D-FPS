#include "M10PoisonGas.h"
#include "M10Mawcrawler.h"
#include "HandBrainMonster.h"
#include "PoisonMaggotProjectile.h"
#include "FPSCombatHealthComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "UObject/ConstructorHelpers.h"

AM10PoisonGas::AM10PoisonGas()
{
    Radius=480.f; // 1.5x local coverage; retain the Slag smoke's 8 s hold + 1.5 s fade.
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> FX(TEXT("/Game/Monsters/M10Mawcrawler/CombatPaceV10/NS_M10LocalPoisonGas.NS_M10LocalPoisonGas"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> View(TEXT("/Game/Monsters/M10Mawcrawler/LocalGasV8/M_M10LocalGasBlindView.M_M10LocalGasBlindView"));
    GetSmokeComponent()->SetAsset(FX.Object);BlindViewOverride=View.Object;
    // The lingering cloud can be relevant after its emitting monster moves away.
    bNetUseOwnerRelevancy=false;SetNetCullDistanceSquared(FMath::Square(3500.f));
}
bool AM10PoisonGas::ShouldEmit() const
{
    // Remote clients consume the cloud's replicated emission flag. Its owner
    // and attack state can arrive later on a different actor channel.
    if(!HasAuthority())return true;
    const auto* Monster=Cast<AM10Mawcrawler>(GetOwner());
    return IsValid(Monster)&&!Monster->Dead()&&Monster->State==EM10State::RearGas;
}
void AM10PoisonGas::GetEmissionSources(FVector (&Origins)[3],FVector& Drift) const
{
    const auto* Monster=Cast<AM10Mawcrawler>(GetOwner());
    for(int32 I=0;I<3;++I)Origins[I]=Monster?Monster->RearGasOutlet(I):GetActorLocation();
    Drift=FVector(0,0,12);
    // Puff centres rise over their birth locations; the shared radius growth
    // supplies radial diffusion. Visual smoke and exposure use the same motion.
    // Limit upward travel at a ceiling instead of projecting a rearward jet.
    const float Lifetime=SmokeLifetime+1.5f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M10GasTravel),false,this);Query.AddIgnoredActor(GetOwner());
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(const auto* PC=It->Get())Query.AddIgnoredActor(PC->GetPawn());
    float Fraction=1.f;
    for(const FVector& Origin:Origins)
    {
        FHitResult Hit;
        if(GetWorld()->LineTraceSingleByChannel(Hit,Origin,Origin+Drift*Lifetime+FVector(0,0,.45f*Lifetime*Lifetime),ECC_Visibility,Query))
            Fraction=FMath::Min(Fraction,FMath::Max(0.f,Hit.Time-.04f));
    }
    Drift*=Fraction;
}
void AM10PoisonGas::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!HasAuthority())return;
    TSet<TWeakObjectPtr<APawn>> Inside;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();APawn* Pawn=PC?PC->GetPawn().Get():nullptr;
        auto* HealthComponent=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(!HealthComponent||HealthComponent->IsDead())continue;
        FVector Eye;FRotator Rotation;Pawn->GetActorEyesViewPoint(Eye,Rotation);
        if(PC->IsLocalController()&&PC->PlayerCameraManager)Eye=PC->PlayerCameraManager->GetCameraLocation();
        if(!ContainsExposedEye(Eye,Pawn))continue;
        const TWeakObjectPtr<APawn> Key(Pawn);Inside.Add(Key);
        float* Previous=ExposureSeconds.Find(Key);
        if(!Previous){ExposureSeconds.Add(Key,0.f);continue;}
        *Previous+=DeltaSeconds;
        while(*Previous>=1.f&&!HealthComponent->IsDead())
        {
            *Previous-=1.f;
            if(HealthComponent->IsInvulnerable())continue;
            auto* Poison=Pawn->FindComponentByClass<UMaggotPoisonComponent>();
            if(!Poison){Poison=NewObject<UMaggotPoisonComponent>(Pawn);Pawn->AddInstanceComponent(Poison);Poison->RegisterComponent();}
            // Use the shared player poison path: stack badge, cleansing, immunity
            // and five-second decay remain consistent with other monster poison.
            Poison->AddStack(this);
            UGameplayStatics::ApplyDamage(Pawn,MagicDamagePerSecond,GetInstigatorController(),this,UHandBrainMagicDamage::StaticClass());
        }
    }
    for(auto It=ExposureSeconds.CreateIterator();It;++It)
        if(!It.Key().IsValid()||!Inside.Contains(It.Key()))It.RemoveCurrent();
}
