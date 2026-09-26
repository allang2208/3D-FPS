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
    const TCHAR* Water = TEXT("/Game/Clearwater/L_ClearwaterWater");

    /** How far behind the player a link door is planted. Shared so the hills door (behind)
     *  and the water door (to the left) cannot drift into each other's space. */
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
    if (GetNetMode() != NM_Standalone) return;
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
    if (bTravelling || !Pawn || PC->bShowMouseCursor || GetNetMode() != NM_Standalone) return;
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
    if (Destination == ScenePortalMaps::Water)
    {
        // Stream the water level in before tearing the current map down, so the travel does
        // not stall on a cold level load.
        Sign->SetText(FText::FromString(TEXT("Preparing water...\n[Esc] Cancel")));
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
        const bool bWater = Destination == ScenePortalMaps::Water;
        CancelLoading();
        Sign->SetText(FText::FromString(bWater
            ? TEXT("Water level could not load\n[E] Retry")
            : TEXT("Hills could not load\n[E] Retry")));
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

int32 ASceneTestPortal::InstallWaterLink(UWorld* World)
{
    if (!World || !World->IsGameWorld() || World->GetNetMode() != NM_Standalone) return 2;
    const FString Current = UGameplayStatics::GetCurrentLevelName(World, true);
    if (Current != TEXT("DayNight_Lighting") && Current != TEXT("L_ClearwaterWater")) return 2;
    APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0);
    if (!Pawn) return 0;
    const FName LinkTag(TEXT("ScenePortal.WaterLink"));
    for (TActorIterator<ASceneTestPortal> It(World); It; ++It)
        if (It->ActorHasTag(LinkTag)) return 1;

    const bool bInWater = Current == TEXT("L_ClearwaterWater");
    const FString Map = bInWater ? ScenePortalMaps::Hub : ScenePortalMaps::Water;
    const FString Label = bInWater ? TEXT("HOME / Main Map") : TEXT("CLEARWATER / Water Test");
    const FColor Color = bInWater ? FColor::Cyan : FColor(120, 220, 255);
    FVector Position = Pawn->GetActorLocation();
    FRotator Facing = Pawn->GetActorRotation();
    if (bInWater)
    {
        // On the basin's shore, behind the level's PlayerStart. The player spawns at
        // (+9660, 0, 200) and faces -X across the water, so the return door sits the other
        // way at +9660 and faces back at them. Setting it to the middle of the water would
        // put it below the surface, where an unbound door is invisible.
        //
        // Keep in step with VIEW_DISTANCE_CM / SHORE_STAND_X in
        // Tools/Fluids/author_clearwater_water.py.
        Position = FVector(9660.f, 0.f, 200.f);
        Facing = FRotator(0.f, 180.f, 0.f);
    }
    else
    {
        // Off the player's LEFT, not behind them. InstallHillsLink already puts its door
        // directly behind (Facing.Vector() * -Spacing), and sharing that spot stacked the
        // two portals and their signs on top of each other. A right angle gives them
        // Spacing * sqrt(2) = 495 cm of separation, so neither can occlude the other and
        // both stay a short walk from the spawn.
        //
        // Left is yaw - 90, the direction the player faces after turning left:
        // Left.Vector() = (cos(yaw-90), sin(yaw-90), 0) = (sin yaw, -cos yaw, 0).
        const float LeftYaw = Pawn->GetActorRotation().Yaw - 90.f;
        const FRotator Left(0.f, LeftYaw, 0.f);
        Position = Pawn->GetActorLocation() + Left.Vector() * -ScenePortalMaps::PortalSpacing;
        // LeftYaw + 180, which is the SAME rule the hills door uses. The door reads from its
        // -X face (check the hills door: at rotation PawnYaw+180 its -X points back at the
        // pawn), so for any placement the readable rotation is "bearing to the pawn + 180".
        // The hills door happens to sit behind, giving PawnYaw+180; the water door sits to
        // the side, giving PawnYaw+90. Deriving it from the known-good door rather than
        // assuming +X faces the viewer is what makes this correct.
        Facing = FRotator(0.f, LeftYaw + 180.f, 0.f);
    }
    FHitResult Hit;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(Pawn);
    if (!bInWater && World->LineTraceSingleByChannel(
            Hit, Position + FVector(0, 0, 200), Position - FVector(0, 0, 1500), ECC_Pawn, Params))
        Position.Z = Hit.ImpactPoint.Z + .5f;

    FActorSpawnParameters SpawnParams;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ASceneTestPortal* Portal = World->SpawnActor<ASceneTestPortal>(
        Position, Facing, SpawnParams);
    if (Portal)
    {
        Portal->Tags.Add(LinkTag);
        Portal->Configure(Map, Label, FString(), Color);
    }
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Installed water link in %s"), *Current);
    return 1;
}

int32 ASceneTestPortal::InstallHillsLink(UWorld* World)
{
    if (!World || !World->IsGameWorld() || World->GetNetMode() != NM_Standalone) return 2;
    const FString Current = UGameplayStatics::GetCurrentLevelName(World, true);
    if (Current != TEXT("DayNight_Lighting") && Current != TEXT("L_TemperateHills_Initial")) return 2;
    APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0);
    if (!Pawn) return 0;
    const FName LinkTag(TEXT("ScenePortal.HillsLink"));
    for (TActorIterator<ASceneTestPortal> It(World); It; ++It)
        if (It->ActorHasTag(LinkTag)) return 1;

    const bool bHills = Current == TEXT("L_TemperateHills_Initial");
    const FString Map = bHills ? ScenePortalMaps::Hub : ScenePortalMaps::Hills;
    const FString Label = bHills ? TEXT("HOME / Main Map") : TEXT("TEMPERATE HILLS\nBlack Poplar");
    const FString Options = bHills ? FString() : TEXT("HillsContinue");
    const FColor Color = bHills ? FColor::Cyan : FColor(100, 255, 145);
    const FRotator Facing(0, Pawn->GetActorRotation().Yaw, 0);
    FVector Position = Pawn->GetActorLocation() + Facing.Vector() * -ScenePortalMaps::PortalSpacing;
    FHitResult Hit;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(Pawn);
    if (World->LineTraceSingleByChannel(Hit, Position + FVector(0, 0, 200), Position - FVector(0, 0, 1500), ECC_Pawn, Params))
        Position.Z = Hit.ImpactPoint.Z + .5f;
    else
        Position.Z -= 90.f;
    FActorSpawnParameters SpawnParams;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ASceneTestPortal* Portal = World->SpawnActor<ASceneTestPortal>(Position, FRotator(0, Facing.Yaw + 180.f, 0), SpawnParams);
    if (Portal)
    {
        Portal->Tags.Add(LinkTag);
        Portal->Configure(Map, Label, Options, Color);
    }
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Installed hills link in %s"), *Current);
    return 1;
}
