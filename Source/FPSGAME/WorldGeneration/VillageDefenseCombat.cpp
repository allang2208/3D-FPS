#include "VillageDefenseCombat.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterTargeting.h"
#include "../UI/ColdSteelDamageNumberSubsystem.h"
#include "VillageDefenseSection.h"
#include "ChapelShrine.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "NavigationSystem.h"

namespace
{
    TAutoConsoleVariable<float> CVarDefenseDamageNumberRangeCm(
        TEXT("fps.Village.DefenseDamageNumberRangeCm"),
        6500.f,
        TEXT("Maximum distance in cm at which village defense facility damage numbers are shown to host/clients."));
}

FVector VillageDefenseCombat::Aim(const AActor* Target,const FVector& From)
{
    if(const auto* Wall=Cast<AVillageDefenseSection>(Target))return Wall->TargetPoint(From);
    if(const auto* Shrine=Cast<AChapelShrine>(Target))return Shrine->GetRaidTargetPoint(From);
    if(const auto* Pawn=Cast<APawn>(Target))return MonsterTargeting::ContactBody(Pawn)->GetActorLocation();
    return Target?Target->GetActorLocation():From;
}
AVillageDefenseSection* VillageDefenseCombat::Blocking(const APawn* Monster,const AActor* Target)
{
    if(!Monster||!Target||Monster->GetWorld()!=Target->GetWorld())return nullptr;
    if(auto* Wall=Cast<AVillageDefenseSection>(const_cast<AActor*>(Target)))return Wall->BlocksPassage()?Wall:nullptr;
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageDefenseSight),false,Monster);Query.AddIgnoredActor(Target);
    if(Monster->GetWorld()->LineTraceSingleByChannel(Hit,Monster->GetActorLocation(),Aim(Target,Monster->GetActorLocation()),ECC_Visibility,Query))
        if(auto* Wall=Cast<AVillageDefenseSection>(Hit.GetActor());Wall&&Wall->BlocksPassage())return Wall;
    return nullptr;
}
AVillageDefenseSection* VillageDefenseCombat::Reachable(UWorld* World,const FVector& From,const FVector& Goal,
    UNavigationSystemV1* Nav,const ANavigationData* Data,FVector& Approach)
{
    if(!Nav||!Data)return nullptr;
    TArray<AVillageDefenseSection*> Candidates;
    for(TActorIterator<AVillageDefenseSection> It(World);It;++It)
        if(It->BlocksPassage()&&FVector::DistSquared2D(From,It->GetActorLocation())<FMath::Square(22000.))Candidates.Add(*It);
    Candidates.Sort([&](const auto& A,const auto& B)
    {
        auto Cost=[&](const auto& W){return FVector::Dist2D(From,W.GetActorLocation())+.3*FVector::Dist2D(Goal,W.GetActorLocation());};
        return Cost(A)<Cost(B);
    });
    for(int32 I=0;I<FMath::Min(16,Candidates.Num());++I)
    {
        auto* Wall=Candidates[I];const FVector Surface=Wall->TargetPoint(From+FVector(0,0,80));
        const FVector Desired=Surface+(From-Surface).GetSafeNormal2D()*105.;FNavLocation Point;
        if(!Nav->ProjectPointToNavigation(FVector(Desired.X,Desired.Y,Wall->GetActorLocation().Z),Point,FVector(65,65,180),Data))continue;
        FPathFindingQuery Query(nullptr,*Data,From,Point.Location);Query.SetAllowPartialPaths(false);
        if(!Nav->TestPathSync(Query,EPathFindingMode::Regular))continue;
        Approach=Point.Location;return Wall;
    }
    return nullptr;
}
bool VillageDefenseCombat::HasRoute(UWorld* World,const FVector& From,const FVector& Goal,UNavigationSystemV1* Nav,const ANavigationData* Data)
{FVector Approach;return Reachable(World,From,Goal,Nav,Data,Approach)!=nullptr;}

float VillageDefenseCombat::DamageNumberMaxRangeCm()
{
    return FMath::Max(0.f,CVarDefenseDamageNumberRangeCm.GetValueOnGameThread());
}

void VillageDefenseCombat::BroadcastDamageNumber(UWorld* World,AActor* Target,const FVector& FallbackPoint,
    float AppliedDamage,float MagicDamage,bool bCritical,bool bKilled)
{
    if(!World || World->GetNetMode()==NM_Client || AppliedDamage<=0.f)return;
    if(Target)
    {
        if(Target->IsA<AFPSGAMECharacter>())return;
        if(const auto* Pawn=Cast<APawn>(Target);Pawn && Pawn->IsPlayerControlled())return;
    }
    const float MaxRangeCm=DamageNumberMaxRangeCm();
    if(MaxRangeCm<=0.f)return;

    const FVector Anchor=IsValid(Target)?UColdSteelDamageNumberSubsystem::TargetTopAnchor(Target):FallbackPoint;
    float Health=0.f,MaxHealth=0.f;FText Name;
    bool bHasVitals=false;
    if(IsValid(Target))
        if(const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>())
            bHasVitals=Combat->GetVitals(Health,MaxHealth,Name);
    const bool bBig=bCritical || AppliedDamage>=80.f || (bHasVitals && MaxHealth>0.f && AppliedDamage>=MaxHealth*0.10f);

    for(FConstPlayerControllerIterator It=World->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=Cast<AFPSGAMEPlayerController>(It->Get());
        if(!PC)continue;
        FVector ViewerLoc=FVector::ZeroVector;
        if(PC->IsLocalController())
        {
            if(PC->PlayerCameraManager && PC->PlayerCameraManager->GetCameraCacheTime()>0.f)
            {
                FRotator ViewRot=FRotator::ZeroRotator;
                PC->GetPlayerViewPoint(ViewerLoc,ViewRot);
            }
            else if(const APawn* P=PC->GetPawn())
            {
                ViewerLoc=P->GetActorLocation();
            }
            else
            {
                FRotator ViewRot=FRotator::ZeroRotator;
                PC->GetPlayerViewPoint(ViewerLoc,ViewRot);
            }
        }
        else
        {
            ViewerLoc=PC->GetPawn()?PC->GetPawn()->GetActorLocation():PC->GetFocalLocation();
        }
        const float ServerCullCm=PC->IsLocalController()?MaxRangeCm:(MaxRangeCm+900.f);
        if(FVector::DistSquared(ViewerLoc,Anchor)<=FMath::Square(ServerCullCm))
        {
            PC->ClientDefenseDamageNumber(Target,Anchor,AppliedDamage,MagicDamage,bCritical,bKilled,bBig);
        }
    }
}
