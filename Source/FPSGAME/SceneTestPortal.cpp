#include "SceneTestPortal.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Components/InputComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"
#include "InputCoreTypes.h"

namespace ScenePortalMaps
{
    const TCHAR* Hub = TEXT("/Game/GameMaps/DayNight_Lighting");
    const TCHAR* Normandy = TEXT("/Game/GameMaps/L_Normandy_FPS_Test");
    const TCHAR* Trench = TEXT("/Game/GameMaps/L_MilitaryTrench_FPS_Test");
    const TCHAR* Hills = TEXT("/Game/GameMaps/L_TemperateHills_Initial");
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
}

void ASceneTestPortal::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode() != NM_Standalone) return;
    EnableInput(UGameplayStatics::GetPlayerController(this, 0));
    if (InputComponent)
    {
        // Portal spacing keeps the 2m interaction areas separate.
        InputComponent->BindKey(EKeys::E, IE_Pressed, this, &ASceneTestPortal::UsePortal).bConsumeInput = false;
        InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &ASceneTestPortal::CancelLoading).bConsumeInput = false;
    }
}

void ASceneTestPortal::UsePortal()
{
    APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
    APawn* Pawn = PC ? PC->GetPawn() : nullptr;
    if (bTravelling || !Pawn || PC->bShowMouseCursor || GetNetMode() != NM_Standalone) return;
    const FVector Delta = Pawn->GetActorLocation() - GetActorLocation();
    if (Delta.SizeSquared2D() > FMath::Square(200.f) || FMath::Abs(Delta.Z) > 250.f) return;
    if (!FPackageName::DoesPackageExist(Destination))
    {
        if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Red, TEXT("Portal destination missing; travel cancelled."));
        UE_LOG(LogTemp, Error, TEXT("ScenePortal: Missing destination %s"), *Destination);
        return;
    }
    bTravelling = true;
    if (Destination == ScenePortalMaps::Hills)
    {
        Sign->SetText(FText::FromString(TEXT("Preparing hills...\n[Esc] Cancel")));
        const FString ObjectPath=Destination+TEXT(".")+FPackageName::GetShortName(Destination);
        PreloadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(FSoftObjectPath(ObjectPath),FStreamableDelegate::CreateUObject(this,&ASceneTestPortal::FinishLoading));
        return;
    }
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Travel %s"), *Destination);
    UGameplayStatics::OpenLevel(this, FName(*Destination), true, DestinationOptions);
}

void ASceneTestPortal::FinishLoading()
{
    if (!bTravelling) return;
    if (!PreloadHandle || !PreloadHandle->GetLoadedAsset())
    {
        CancelLoading();
        Sign->SetText(FText::FromString(TEXT("Hills could not load\n[E] Retry")));
        return;
    }
    UGameplayStatics::OpenLevel(this,FName(*Destination),true,DestinationOptions);
}

void ASceneTestPortal::CancelLoading()
{
    if (!PreloadHandle) return;
    PreloadHandle->CancelHandle();PreloadHandle.Reset();bTravelling=false;
    Sign->SetText(FText::FromString(DestinationLabel+TEXT("\n[E] Travel (within 2m)")));
}

void ASceneTestPortal::EndPlay(const EEndPlayReason::Type Reason)
{
    if(PreloadHandle){PreloadHandle->CancelHandle();PreloadHandle.Reset();}
    Super::EndPlay(Reason);
}

void USceneTestPortalSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    if (!InWorld.IsGameWorld() || InWorld.GetNetMode() != NM_Standalone) return;
    const FString Map = UGameplayStatics::GetCurrentLevelName(&InWorld, true);
    if (Map != TEXT("DayNight_Lighting") && Map != TEXT("L_Normandy_FPS_Test") && Map != TEXT("L_MilitaryTrench_FPS_Test") && Map != TEXT("L_TemperateHills_Initial")) return;
    InWorld.GetTimerManager().SetTimer(SpawnTimer, this, &USceneTestPortalSubsystem::SpawnPortals, 0.5f, true);
}

void USceneTestPortalSubsystem::SpawnPortals()
{
    UWorld* World = GetWorld();
    APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0);
    if (!Pawn)
    {
        // The asynchronous hills startup can outlive the old 20-second portal timer.
        if(UGameplayStatics::GetCurrentLevelName(World,true)==TEXT("L_TemperateHills_Initial"))return;
        if (++Attempts >= 40) World->GetTimerManager().ClearTimer(SpawnTimer);
        return;
    }
    World->GetTimerManager().ClearTimer(SpawnTimer);
    const FString Current = UGameplayStatics::GetCurrentLevelName(World, true);
    struct FDestination
    {
        FString Map;
        FString Label;
        FString Options;
        FColor Color = FColor::Cyan;
    };
    TArray<FDestination> Destinations;
    if (Current == TEXT("L_TemperateHills_Initial"))
    {
        // The hills GameMode releases the pawn only after terrain collision is ready.
        Destinations.Add({ScenePortalMaps::Hub, TEXT("HOME / Main Map"), FString()});
    }
    else
    {
        const FString Maps[] = {ScenePortalMaps::Hub, ScenePortalMaps::Normandy, ScenePortalMaps::Trench};
        const FString Labels[] = {TEXT("HOME / Main Map"), TEXT("NORMANDY VILLAGE"), TEXT("MILITARY TRENCH")};
        for (int32 Index = 0; Index < UE_ARRAY_COUNT(Maps); ++Index)
            if (FPackageName::GetShortName(Maps[Index]) != Current)
                Destinations.Add({Maps[Index], Labels[Index], FString()});
        if (Current == TEXT("DayNight_Lighting"))
            Destinations.Add({ScenePortalMaps::Hills, TEXT("TEMPERATE HILLS\nBlack Poplar"), TEXT("HillsContinue"), FColor(100, 255, 145)});
    }
    const FRotator Facing(0, Pawn->GetActorRotation().Yaw, 0);
    const FVector Forward = Facing.Vector();
    const FVector Right = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);
    int32 Installed = 0;
    for (int32 Index = 0; Index < Destinations.Num(); ++Index)
    {
        const FDestination& Entry = Destinations[Index];
        const float Side = (Index - (Destinations.Num() - 1) * .5f) * 440.f;
        FVector Position = Pawn->GetActorLocation() + Forward * 350.f + Right * Side;
        FHitResult Hit;
        FCollisionQueryParams Params;
        Params.AddIgnoredActor(Pawn);
        // Fog volumes can block Visibility while deliberately ignoring the player.
        if (World->LineTraceSingleByChannel(Hit, Position + FVector(0, 0, 200), Position - FVector(0, 0, 1500), ECC_Pawn, Params))
            Position.Z = Hit.ImpactPoint.Z + 5.f;
        else
            Position.Z -= 90.f;
        FActorSpawnParameters SpawnParams;
        SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        ASceneTestPortal* Portal = World->SpawnActor<ASceneTestPortal>(Position, FRotator(0, Facing.Yaw + 180.f, 0), SpawnParams);
        if (Portal)
        {
            Portal->Configure(Entry.Map, Entry.Label, Entry.Options, Entry.Color);
            ++Installed;
        }
    }
    UE_LOG(LogTemp, Display, TEXT("ScenePortal: Installed %d portals in %s"), Installed, *Current);
}

void USceneTestPortalSubsystem::Deinitialize()
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(SpawnTimer);
    Super::Deinitialize();
}
