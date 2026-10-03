#include "SceneTestPortal.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Components/InputComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"
#include "InputCoreTypes.h"
#include "UI/TransitLoadingSubsystem.h"
#include "Engine/GameInstance.h"

namespace ScenePortalMaps
{
    const TCHAR* Hub = TEXT("/Game/GameMaps/DayNight_Lighting");
    const TCHAR* Hills = TEXT("/Game/GameMaps/L_TemperateHills_Initial");
    const TCHAR* RandomizedDungeon = TEXT("/Game/GameMaps/L_Dungeon_Randomized");

    /** Return-door spacing in the hills; the hub uses its saved layout anchor. */
    constexpr float PortalSpacing = 350.f;
}

ASceneTestPortal::ASceneTestPortal()
{
    PrimaryActorTick.bCanEverTick = false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    for (int32 Index = 0; Index < 3; ++Index)
    {
        UStaticMeshComponent* Frame = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("Frame%d"), Index));
        Frame->SetupAttachment(RootComponent);
        Frame->SetStaticMesh(Cube.Object);
        Frame->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Frame->SetRelativeLocation(Index < 2 ? FVector(0, Index == 0 ? -75 : 75, 110) : FVector(0, 0, 220));
        Frame->SetRelativeScale3D(Index < 2 ? FVector(.15, .15, 2.2) : FVector(.15, 1.65, .15));
    }
    Sign = CreateDefaultSubobject<UTextRenderComponent>(TEXT("DestinationSign"));
    Sign->SetupAttachment(RootComponent);
    Sign->SetRelativeLocation(FVector(12, 0, 260));
    Sign->SetHorizontalAlignment(EHorizTextAligment::EHTA_Center);
    Sign->SetWorldSize(22);
    Sign->SetTextRenderColor(FColor::Cyan);
}

void ASceneTestPortal::Configure(const FString& Map, const FString& Label, const FString& Options, FColor Color)
{
    Destination = Map;
    DestinationOptions = Options;
    DestinationLabel = Label;
    Sign->SetText(FText::FromString(Label + TEXT("\n[E] Travel (within 2m)")));
    Sign->SetTextRenderColor(Color);

    auto* PortalFrame=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Frame.SM_GamedevPortal_Frame"));
    auto* PortalEnergy=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Energy.SM_GamedevPortal_Energy"));
    if(PortalFrame && PortalEnergy)
    {
        TInlineComponentArray<UStaticMeshComponent*> Pieces(this);
        for(auto* Piece:Pieces)
        {
            const FName PieceName=Piece->GetFName();
            if(PieceName==TEXT("Frame0") || PieceName==TEXT("Frame1"))
            {
                const bool Solid=PieceName==TEXT("Frame0");
                Piece->SetStaticMesh(Solid?PortalFrame:PortalEnergy);
                Piece->SetRelativeTransform(FTransform::Identity);
                Piece->SetVisibility(true);
                Piece->SetCollisionProfileName(Solid?TEXT("BlockAll"):TEXT("NoCollision"));
                Piece->SetCollisionEnabled(Solid?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
                Piece->SetGenerateOverlapEvents(false);
                Piece->SetCastShadow(Solid);
            }
            else if(PieceName==TEXT("Frame2"))
            {
                Piece->SetVisibility(false);
                Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            }
        }
        Sign->SetRelativeLocation(FVector(12,0,PortalFrame->GetBounds().Origin.Z+PortalFrame->GetBounds().BoxExtent.Z+45.f));
    }
}

void ASceneTestPortal::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode() == NM_Client) return;
    EnableInput(UGameplayStatics::GetPlayerController(this, 0));
    if (InputComponent)
    {
        InputComponent->BindKey(EKeys::E, IE_Pressed, this, &ASceneTestPortal::UsePortal).bConsumeInput = false;
        InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &ASceneTestPortal::CancelLoading).bConsumeInput = false;
    }
}

bool ASceneTestPortal::IsWithinInteractionRange(const APawn* Pawn) const
{
    if(!Pawn||ActorHasTag(TEXT("DungeonReward.Locked")))return false;
    const FVector Delta=Pawn->GetActorLocation()-GetActorLocation();
    return Delta.SizeSquared2D()<=FMath::Square(200.f)&&FMath::Abs(Delta.Z)<=250.f;
}

void ASceneTestPortal::UsePortal()
{
    APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
    APawn* Pawn = PC ? PC->GetPawn() : nullptr;
    if (bTravelling || !Pawn || PC->bShowMouseCursor || GetNetMode() == NM_Client) return;
    if (!IsWithinInteractionRange(Pawn)) return;
    if (!FPackageName::DoesPackageExist(Destination))
    {
        if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Red, TEXT("Portal destination missing; travel cancelled."));
        UE_LOG(LogTemp, Error, TEXT("ScenePortal: Missing destination %s"), *Destination);
        return;
    }
    bTravelling = true;
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
        Loading->BeginTransition(Destination,FSimpleDelegate::CreateUObject(this,&ASceneTestPortal::CancelLoading));
    if (Destination == ScenePortalMaps::Hills)
    {
        Sign->SetText(FText::FromString(TEXT("Preparing hills...\n[Esc] Cancel")));
        const FString ObjectPath=Destination+TEXT(".")+FPackageName::GetShortName(Destination);
        PreloadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(FSoftObjectPath(ObjectPath),FStreamableDelegate::CreateUObject(this,&ASceneTestPortal::FinishLoading));
        return;
    }
    if(Destination==ScenePortalMaps::RandomizedDungeon||Destination==ScenePortalMaps::Hub)
    {
        GetWorldTimerManager().SetTimer(DungeonTravelTimer,this,&ASceneTestPortal::OpenDestination,.1f,false);
        return;
    }
    OpenDestination();
}

void ASceneTestPortal::OpenDestination()
{
    if(!bTravelling)return;
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Travel %s"), *Destination);
    UGameplayStatics::OpenLevel(this, FName(*Destination), true, DestinationOptions);
}

void ASceneTestPortal::FinishLoading()
{
    if (!bTravelling) return;
    if (!PreloadHandle || !PreloadHandle->GetLoadedAsset())
    {
        CancelLoading();
        Sign->SetText(FText::FromString(DestinationLabel + TEXT(" could not load\n[E] Retry")));
        return;
    }
    UGameplayStatics::OpenLevel(this,FName(*Destination),true,DestinationOptions);
}

void ASceneTestPortal::CancelLoading()
{
    if (!bTravelling) return;
    GetWorldTimerManager().ClearTimer(DungeonTravelTimer);
    if(PreloadHandle){PreloadHandle->CancelHandle();PreloadHandle.Reset();}
    bTravelling=false;
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())Loading->CancelTransition();
    Sign->SetText(FText::FromString(DestinationLabel+TEXT("\n[E] Travel (within 2m)")));
}

void ASceneTestPortal::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DungeonTravelTimer);
    if(PreloadHandle){PreloadHandle->CancelHandle();PreloadHandle.Reset();}
    Super::EndPlay(Reason);
}

int32 ASceneTestPortal::InstallHillsLink(UWorld* World)
{
    if (!World || !World->IsGameWorld() || World->GetNetMode() == NM_Client) return 2;
    const FString Current = UGameplayStatics::GetCurrentLevelName(World, true);
    if (Current != TEXT("DayNight_Lighting") && Current != TEXT("L_TemperateHills_Initial")) return 2;
    APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0);
    if (!Pawn) return 0;
    const FName LinkTag(TEXT("ScenePortal.HillsLink"));
    for (TActorIterator<ASceneTestPortal> It(World); It; ++It)
        if (It->ActorHasTag(LinkTag)) return 1;

    const bool bHills = Current == TEXT("L_TemperateHills_Initial");
    const bool bReturnToHub = bHills;
    const FString Map = bReturnToHub ? ScenePortalMaps::Hub : ScenePortalMaps::Hills;
    const FString Label = bReturnToHub ? TEXT("HOME / God Space") : TEXT("TEMPERATE HILLS\nBlack Poplar");
    const FString Options = bReturnToHub ? FString() : TEXT("HillsContinue");
    const FColor Color = bReturnToHub ? FColor::Cyan : FColor(100, 255, 145);
    FRotator Facing(0, Pawn->GetActorRotation().Yaw + 180.f, 0);
    FVector Position = Pawn->GetActorLocation() - Pawn->GetActorForwardVector() * ScenePortalMaps::PortalSpacing;
    bool bFixedHubAnchor = false;
    if (!bHills)
        for (TActorIterator<AActor> It(World); It; ++It)
            if (It->ActorHasTag(TEXT("GodSpace.HillsPortalAnchor")))
            {
                Position = It->GetActorLocation();
                Facing = It->GetActorRotation();
                bFixedHubAnchor = true;
                break;
            }
    if (!bFixedHubAnchor)
    {
        FHitResult Hit;
        FCollisionQueryParams Params;
        Params.AddIgnoredActor(Pawn);
        if (World->LineTraceSingleByChannel(Hit, Position + FVector(0, 0, 200), Position - FVector(0, 0, 1500), ECC_Pawn, Params))
            Position.Z = Hit.ImpactPoint.Z + .5f;
        else
            Position.Z -= 90.f;
    }
    FActorSpawnParameters SpawnParams;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ASceneTestPortal* Portal = World->SpawnActor<ASceneTestPortal>(Position, Facing, SpawnParams);
    if (Portal)
    {
        Portal->Tags.Add(LinkTag);
        Portal->Configure(Map, Label, Options, Color);
    }
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Installed hills link in %s"), *Current);
    return 1;
}
