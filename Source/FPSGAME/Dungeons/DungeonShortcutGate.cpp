#include "DungeonShortcutGate.h"
#include "DungeonRunSubsystem.h"
#include "DungeonRoomGateDimensions.h"
#include "Components/BoxComponent.h"
#include "NavAreas/NavArea_Null.h"

ADungeonShortcutGate::ADungeonShortcutGate()
{
    NavigationBarrier=CreateDefaultSubobject<UBoxComponent>(TEXT("ShortcutNavigationBarrier"));
    NavigationBarrier->SetupAttachment(RootComponent);
    NavigationBarrier->SetCollisionProfileName(TEXT("BlockAll"));
    NavigationBarrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    NavigationBarrier->SetGenerateOverlapEvents(false);
    NavigationBarrier->bDynamicObstacle=true;
    NavigationBarrier->SetAreaClassOverride(UNavArea_Null::StaticClass());
    NavigationBarrier->SetCanEverAffectNavigation(false);
    Tags.Add(TEXT("Dungeon.ReturnShortcut"));
}

bool ADungeonShortcutGate::ConfigureReturnLink(UDungeonRunSubsystem* InRun,const FDungeonRunDoor& Door,const FString& A,const FString& B)
{
    if(!HasAuthority()||!InRun||!Configure(Door))return false;
    Run=InRun;RouteA=A;RouteB=B;
    NavigationBarrier->SetRelativeLocation(FVector(0,35,Door.Height*.5));
    NavigationBarrier->SetBoxExtent(FVector(Door.Width*.5+10,50,Door.Height*.5));
    NavigationBarrier->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    NavigationBarrier->SetCanEverAffectNavigation(true);
    SetOpenFraction(0.f);SetEncounterLocked(true);SetActorTickInterval(.2f);SetActorTickEnabled(true);
    return true;
}

void ADungeonShortcutGate::Tick(float DeltaSeconds)
{
    if(!HasAuthority()||!Run.IsValid()||!Run->IsRunActive())return;
    if(!bReleased)
    {
        if(!Run->AreRouteObjectivesDefeated(RouteA)||!Run->AreRouteObjectivesDefeated(RouteB))return;
        bReleased=true;SetActorTickInterval(0.f);
    }
    SetOpenFraction(FMath::FInterpConstantTo(NetOpen,1.f,DeltaSeconds,1.f/float(DungeonRoomGateDimensions::TravelSeconds)));
    if(NetOpen>=1.f)
    {
        NavigationBarrier->SetCanEverAffectNavigation(false);
        NavigationBarrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        SetEncounterLocked(false);SetActorTickEnabled(false);ForceNetUpdate();
    }
}
