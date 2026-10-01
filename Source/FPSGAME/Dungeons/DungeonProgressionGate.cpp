#include "DungeonProgressionGate.h"
#include "DungeonRunSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"

ADungeonProgressionGate::ADungeonProgressionGate()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("GateRoot"));
    Leaf=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AuthoredShutter"));Leaf->SetupAttachment(RootComponent);
    Leaf->SetMobility(EComponentMobility::Movable);Leaf->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Leaf->SetGenerateOverlapEvents(false);Leaf->SetCanEverAffectNavigation(false);
    Blocker=CreateDefaultSubobject<UBoxComponent>(TEXT("ShutterBlocker"));Blocker->SetupAttachment(RootComponent);
    Blocker->SetMobility(EComponentMobility::Movable);Blocker->SetCollisionProfileName(TEXT("BlockAll"));
    Blocker->SetGenerateOverlapEvents(false);Blocker->SetCanEverAffectNavigation(false);
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.TickInterval=.2f;Tags.Add(TEXT("Dungeon.ProgressionGate"));
}

void ADungeonProgressionGate::Configure(UStaticMesh* Mesh,int32 NodeId,bool bAnyRoute,const FVector& ClearSize,const FVector& Travel)
{
    Leaf->SetStaticMesh(Mesh);RequiredNode=NodeId;bRequireAnyRoute=bAnyRoute;Opening=ClearSize;Lift=Travel;
    Blocker->SetRelativeLocation(FVector(0,0,Opening.Z*.5));Blocker->SetBoxExtent(Opening*.5);
    Blocker->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    SetActorTickEnabled(GetWorld()&&GetWorld()->IsGameWorld());
}

void ADungeonProgressionGate::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!bReleased)
    {
        const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
        if(!Run||!Run->IsRunActive()||!Run->IsRoomCleared(RequiredNode))return;
        if(bRequireAnyRoute&&!Run->AnyThemedRouteCleared())
        {
            // Report the first remaining route barrier once, not every polling tick.
            const FName WaitingTag(TEXT("DungeonGate.WaitingForRouteClear"));
            if(!ActorHasTag(WaitingTag))
            {
                Tags.Add(WaitingTag);
                for(int32 R=1;R<=3;++R)
                {
                    const FString Route=FString::Printf(TEXT("Route%d"),R);FString Pending;
                    for(const auto& Node:Run->AllNodes())
                        if(Node.bCombatRoom&&Node.Route==Route&&!Run->IsRoomCleared(Node.Id))
                            Pending+=FString::Printf(TEXT(" %d:%s"),Node.Id,*Node.Module);
                    UE_LOG(LogTemp, Display, TEXT("[DungeonProgressionGate] 档案房 %d 已清除；等待任一路线完成，%s 未清房：%s"),
                        RequiredNode,*Route,*Pending);
                }
            }
            return;
        }
        bReleased=true;SetActorTickInterval(0.f);
        UE_LOG(LogTemp, Display, TEXT("[DungeonProgressionGate] 放行：Node=%d AnyRoute=%s Gate=%s"),
            RequiredNode, bRequireAnyRoute ? TEXT("是") : TEXT("否"), *GetName());
    }
    OpenFraction=FMath::Min(1.f,OpenFraction+DeltaSeconds/2.8f);
    const FVector Offset=Lift*FMath::SmoothStep(0.f,1.f,OpenFraction);
    Leaf->SetRelativeLocation(Offset);
    Blocker->SetRelativeLocation(Offset+FVector(0,0,Opening.Z*.5));
    if(Offset.Z>=Opening.Z||OpenFraction>=1.f)Blocker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(OpenFraction>=1.f){Leaf->SetHiddenInGame(true);SetActorTickEnabled(false);}
}
