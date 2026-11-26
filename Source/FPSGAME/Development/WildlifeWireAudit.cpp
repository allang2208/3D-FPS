#include "WildlifeWireAudit.h"
#include "../Monsters/WildlifeAnimal.h"
#include "../Monsters/MonsterCorpseRagdollComponent.h"
#include "../Monsters/QuadrupedAnimationTemplate.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpectatorPawn.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace WildlifeWire
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(), TEXT("WildlifeWireAudit"));
#endif
}
const TCHAR* Species[] = {TEXT("deer_doe"), TEXT("boar"), TEXT("crow")};
constexpr int32 Steps = 8, Count = UE_ARRAY_COUNT(Species) * Steps;
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows, bool Passed, const TCHAR* Role)
{
    FString Root; FParse::Value(FCommandLine::Get(), TEXT("WildlifeWireOutput="), Root);
    if (Root.IsEmpty()) Root = FPaths::ProjectSavedDir()/TEXT("WildlifeWireAudit");
    IFileManager::Get().MakeDirectory(*Root, true);
    auto Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("passed"), Passed);
    Result->SetStringField(TEXT("role"), Role);
    Result->SetStringField(TEXT("scope"), TEXT("Real UDP animal presentation, repeated hit, initial corpse state, death collision and 5s cleanup. Direct server stimuli; no weapon/AI/loot or render acceptance."));
    Result->SetArrayField(TEXT("cases"), Rows);
    FString Json; FJsonSerializer::Serialize(Result, TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json, *(Root/FString(Role).Append(TEXT(".json"))));
    UE_LOG(LogTemp, Display, TEXT("WILDLIFE_WIRE_RESULT role=%s passed=%d cases=%d"), Role, Passed, Rows.Num());
}
}

struct FWildlifeWireAuditAccess
{
    static uint32 Revision(const AColdSteelAnimal& A) { return A.Presentation.Revision; }
    static double Age(const AColdSteelAnimal& A) { return A.StateSeconds; }
    static void Hit(AColdSteelAnimal& A, FName Action)
    {
        if (A.SpeciesId == TEXT("crow"))
            A.EnterState(Action == TEXT("HitLeft") ? EWildlifeState::Fly : EWildlifeState::Glide);
        else { A.HitAction = Action; A.EnterState(EWildlifeState::Hit); }
    }
    static void Hold(AColdSteelAnimal& A)
    {
        A.bHillsGroup = true;
        A.SetActorTickEnabled(false);
        A.GetCharacterMovement()->SetComponentTickEnabled(false);
        A.GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    }
    static void Kill(AColdSteelAnimal& A, bool ImmediateCorpse)
    {
        A.SetActorTickEnabled(true);
        A.GetCharacterMovement()->SetComponentTickEnabled(true);
        if (A.SpeciesId == TEXT("crow") && !ImmediateCorpse)
        {
            A.SetActorLocation(FVector(0,0,350));
            A.GetCharacterMovement()->SetMovementMode(MOVE_Flying);
            A.EnterState(EWildlifeState::Fly);
        }
        FDamageEvent Event; A.TakeDamage(10000000.f, Event, nullptr, nullptr);
        if (ImmediateCorpse)
        {
            if (A.Row->bUseRagdoll) A.EnterRagdoll();
            else
            {
                A.SampleAction(TEXT("Death"), A.ClipLength(TEXT("Death")));
                A.CorpseRagdoll->FreezeAnimatedPose(A.GetMesh());
                A.EnterState(EWildlifeState::Corpse);
            }
        }
    }
};

void AWildlifeWireAuditController::BeginPlay()
{
    Super::BeginPlay();
    if (!WildlifeWire::Enabled() || !IsLocalController()) return;
    // Identical local floor on both peers; no production map or asset writes.
    auto* Floor = GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,-10), FRotator::ZeroRotator);
    Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Floor->SetActorScale3D(FVector(100,100,.2));
    Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
}
void AWildlifeWireAuditController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWildlifeWireAuditController, Subject);
    DOREPLIFETIME(AWildlifeWireAuditController, Case);
    DOREPLIFETIME(AWildlifeWireAuditController, Revision);
}
void AWildlifeWireAuditController::Tick(float Delta)
{
    Super::Tick(Delta);
    if (!WildlifeWire::Enabled() || !IsLocalController() || HasAuthority()) return;
    const double Now = GetWorld()->GetRealTimeSeconds();
    if (ExitAt >= 0.) { if (Now >= ExitAt) FPlatformMisc::RequestExit(false); return; }
    if (Case < 0 || Reported == Case) return;
    if (Watching != Case) { Watching = Case; WatchStart = Now; }
    const int32 Step = Case % WildlifeWire::Steps;
    bool Passed = false;
    FString Detail;
    if (Step == 6)
    {
        Passed = !Seen.IsValid();
        Detail = TEXT("server-destroyed corpse no longer exists on client");
    }
    else if (IsValid(Subject) && Subject->HasActorBegunPlay())
    {
        Seen = Subject;
        const bool CaughtUp = FWildlifeWireAuditAccess::Revision(*Subject) >= Revision;
        const auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(Subject->GetMesh()->GetAnimInstance());
        if (Step == 0) Passed = CaughtUp && Subject->State == EWildlifeState::Idle && Anim;
        if (Step >= 1 && Step <= 3 && Subject->SpeciesId != TEXT("crow"))
            Passed = CaughtUp && Subject->State == EWildlifeState::Hit && Anim
                && Anim->ActiveAction == (Step == 1 ? TEXT("HitLeft") : TEXT("HitRight"))
                && Anim->ActiveDefinition.Sequence
                && FMath::Abs(Anim->ActionTime - FMath::Min(float(FWildlifeWireAuditAccess::Age(*Subject)), Anim->ActiveDefinition.Sequence->GetPlayLength())) < .12f;
        if (Step >= 1 && Step <= 3 && Subject->SpeciesId == TEXT("crow"))
            Passed = CaughtUp && Anim && Anim->ActiveAction == (Step == 1 ? TEXT("Fly") : TEXT("Glide"));
        const bool NoGhost = Subject->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Ignore
            && (Subject->State == EWildlifeState::AirFall || Subject->GetCapsuleComponent()->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
        if (Step == 4) Passed = CaughtUp && Subject->IsDead() && NoGhost;
        if (Step == 5 || Step == 7)
            Passed = CaughtUp && Subject->State == EWildlifeState::Corpse && NoGhost
                && (Subject->CorpseRagdoll->SimulatedBodyCount() > 0 || Subject->CorpseRagdoll->IsFrozen());
        if (Step == 7) Passed &= FWildlifeWireAuditAccess::Age(*Subject) > .6;
        Detail = FString::Printf(TEXT("state=%d revision=%u expected=%u age=%.3f capsule=%d bodies=%d frozen=%d"),
            int32(Subject->State), FWildlifeWireAuditAccess::Revision(*Subject), Revision, FWildlifeWireAuditAccess::Age(*Subject),
            int32(Subject->GetCapsuleComponent()->GetCollisionEnabled()), Subject->CorpseRagdoll->SimulatedBodyCount(), Subject->CorpseRagdoll->IsFrozen());
    }
    if (!Passed && Now-WatchStart < 8.) return;
    Reported = Case; AllPassed &= Passed;
    auto Row = MakeShared<FJsonObject>(); Row->SetNumberField(TEXT("case"), Case);
    Row->SetStringField(TEXT("species"), WildlifeWire::Species[Case/WildlifeWire::Steps]);
    Row->SetBoolField(TEXT("passed"), Passed); Row->SetStringField(TEXT("details"), Detail);
    Results.Add(MakeShared<FJsonValueObject>(Row));
    ServerObserved(Case, Passed, Detail);
}
void AWildlifeWireAuditController::ServerObserved_Implementation(int32 Index, bool Passed, const FString& Detail)
{
    if (!WildlifeWire::Enabled() || Index != Case || Finished >= Index) return;
    Finished = Index; AllPassed &= Passed;
    auto Row = MakeShared<FJsonObject>(); Row->SetNumberField(TEXT("case"), Index);
    Row->SetBoolField(TEXT("passed"), Passed); Row->SetStringField(TEXT("details"), Detail);
    Results.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp, Display, TEXT("WILDLIFE_WIRE_CASE %d passed=%d %s"), Index, Passed, *Detail);
}
void AWildlifeWireAuditController::ClientFinish_Implementation(bool Passed)
{
    if (!WildlifeWire::Enabled()) return;
    WildlifeWire::Save(Results, Passed && AllPassed, TEXT("client"));
    ExitAt = GetWorld()->GetRealTimeSeconds() + 1.;
}
AWildlifeWireAuditGameMode::AWildlifeWireAuditGameMode()
{
    PrimaryActorTick.bCanEverTick = true;
    PlayerControllerClass = AWildlifeWireAuditController::StaticClass();
    DefaultPawnClass = ASpectatorPawn::StaticClass();
    HUDClass = nullptr;
}
void AWildlifeWireAuditGameMode::StartPlay()
{
    if (WildlifeWire::Enabled())
        for (TActorIterator<ATemperateHillsWorld> It(GetWorld()); It; ++It) It->Destroy();
    Super::StartPlay();
    Started = GetWorld()->GetRealTimeSeconds();
    if (WildlifeWire::Enabled()) UE_LOG(LogTemp, Display, TEXT("WILDLIFE_WIRE_HOST_READY"));
}
void AWildlifeWireAuditGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);
    if (WildlifeWire::Enabled() && !Player->IsLocalController()) Guest = Cast<AWildlifeWireAuditController>(Player);
}
void AWildlifeWireAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);
    if (!WildlifeWire::Enabled()) return;
    const double Now = GetWorld()->GetRealTimeSeconds();
    if (ExitAt >= 0.) { if (Now >= ExitAt) FPlatformMisc::RequestExit(false); return; }
    if (!Guest) { if (Now-Started > 300.) FPlatformMisc::RequestExit(false); return; }
    if (Guest->Finished >= WildlifeWire::Count-1 || Now-Started > 480.)
    {
        Passed &= Guest->AllPassed && Guest->Finished == WildlifeWire::Count-1;
        Guest->ClientFinish(Passed); WildlifeWire::Save(Guest->Results, Passed, TEXT("host")); ExitAt = Now+3.; return;
    }
    const int32 Next = Guest->Finished+1, Step = Next%WildlifeWire::Steps;
    if (Prepared == Next)
    {
        if (Step == 7 && !Revealed && Now-PreparedAt >= 1.25)
        {
            Animal->bOnlyRelevantToOwner = false; Animal->bAlwaysRelevant = true;
            Animal->SetOwner(nullptr); Animal->ForceNetUpdate();
            Guest->Subject = Animal; Guest->Case = Next; Guest->Revision = FWildlifeWireAuditAccess::Revision(*Animal); Revealed = true;
        }
        return;
    }
    // Give repeated actions a distinct timestamp and death time to reach physics.
    if (Now-PreparedAt < .2) return;
    if (Step == 5 && IsValid(Animal) && Animal->State != EWildlifeState::Corpse) return;
    if (Step == 6 && IsValid(Animal)) return;
    Prepared = Next; PreparedAt = Now;
    if (Step == 0 || Step == 7)
    {
        if (IsValid(Animal)) Animal->Destroy();
        const auto* Row = WildlifeCatalog::Get().Find(WildlifeWire::Species[Next/WildlifeWire::Steps]);
        UClass* Class = LoadObject<UClass>(nullptr, *Row->CharacterClass);
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if (Step == 7) Params.Owner = GetWorld()->GetFirstPlayerController();
        Animal = GetWorld()->SpawnActor<AColdSteelAnimal>(Class, FVector(0,0,Row->CapsuleHalfHeight+3), FRotator::ZeroRotator, Params);
        if (!Animal) { Passed = false; Guest->Finished = WildlifeWire::Count-1; return; }
        Animal->bAlwaysRelevant = Step != 7;
        FWildlifeWireAuditAccess::Hold(*Animal);
        if (Step == 7)
        {
            Animal->bOnlyRelevantToOwner = true;
            FWildlifeWireAuditAccess::Kill(*Animal, true);
            Revealed = false; return;
        }
    }
    if (Step >= 1 && Step <= 3) FWildlifeWireAuditAccess::Hit(*Animal, Step == 1 ? TEXT("HitLeft") : TEXT("HitRight"));
    if (Step == 4) { FWildlifeWireAuditAccess::Kill(*Animal, false); DiedAt = GetWorld()->GetTimeSeconds(); }
    if (Step == 6) Passed &= FMath::Abs(GetWorld()->GetTimeSeconds()-DiedAt-5.) < .5;
    Guest->Subject = IsValid(Animal) ? Animal : nullptr; Guest->Case = Next;
    Guest->Revision = IsValid(Animal) ? FWildlifeWireAuditAccess::Revision(*Animal) : 0;
    Guest->ForceNetUpdate();
}
