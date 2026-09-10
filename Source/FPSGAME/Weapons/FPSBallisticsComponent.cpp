#include "FPSBallisticsComponent.h"
#include "FPSWeaponFXComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

UFPSBallisticsComponent::UFPSBallisticsComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UFPSBallisticsComponent::Launch(FVector Start,FVector Direction,float SpeedCM,float RangeCM,float Damage,UFPSWeaponFXComponent* FX,USoundBase* Headshot)
{
    if(!GetWorld()||!FMath::IsFinite(SpeedCM)||SpeedCM<=0||RangeCM<=0||Direction.IsNearlyZero())return;
    WeaponFX=FX;HeadshotSound=Headshot;
    Rounds.Add({Start,Direction.GetSafeNormal(),SpeedCM,RangeCM,Damage,GetWorld()->GetTimeSeconds()});
    SetComponentTickEnabled(true);
}
void UFPSBallisticsComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Type,Fn);
    const double Now=GetWorld()->GetTimeSeconds();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FlyingRound),true,GetOwner());Params.bReturnPhysicalMaterial=true;
    const auto* Pawn=Cast<APawn>(GetOwner());
    for(int32 I=Rounds.Num()-1;I>=0;--I)
    {
        auto& R=Rounds[I];const float Distance=FMath::Min(R.Remaining,R.Speed*static_cast<float>(FMath::Max(0.,Now-R.Timestamp)));
        R.Timestamp=Now;if(Distance<=0)continue;
        const FVector End=R.Position+R.Direction*Distance;FHitResult Hit;
        if(GetWorld()->LineTraceSingleByChannel(Hit,R.Position,End,ECC_Visibility,Params))
        {
            ++ImpactCount;
            if(Hit.GetActor())UGameplayStatics::ApplyPointDamage(Hit.GetActor(),R.Damage,R.Direction,Hit,Pawn?Pawn->GetController():nullptr,GetOwner(),nullptr);
            if(WeaponFX)WeaponFX->OnImpact(Hit);
            if(HeadshotSound&&Hit.BoneName.ToString().Contains(TEXT("head"),ESearchCase::IgnoreCase))UGameplayStatics::PlaySound2D(this,HeadshotSound,.630957f);
            Rounds.RemoveAtSwap(I);continue;
        }
        R.Position=End;R.Remaining-=Distance;
        if(R.Remaining<=KINDA_SMALL_NUMBER)Rounds.RemoveAtSwap(I);
    }
    if(Rounds.IsEmpty())SetComponentTickEnabled(false);
}
