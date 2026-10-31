#include "NearBankPCGAuthoringTools.h"
#include "PCGComponent.h"
#include "PCGGraph.h"
#include "PCGVolume.h"
#include "Subsystems/PCGSubsystem.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Components/SplineComponent.h"
#include "Async/TaskGraphInterfaces.h"
#include "Containers/Ticker.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "JsonObjectConverter.h"
#include "Serialization/JsonSerializer.h"
#include "StructUtils/PropertyBag.h"
#include "UObject/UnrealType.h"
#include "UObject/UObjectGlobals.h"
#include "AssetCompilingManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeExit.h"

bool UNearBankPCGAuthoringTools::GenerateOffline(APCGVolume* Volume, float TimeoutSeconds)
{
#if WITH_EDITOR
    if (!IsValid(Volume) || !Volume->PCGComponent || !Volume->GetWorld()
        || Volume->GetWorld()->WorldType != EWorldType::Editor) return false;
    UPCGComponent* Component = Volume->PCGComponent;
    UPCGSubsystem* Subsystem = Volume->GetWorld()->GetSubsystem<UPCGSubsystem>();
    if (!Subsystem || Component->IsGenerating()) return false;
    Component->GenerationTrigger = EPCGComponentGenerationTrigger::GenerateOnDemand;
    Component->bGenerateOnDropWhenTriggerOnDemand = false;
    Component->bRegenerateInEditor = false;
    IConsoleVariable* DelegateDelay = IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int32 PreviousDelay = DelegateDelay ? DelegateDelay->GetInt() : 1;
    if (DelegateDelay) DelegateDelay->Set(0, ECVF_SetByCode);
    ON_SCOPE_EXIT { if (DelegateDelay) DelegateDelay->Set(PreviousDelay, ECVF_SetByCode); };
    Component->GenerateLocal(true);
    const double Deadline = FPlatformTime::Seconds() + FMath::Max(1.0f, TimeoutSeconds);
    // A Python commandlet has no editor tick loop. Pump only the PCG scheduler,
    // core ticker and game-thread tasks; never call UWorld::Tick or BeginPlay.
    do
    {
        FTaskGraphInterface::Get().ProcessThreadUntilIdle(ENamedThreads::GameThread);
        ProcessAsyncLoading(true, false, 0.01);
        FAssetCompilingManager::Get().ProcessAsyncTasks(true);
        FTSTicker::GetCoreTicker().Tick(1.0f / 60.0f);
        Subsystem->Tick(1.0f / 60.0f);
        if (FPlatformTime::Seconds() >= Deadline)
        {
            Component->CancelGeneration();
            UE_LOG(LogTemp, Error, TEXT("Near-bank PCG production timed out: %s"), *Volume->GetActorLabel());
            return false;
        }
        FPlatformProcess::Sleep(0.001f);
    } while (Component->IsGenerating() || Component->IsCleaningUp());
    Volume->MarkPackageDirty();
    return Component->bGenerated;
#else
    return false;
#endif
}

AActor* UNearBankPCGAuthoringTools::CreateSplineInput(UObject* WorldContext,
    const FString& Label, const TArray<FVector>& WorldPoints, bool bClosed, FName SemanticTag)
{
#if WITH_EDITOR
    UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    if (!World || World->WorldType != EWorldType::Editor || WorldPoints.Num() < (bClosed ? 3 : 2)) return nullptr;
    FActorSpawnParameters Params;
    Params.ObjectFlags = RF_Transactional;
    AActor* Actor = World->SpawnActor<AActor>(WorldPoints[0], FRotator::ZeroRotator, Params);
    if (!Actor) return nullptr;
    Actor->SetActorLabel(Label);
    Actor->Tags.Add(TEXT("CyberpunkApartment.NearBankNativePCG20261028"));
    Actor->Tags.Add(SemanticTag);
    Actor->PrimaryActorTick.bCanEverTick = false;
    auto* Spline = NewObject<USplineComponent>(Actor, TEXT("DistrictInput"), RF_Transactional);
    Actor->SetRootComponent(Spline);
    Actor->AddInstanceComponent(Spline);
    Spline->SetMobility(EComponentMobility::Static);
    Spline->SetWorldLocation(WorldPoints[0]);
    Spline->RegisterComponent();
    Spline->ClearSplinePoints(false);
    for (const FVector& Point : WorldPoints) Spline->AddSplinePoint(Point, ESplineCoordinateSpace::World, false);
    for (int32 Index = 0; Index < WorldPoints.Num(); ++Index) Spline->SetSplinePointType(Index, ESplinePointType::Linear, false);
    Spline->SetClosedLoop(bClosed, true);
    Actor->MarkPackageDirty();
    return Actor;
#else
    return nullptr;
#endif
}

FString UNearBankPCGAuthoringTools::DescribeParameters(const UPCGGraphInterface* Graph)
{
    TSharedRef<FJsonObject> Result = MakeShared<FJsonObject>();
    const FInstancedPropertyBag* Bag = Graph ? Graph->GetUserParametersStruct() : nullptr;
    if (Bag && Bag->GetPropertyBagStruct())
    {
        for (TFieldIterator<FProperty> It(Bag->GetPropertyBagStruct()); It; ++It)
        {
            TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("type"), It->GetCPPType());
            const void* Value = It->ContainerPtrToValuePtr<void>(Bag->GetValue().GetMemory());
            if (TSharedPtr<FJsonValue> Json = FJsonObjectConverter::UPropertyToJsonValue(*It, Value))
                Row->SetField(TEXT("value"), Json);
            Result->SetObjectField(It->GetName(), Row);
        }
    }
    FString Text;
    FJsonSerializer::Serialize(Result, TJsonWriterFactory<>::Create(&Text));
    return Text;
}
