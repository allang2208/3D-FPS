#include "HeQueArenaNavigation.h"
#include "HeQueMonster.h"
#include "../Dungeons/DungeonRunSubsystem.h"

FVector HeQueArenaNavigation::Goal(const AHeQueMonster& Boss,const FVector& TargetFeet)
{
    // The control balconies are deliberately player-sized. Pursue a visible
    // elevated target from authored floor positions, never onto an unreachable
    // upper NavMesh or by projecting through a floor. Attacks retain sight tests.
    if(FMath::Abs(TargetFeet.Z-Boss.GetNavAgentLocation().Z)<=100.f)return TargetFeet;
    const auto* Run=UDungeonRunSubsystem::Get(Boss.GetWorld());
    const auto* Room=Run?Run->NodeById(Run->NodeNearPosition(Boss.Home)):nullptr;
    if(!Room||Room->Module!=TEXT("BossPumpHall")||Room->DistanceSquared(TargetFeet)>FMath::Square(20.))return TargetFeet;
    const FVector* Best=nullptr;double Distance=TNumericLimits<double>::Max();
    for(const FVector& Position:Room->NavigationAnchors)
    {
        if(FMath::Abs(Position.Z-Boss.GetNavAgentLocation().Z)>100.f)continue;
        const double Candidate=FVector::DistSquared2D(Position,TargetFeet);
        if(Candidate<Distance){Distance=Candidate;Best=&Position;}
    }
    return Best?*Best:TargetFeet;
}
