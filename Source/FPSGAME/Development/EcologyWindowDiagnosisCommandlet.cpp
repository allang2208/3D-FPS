#include "EcologyWindowDiagnosisCommandlet.h"
#include "../Movement/FPSTraversalComponent.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "EngineUtils.h"
#include "UObject/Package.h"

int32 UEcologyWindowDiagnosisCommandlet::Main(const FString& Params)
{
    UPackage* Package=LoadPackage(nullptr,TEXT("/Game/GameMaps/Design/L_EcoNursery_Subject"),LOAD_None);
    UWorld* SourceWorld=Package?UWorld::FindWorldInPackage(Package):nullptr;
    if (!SourceWorld) return 1;
#if WITH_EDITOR
    FAssetCompilingManager::Get().FinishAllCompilation();
#endif
    // Loaded packages are inactive worlds in a commandlet. Reproduce their actual
    // mesh collision and transforms in a query-only game world, without BeginPlay.
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("EcologyWindowDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if (!World) return 1;
    int32 Copied=0;
    for (AActor* SourceActor:SourceWorld->PersistentLevel->Actors)
    {
        if (!SourceActor || !SourceActor->GetActorEnableCollision()) continue;
        TInlineComponentArray<UStaticMeshComponent*> Components(SourceActor);
        for (auto* Source:Components)
        {
            // Broken panes immediately lose collision in UWardBreakableGlass::BreakAt.
            if (Source->IsA<UWardBreakableGlass>() || !Source->GetStaticMesh() || !Source->IsQueryCollisionEnabled()) continue;
            auto* Actor=World->SpawnActor<AActor>();
            Actor->Tags=SourceActor->Tags;
            auto* Copy=NewObject<UStaticMeshComponent>(Actor);
            Actor->AddInstanceComponent(Copy); Actor->SetRootComponent(Copy);
            Copy->SetMobility(EComponentMobility::Static);
            Copy->SetStaticMesh(Source->GetStaticMesh());
            Copy->SetCollisionProfileName(Source->GetCollisionProfileName());
            Copy->SetCollisionEnabled(Source->GetCollisionEnabled());
            Copy->SetCollisionObjectType(Source->GetCollisionObjectType());
            Copy->SetCollisionResponseToChannels(Source->GetCollisionResponseToChannels());
            Copy->ComponentTags=Source->ComponentTags;
            Copy->RegisterComponent();
            Actor->SetActorTransform(Source->GetComponentTransform());
            ++Copied;
            if (Source->GetStaticMesh()->GetName().Contains(TEXT("Floor")) || Source->GetStaticMesh()->GetName().Contains(TEXT("Sill")))
                UE_LOG(LogTemp,Display,TEXT("ECO_COLLIDER %s transform=%s bounds=%s extent=%s physics=%d trace=%d"),
                    *Source->GetStaticMesh()->GetName(),*Source->GetComponentTransform().ToHumanReadableString(),
                    *Copy->Bounds.Origin.ToString(),*Copy->Bounds.BoxExtent.ToString(),Copy->IsPhysicsStateCreated(),
                    Copy->GetBodySetup()?(int32)Copy->GetBodySetup()->GetCollisionTraceFlag():-1);
        }
    }
    UE_LOG(LogTemp,Display,TEXT("ECO_COLLIDERS copied=%d"),Copied);
    auto* Character=World->SpawnActor<ACharacter>();
    Character->GetCapsuleComponent()->SetCapsuleSize(42,96);
    Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    auto* Detector=NewObject<UFPSTraversalComponent>(Character);
    Character->AddInstanceComponent(Detector);Detector->RegisterComponent();
    for (float X:{-1160.f,-1000.f,-820.f}) for (float Y:{-235.f,-240.f,-365.f})
    {
        Character->SetActorLocation(FVector(X,Y,98));
        Character->SetActorRotation(FRotator(0,Y < -300.f?90.f:-90.f,0));
        FHitResult Ground;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(EcologyWindowGround),false,Character);
        World->LineTraceSingleByProfile(Ground,FVector(X,Y,100),FVector(X,Y,-100),TEXT("Pawn"),Query);
        UE_LOG(LogTemp,Display,TEXT("ECO_GROUND x=%.1f y=%.1f blocking=%d point=%s normal=%s mesh=%s"),
            X,Y,Ground.bBlockingHit,*Ground.ImpactPoint.ToString(),*Ground.ImpactNormal.ToString(),
            Ground.GetComponent()?*Ground.GetComponent()->GetName():TEXT("none"));
        const auto T=Detector->FindTarget(true,true);
        UE_LOG(LogTemp,Display,TEXT("ECO_WINDOW x=%.1f y=%.1f action=%d reason=%s H=%.2f D=%.2f edge=%.2f top=%d landing=%d approach=%d vault=%d mantle=%d obstacle=%s"),
            X,Y,(int32)T.Action,*T.Reason,T.Probe.Height,T.Probe.Depth,T.Probe.EdgeDistance,
            T.Probe.bTopStandingSpace,T.Probe.bLandingStandingSpace,T.Probe.bApproachClear,T.Probe.bVaultPathClear,T.Probe.bMantlePathClear,
            Cast<UStaticMeshComponent>(T.Obstacle)?*CastChecked<UStaticMeshComponent>(T.Obstacle)->GetStaticMesh()->GetName():TEXT("none"));
    }
    return 0;
}
