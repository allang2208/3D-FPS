#include "VillageDefenseCombat.h"
#include "VillageDefenseSection.h"
#include "ChapelShrine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "NavigationSystem.h"

FVector VillageDefenseCombat::Aim(const AActor* Target,const FVector& From)
{
    if(const auto* Wall=Cast<AVillageDefenseSection>(Target))return Wall->TargetPoint(From);
    if(const auto* Shrine=Cast<AChapelShrine>(Target))return Shrine->GetRaidTargetPoint(From);
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
