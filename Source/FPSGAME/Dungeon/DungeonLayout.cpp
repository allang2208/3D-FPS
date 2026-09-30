#include "DungeonLayout.h"
#include "GameFramework/Actor.h"

namespace DungeonLayout
{
bool RecordKill(FDungeonRunState& Run, const AActor* Victim)
{
    if(!Victim||Run.RunId.IsEmpty())return true;
    const FString Prefix=TEXT("DungeonEnemy.")+Run.RunId+TEXT(".");
    for(FName Tag:Victim->Tags)if(Tag.ToString().StartsWith(Prefix))
    {
        const FName Slot(*Tag.ToString().RightChop(Prefix.Len()));
        if(Run.DefeatedEnemies.Contains(Slot))return false;
        Run.DefeatedEnemies.Add(Slot);break;
    }
    return true;
}
}
