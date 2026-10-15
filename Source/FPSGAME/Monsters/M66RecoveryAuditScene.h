#pragma once
#include "CoreMinimal.h"
class UWorld;
class APlayerController;
class AM66IncineratorMonster;
namespace M66RecoveryAuditScene
{
    void Create(UWorld* World);
    FVector SpawnPoint(UWorld* World, bool Held);
    void Observe(APlayerController* PC, AM66IncineratorMonster* Monster);
    void CorpseDetails(AM66IncineratorMonster* Monster);
}
