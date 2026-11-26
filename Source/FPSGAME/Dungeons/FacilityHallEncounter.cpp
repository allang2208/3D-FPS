#include "FacilityHallEncounter.h"
#include "../Monsters/HeQueMonster.h"
#include "HeQuePumpControl.h"
#include "FacilityMonsterGpuWarmup.h"
#include "FacilityHallSpawnSubsystem.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonThemeEncounter.h"
#include "../Development/DevelopmentSpawnComponent.h"
#include "UObject/UnrealType.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/BellowSacLobber.h"
#include "../Monsters/BoundCongregate.h"
#include "../Monsters/HangingBellM09.h"
#include "../Monsters/LurkerM08Monster.h"
#include "../Monsters/MantisM27Monster.h"
#include "../Monsters/BlindSupplicantMonster.h"
#include "../Monsters/M10Mawcrawler.h"
#include "../Monsters/RootCrownRigPreview.h"
#include "../Monsters/VortexCofferM25.h"
#include "../Monsters/M66IncineratorMonster.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/HumanoidKnockdownComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "NavigationData.h"
#include "NavigationSystem.h"
#include "TimerManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
constexpr int32 StaffClassCount = 3;
constexpr int32 BellowCount = 4;
constexpr int32 EliteAttemptsBeforeReplacement = 3;

TArray<const FDevelopmentMonsterEntry*> SelectHallElites(int32 Seed)
{
    // Actual ground-capable M-series elites. Staff/Bellow are ordinary species;
    // M07/M10/M25/M88 are lords. Hanging Bell requires a ceiling placement.
    static const TSet<FName> GroundElites = {
        TEXT("MantisM27"), TEXT("LurkerM08"), TEXT("SpiralPillarM14")
    };
    TArray<const FDevelopmentMonsterEntry*> Pool;
    for (const auto& Entry : GetDefault<UDevelopmentSpawnComponent>()->GetMonsters())
        if (GroundElites.Contains(Entry.Id)) Pool.Add(&Entry);
    FRandomStream Draw(int32(HashCombineFast(uint32(Seed), DungeonRunDomains::EliteSelection)));
    TArray<const FDevelopmentMonsterEntry*> Candidates;
    while (!Pool.IsEmpty())
    {
        const int32 Index = Draw.RandRange(0, Pool.Num() - 1);
        Candidates.Add(Pool[Index]);
        Pool.RemoveAt(Index);
    }
    return Candidates;
}
}

AFacilityHallEncounter::AFacilityHallEncounter()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
}

bool AFacilityHallEncounter::IsHall(const FString& Module)
{
    return Module == TEXT("FacilityReceptionHall") || Module == TEXT("FacilityTransit");
}

bool AFacilityHallEncounter::IsDoorLeaf(const FString& Module, const FString& Mesh)
{
    return (IsHall(Module)||Module==TEXT("AbandonedTransitStation")) && (Mesh.EndsWith(TEXT("/SM_Entry_DoorLeaf"))
        || Mesh.EndsWith(TEXT("/SM_Entry_DoorLeafRight")));
}

TArray<FString> AFacilityHallEncounter::MonsterClassPaths()
{
    return {
        TEXT("/Game/Monsters/FacelessReceptionist/BP_FacelessReceptionist.BP_FacelessReceptionist_C"),
        TEXT("/Game/Monsters/FacelessSecurity/BP_FacelessSecurity.BP_FacelessSecurity_C"),
        TEXT("/Game/Monsters/FacelessResearcher/BP_FacelessResearcher.BP_FacelessResearcher_C"),
        TEXT("/Game/Monsters/BellowSacLobber/BP_BellowSacLobber.BP_BellowSacLobber_C")
    };
}

FString AFacilityHallEncounter::ObjectiveEliteClassPath(int32 RunSeed)
{
    const auto Candidates = SelectHallElites(RunSeed);
    return Candidates.IsEmpty() ? FString() : Candidates[0]->CharacterClass.ToSoftObjectPath().ToString();
}

bool AFacilityHallEncounter::IsObjectiveEliteDefeated() const
{
    return Slots.IsValidIndex(ObjectiveEliteSlot) && Slots[ObjectiveEliteSlot].bDefeated;
}

TArray<FString> AFacilityHallEncounter::PreparationAssetPaths(int32 RunSeed)
{
    TArray<FString> Paths = SelectedMonsterClassPaths(RunSeed);
    // All three staff classes use the Nurse knockdown rig. These runtime defaults
    // are not hard references in their blueprints, so loading the classes misses them.
    for (const FSoftObjectPath& Path : UHumanoidKnockdownComponent::DefaultAnimationPaths(TEXT("Nurse")))
        Paths.Add(Path.ToString());
    return Paths;
}

TArray<FString> AFacilityHallEncounter::SelectedMonsterClassPaths(int32 RunSeed)
{
    TArray<FString> Paths = MonsterClassPaths();
    // Prepare the three eligible species through the existing async resource and
    // rendering stages; replacing a failed spawn must never synchronously load.
    for (const auto* Entry : SelectHallElites(RunSeed))
        Paths.AddUnique(Entry->CharacterClass.ToSoftObjectPath().ToString());
    return Paths;
}

bool AFacilityHallEncounter::Configure(UDungeonRunSubsystem* InRun,int32 InNode,AAuthoredDungeonGenerator* InGenerator,ADungeonThemeEncounter* InTheme)
{
    ConfigureRoom(InRun,InNode,InGenerator,InTheme);
    bConfigured=Run.IsValid()&&Generator.IsValid()&&Theme.IsValid()&&FirstWaveCount>0
        &&Slots.Num()>=FirstWaveCount&&!Members.IsEmpty()
        &&!Slots.ContainsByPredicate([this](const auto& Slot){return !Members.IsValidIndex(Slot.Member)||!Members[Slot.Member];});
    if(!bConfigured)
    {
        GetWorldTimerManager().ClearTimer(EncounterTimer);
        UE_LOG(LogTemp,Error,TEXT("[FacilityEncounter] Configuration failed: room=%d module=%s"),InNode,*Room.Module);
        return false;
    }
    ConfigurePacing();CacheSpawnNavigationAnchors();CacheHallTrafficAreas();InTheme->RegisterHall(this);
    return true;
}

void AFacilityHallEncounter::ConfigureRoom(UDungeonRunSubsystem* InRun, int32 InNode, AAuthoredDungeonGenerator* InGenerator, ADungeonThemeEncounter* InTheme)
{
    if (!HasAuthority() || !InRun || !InGenerator) return;
    const auto* Node = InRun->NodeById(InNode);
    if (!Node || (!IsHall(Node->Module) && !IsMedical(Node->Module) && !IsFreight(Node->Module) && !IsEcology(Node->Module) && !IsPower(Node->Module) && !IsIncineration(Node->Module) && !IsFinalBossRoom(Node->Module) && !IsStaffLiving(Node->Module))) return;
    Run = InRun;
    Generator = InGenerator;
    Theme = InTheme;
    InGenerator->OnDestroyed.AddDynamic(this, &AFacilityHallEncounter::DungeonDestroyed);
    Room = *Node;
    bFinalBossRoom=IsFinalBossRoom(Room.Module);
    if(bFinalBossRoom){ConfigureFinalBoss();return;}
    bMedical = IsMedical(Room.Module);
    if (bMedical) { ConfigureMedical(); return; }
    bFreight = IsFreight(Room.Module);
    if (bFreight) { ConfigureFreight(); return; }
    bEcology = IsEcology(Room.Module);
    if (bEcology) { ConfigureEcology(); return; }
    bPower = IsPower(Room.Module);
    if (bPower) { ConfigurePower(); return; }
    bIncineration = IsIncineration(Room.Module);
    if (bIncineration) { ConfigureIncineration(); return; }
    bStaffLiving = IsStaffLiving(Room.Module);
    if (bStaffLiving) { ConfigureStaffLiving(); return; }
    // Loaded by the generator's existing asynchronous preparation stage.
    for (const FString& Path : MonsterClassPaths())
    {
        UClass* Class = FSoftClassPath(Path).ResolveClass();
        const UClass* Expected = Members.Num() < StaffClassCount ? ANurseZombie::StaticClass() : ABellowSacLobber::StaticClass();
        if (!Class || !Class->IsChildOf(Expected))
        {
            UE_LOG(LogTemp, Error, TEXT("[HallWaves] Missing prepared monster class: %s"), *Path);
            return;
        }
        Members.Add(Class);
    }
    const bool bAddElite = Room.Module == TEXT("FacilityTransit");
    int32 EliteMember = INDEX_NONE;
    if (bAddElite)
    {
        for (const auto* Entry : SelectHallElites(InRun->RunSeed()))
        {
            UClass* Class = Entry->CharacterClass.Get();
            const auto* Rank = Class ? FindFProperty<FEnumProperty>(Class, TEXT("Rank")) : nullptr;
            if (!Class || !Class->IsChildOf(ACharacter::StaticClass()) || !Rank || Rank->GetEnum() != StaticEnum<EMonsterRank>())
            {
                UE_LOG(LogTemp, Warning, TEXT("[HallWaves] Skipping unprepared objective elite: %s"), *Entry->Id.ToString());
                continue;
            }
            auto& Candidate = ObjectiveEliteCandidates.AddDefaulted_GetRef();
            Candidate.Member = Members.Add(Class);
            Candidate.Footprint = Entry->FootprintRadius;
        }
        if (ObjectiveEliteCandidates.IsEmpty())
        {
            UE_LOG(LogTemp, Error, TEXT("[HallWaves] No prepared objective elite candidates."));
            return;
        }
        EliteMember = ObjectiveEliteCandidates[0].Member;
        ObjectiveEliteFootprint = ObjectiveEliteCandidates[0].Footprint;
    }
    const FName RoomTag(*FString::Printf(TEXT("DungeonModule.%d.%s"), Room.Id, *Room.Module));
    const FString Prefix = TEXT("DungeonHallDoor.");
    // One registration pass per hall; no world scans in the encounter timer.
    for (TActorIterator<AStaticMeshActor> It(GetWorld()); It; ++It)
    {
        if (It->GetOwner() != InGenerator || !It->ActorHasTag(RoomTag)) continue;
        FString Id;
        for (FName Tag : It->Tags)
            if (Tag.ToString().StartsWith(Prefix)) { Id = Tag.ToString().RightChop(Prefix.Len()); break; }
        if (Id.IsEmpty()) continue;
        auto* Door = Doors.FindByPredicate([&Id](const auto& D) { return D.Id == Id; });
        if (!Door) { Door = &Doors.AddDefaulted_GetRef(); Door->Id = Id; }
        const UStaticMesh* Mesh = It->GetStaticMeshComponent()->GetStaticMesh();
        if (Mesh && Mesh->GetName() == TEXT("SM_Entry_DoorLeaf"))
        { Door->Left = *It; Door->ClosedLeft = It->GetActorTransform(); }
        else if (Mesh && Mesh->GetName() == TEXT("SM_Entry_DoorLeafRight"))
        { Door->Right = *It; Door->ClosedRight = It->GetActorTransform(); }
    }
    Doors.RemoveAll([](const auto& D) { return !D.Left.IsValid() || !D.Right.IsValid(); });
    Doors.Sort([](const auto& A, const auto& B) { return A.Id < B.Id; });
    for (auto& Door : Doors)
    {
        Door.FloorCenter = (Door.ClosedLeft.GetLocation() + Door.ClosedRight.GetLocation()) * .5;
        Door.Inward = Door.ClosedLeft.GetRotation().GetForwardVector().GetSafeNormal2D();
    }
    if (Doors.IsEmpty())
    {
        UE_LOG(LogTemp, Error, TEXT("[HallWaves] %s has no complete authored service doors; encounter not started."), *Room.Module);
        return;
    }
    EnableServiceDoorReplication();
    const uint32 Salt = InRun->NodeRandomSalt(Room.Id);
    FRandomStream Composition(int32(HashCombineFast(uint32(InRun->RunSeed()), DungeonRunDomains::SpawnComposition ^ Salt)));
    Placement.Initialize(int32(HashCombineFast(uint32(InRun->RunSeed()), DungeonRunDomains::SpawnPlacement ^ Salt)));
    FirstWaveCount = Composition.RandRange(12, 15) + BellowCount;
    const int32 SecondWaveCount = Composition.RandRange(12, 15);
    if (bAddElite) ObjectiveEliteSlot = FirstWaveCount++;
    Slots.SetNum(FirstWaveCount + SecondWaveCount);
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
    {
        auto& Slot = Slots[Index];
        if (Index == ObjectiveEliteSlot)
        {
            Slot.Member = EliteMember;
            Slot.bObjectiveElite = true;
        }
        else if (Index < BellowCount)
        {
            Slot.Member = StaffClassCount;
            Slot.BellowPosition = Index;
        }
        else Slot.Member = Composition.RandRange(0, StaffClassCount - 1);
    }
    GetWorldTimerManager().SetTimer(EncounterTimer, this, &AFacilityHallEncounter::UpdateEncounter, .2f, true);
    UE_LOG(LogTemp, Log, TEXT("[HallWaves] %s: wave1=%d (staff + 2 ground / 2 upper Bellow) wave2=%d staff trigger=%d kills service_doors=%d"),
        *Room.Module, FirstWaveCount, SecondWaveCount, (FirstWaveCount - (bAddElite ? 1 : 0)) / 2 + 1, Doors.Num());
}

APawn* AFacilityHallEncounter::PlayerInHall() const
{
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Pawn = It->Get() ? It->Get()->GetPawn().Get() : nullptr;
        if (!IsValid(Pawn) || Room.DistanceSquared(Pawn->GetActorLocation()) > FMath::Square(20.)) continue;
        const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        if (!Health || !Health->IsDead()) return Pawn;
    }
    return nullptr;
}

bool AFacilityHallEncounter::SpawnSlot(int32 SlotIndex)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHallSpawn_Create);
    const FString PerfKey=FString::Printf(TEXT("room=%d module=%s slot=%d wave=%d"),Room.Id,*Room.Module,SlotIndex,SlotIndex>=FirstWaveCount?2:1);
    FFPSPerformanceScope SpawnScope(this,TEXT("Hall.SpawnAttempt"),PerfKey,true);
    auto& Slot = Slots[SlotIndex];
    if (!IsSlotReleased(Slot)) return false;
    SpawnPathQueriesRemaining=3;
    const auto* Defaults = Members[Slot.Member]->GetDefaultObject<ACharacter>();
    const bool Reinforcement = SlotIndex >= FirstWaveCount;
    const bool FreightReinforcement = Slot.FreightDoor != INDEX_NONE;
    if(FreightReinforcement&&(IsFreightBossDefeated()||!FreightTargetNear(Room.Origin)))return false;
    FVector Location;
    FRotator Facing;
    FFacilityHallDoor* Exit = nullptr;
    if (Reinforcement)
    {
        for (int32 Attempt = 0; Attempt < Doors.Num(); ++Attempt)
        {
            auto& Door = Doors[(NextDoor + Attempt) % Doors.Num()];
            if(FreightReinforcement && (NextDoor+Attempt)%Doors.Num()!=Slot.FreightDoor)continue;
            if(FreightReinforcement&&(!Door.Left.IsValid()||!Door.Right.IsValid()))continue;
            if (Door.OpenAlpha < .999f || GetWorld()->GetTimeSeconds() < Door.NextSpawnAt) continue;
            // Inside the real 150 cm service recess, behind its authored hinged leaves.
            // Never move a rejected spawn out into the middle of the hall.
            if (!FindSpawn(Defaults, Door.FloorCenter - Door.Inward * 65., Location)) continue;
            // Keep the real service-door origin; wait for the previous entrant
            // to move clear instead of stacking another body in the recess.
            if (IsHall(Room.Module) && !Slot.bObjectiveElite && Slot.BellowPosition == INDEX_NONE && Theme.IsValid()
                && !Theme->HasHallSpace(Location-FVector(0,0,Defaults->GetSimpleCollisionHalfHeight()),
                    Defaults->GetSimpleCollisionRadius(),nullptr,70.f,false)) continue;
            Exit = &Door;
            NextDoor = (NextDoor + Attempt + 1) % Doors.Num();
            Facing = Door.Inward.Rotation();
            break;
        }
        if (!Exit) return false;
    }
    else if (!FindInitialSpawn(Slot, Defaults, Location, Facing)) return false;
    const FTransform Transform(Facing, Location);
    ACharacter* Monster = nullptr;
    const int32 PreparedIndex = PreparedMonsters.IndexOfByPredicate([&](const auto& Entry)
        { return Entry->Slot == SlotIndex && Entry->Monster.IsValid() && Entry->Monster->GetClass() == Members[Slot.Member]; });
    const auto* Prepared = PreparedIndex != INDEX_NONE ? PreparedMonsters[PreparedIndex].Get() : nullptr;
    const bool bPreparedHit = Prepared != nullptr;
    const FString PreparationDetail = FString::Printf(TEXT(" preparation=%s prepared_slot=%d prepared_age=%.3f warmup=%s"),
        bPreparedHit ? TEXT("hit") : !PreparedMonsters.IsEmpty() ? TEXT("other_slot") : TEXT("not_prepared"),
        Prepared ? Prepared->Slot : INDEX_NONE, Prepared ? GetWorld()->GetTimeSeconds() - Prepared->PreparedAt : 0.,
        Prepared && Prepared->GpuWarmup ? *Prepared->GpuWarmup->Stage().ToString() : TEXT("none"));
    if (bPreparedHit)
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHallSpawn_ActivatePrepared);
        auto Entry = MoveTemp(PreparedMonsters[PreparedIndex]);
        PreparedMonsters.RemoveAt(PreparedIndex);
        Monster = Entry->Monster.Get();
        if (Entry->GpuWarmup) Entry->GpuWarmup->RestoreForActivation();
        // Placement and RNG run above at the original spawn time. BeginPlay,
        // AI possession, timers and all gameplay initialization run below once.
        Monster->Tags = MoveTemp(Entry->Tags);
        Monster->SetActorHiddenInGame(Entry->bHidden);
        Monster->SetCanBeDamaged(Entry->bDamage);
        Monster->SetActorEnableCollision(Entry->bCollision);
        for (const auto& Component : Entry->AutoActivateComponents)
            if (Component.IsValid()) Component->bAutoActivate = true;
        // No prepared actor is sent to a client. Normal construction, component
        // initialization and initial replication resume together below.
        Monster->SetReplicates(Entry->bReplicates);
        Monster->SpawnCollisionHandlingMethod = ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
    }
    else
    {
        FFPSPerformanceScope AllocationScope(this,TEXT("Hall.NativeAllocation"),PerfKey,true);
        Monster = GetWorld()->SpawnActorDeferred<ACharacter>(Members[Slot.Member], Transform, this, nullptr,
            ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding);
    }
    if (!Monster) return false;
    // Mantis and regional lords also inherit NurseZombie. Only actual ordinary
    // staff slots use this override; preserve each special species' native rank.
    const bool bOrdinaryStaff = bMedical ? Slot.Member < StaffClassCount
        : bFreight ? Slot.Member < 2 : bEcology ? Slot.Member == 0
        : bPower || bIncineration ? Slot.Member < 2
        : bStaffLiving ? Slot.Member < StaffClassCount : !Slot.bObjectiveElite && !bFinalBossRoom;
    if (auto* Staff = Cast<ANurseZombie>(Monster); Staff && bOrdinaryStaff) Staff->Rank = EMonsterRank::Normal;
    if (auto* Bellow = Cast<ABellowSacLobber>(Monster)) Bellow->Rank = EMonsterRank::Normal;
    if (auto* Bell = Cast<AHangingBellM09>(Monster); Bell && bMedical) Bell->Rank = EMonsterRank::Normal;
    if (bStaffLiving)
    {
        // Mantis and BlindSupplicant inherit NurseZombie too; retain their species ranks.
        if (auto* Mantis = Cast<AMantisM27Monster>(Monster)) Mantis->Rank = EMonsterRank::Elite;
        if (auto* Lurker = Cast<ALurkerM08Monster>(Monster)) Lurker->Rank = EMonsterRank::Elite;
        if (Slot.bStaffLivingBoss)
        {
            CastChecked<ABlindSupplicantMonster>(Monster)->Rank = EMonsterRank::Lord;
            Monster->Tags.AddUnique(TEXT("DungeonObjective.StaffLivingBoss"));
        }
    }
    if (Slot.bMedicalBoss)
    {
        CastChecked<ABoundCongregate>(Monster)->Rank = EMonsterRank::Lord;
        Monster->Tags.AddUnique(TEXT("DungeonObjective.MedicalBoss"));
    }
    if (Slot.bFreightBoss)
    {
        CastChecked<AM10Mawcrawler>(Monster)->Rank = EMonsterRank::Lord;
        Monster->Tags.AddUnique(TEXT("DungeonObjective.FreightBoss"));
    }
    if (Slot.bEcologyBoss)
    {
        CastChecked<ARootCrownRigPreview>(Monster)->Rank = EMonsterRank::Lord;
        Monster->Tags.AddUnique(TEXT("DungeonObjective.EcologyBoss"));
    }
    if (Slot.bPowerBoss)
    {
        CastChecked<AVortexCofferM25>(Monster)->Rank = EMonsterRank::Lord;
        Monster->Tags.AddUnique(TEXT("DungeonObjective.PowerBoss"));
    }
    if (Slot.bIncinerationBoss)
    {
        CastChecked<AM66IncineratorMonster>(Monster)->Rank = EMonsterRank::Lord;
        Monster->Tags.AddUnique(TEXT("DungeonObjective.IncinerationBoss"));
    }
    if(Slot.bFinalBoss)
    {
        auto* FinalBoss=CastChecked<AHeQueMonster>(Monster);
        FinalBoss->Rank=EMonsterRank::Lord;
        Monster->Tags.AddUnique(TEXT("DungeonObjective.FinalBoss"));
    }
    if (Slot.bObjectiveElite)
    {
        // Set before component BeginPlay so rank, toughness and kill rewards all
        // use the existing elite rules, including on a retried spawn of this slot.
        auto* Rank = FindFProperty<FEnumProperty>(Monster->GetClass(), TEXT("Rank"));
        Rank->GetUnderlyingProperty()->SetIntPropertyValue(Rank->ContainerPtrToValuePtr<void>(Monster), int64(EMonsterRank::Elite));
        Monster->Tags.AddUnique(TEXT("DungeonObjective.WelcomeElite"));
    }
    Monster->Tags.AddUnique(Run->EnemySlotTag(Room.Id, Slot.RewardSlot==INDEX_NONE?SlotIndex:Slot.RewardSlot));
    if(FreightReinforcement)Monster->Tags.AddUnique(TEXT("FacilityFreightReinforcement"));
    Monster->Tags.AddUnique(bStaffLiving ? TEXT("FacilityStaffLivingEnemy") : bIncineration ? TEXT("FacilityIncinerationEnemy") : bPower ? TEXT("FacilityPowerEnemy") : bEcology ? TEXT("FacilityEcologyEnemy") : bFreight ? TEXT("FacilityFreightEnemy") : bMedical ? TEXT("FacilityMedicalEnemy") : TEXT("FacilityHallEnemy"));
    if (Slot.bIncinerationBasement) Monster->Tags.AddUnique(TEXT("FacilityIncineration.Basement"));
    if (Slot.BellowPosition != INDEX_NONE)
        Monster->Tags.AddUnique(Slot.BellowPosition >= 2 ? TEXT("FacilityHallBellow.Upper") : TEXT("FacilityHallBellow.Ground"));
    Slot.Monster = Monster;
    if (!bMedical && !bFreight && !bEcology && !bPower && !bIncineration && !bFinalBossRoom && !bStaffLiving && !Slot.bObjectiveElite)
    {
        Monster->OnTakeAnyDamage.AddDynamic(this, &AFacilityHallEncounter::MonsterDamaged);
        Monster->OnDestroyed.AddDynamic(this, &AFacilityHallEncounter::MonsterDestroyed);
    }
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHallSpawn_FinishSpawning);
        FFPSPerformanceScope FinishScope(this,TEXT("Hall.FinishSpawning"),PerfKey,true);
        Monster->FinishSpawning(Transform);
    }
    if (!IsValid(Monster)) return false;
    // BeginPlay can reject placement or initialization. Bind objective death
    // callbacks only after a live spawn, so failure cannot complete the task.
    if (bMedical || bFreight || bEcology || bPower || bIncineration || bFinalBossRoom || bStaffLiving || Slot.bObjectiveElite)
    {
        const auto* Combat = Monster->FindComponentByClass<UMonsterCombatComponent>();
        float Health=0.f, MaxHealth=0.f; FText Name;
        if (!Combat || !Combat->GetVitals(Health, MaxHealth, Name) || Health <= 0.f)
        { Slot.Monster.Reset(); Monster->Destroy(); return false; }
    }
    if (bMedical || bFreight || bEcology || bPower || bIncineration || bFinalBossRoom || bStaffLiving || Slot.bObjectiveElite)
    {
        Monster->OnTakeAnyDamage.AddDynamic(this, &AFacilityHallEncounter::MonsterDamaged);
        Monster->OnDestroyed.AddDynamic(this, &AFacilityHallEncounter::MonsterDestroyed);
    }
    bool& WaveObserved=Reinforcement?bSecondWaveObserved:bFirstWaveObserved;
    if(!WaveObserved)
    {
        WaveObserved=true;
        UFPSPerformanceMetricsSubsystem::StartCombatWindow(this,FString::Printf(TEXT("room=%d module=%s wave=%d first_spawn"),Room.Id,*Room.Module,Reinforcement?2:1));
    }
    UFPSPerformanceMetricsSubsystem::RecordMarker(this,TEXT("Hall.SpawnActivated"),
        PerfKey+FString::Printf(TEXT(" prepared=%d actor=%s class=%s"),bPreparedHit?1:0,*Monster->GetPathName(),*Monster->GetClass()->GetPathName())+PreparationDetail,true);
    if (!Monster->GetController()) Monster->SpawnDefaultController();
    if (Exit)
    {
        // Existing return-home BT moves an entrant out even if the player has left.
        if (auto* Staff = Cast<ANurseZombie>(Monster))
            Staff->SpawnPosition = Exit->FloorCenter + Exit->Inward * 250. + FVector(0,0,Monster->GetSimpleCollisionHalfHeight());
        Exit->NextSpawnAt = GetWorld()->GetTimeSeconds() + 1.;
        if(FreightReinforcement)Exit->HoldOpenUntil=GetWorld()->GetTimeSeconds()+2.;
    }
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController()))
    {
        AI->SetEncounterArea(Theme.Get());
        if(FreightReinforcement)
        {
            Slot.FreightTarget=FreightTargetNear(Monster->GetActorLocation());
            AI->SetEncounterTarget(Slot.FreightTarget.Get());
        }
        AI->UpdateKnowledge();
    }
    if (Slot.bObjectiveElite)
        UE_LOG(LogTemp, Log, TEXT("[HallWaves] Objective elite spawned: room=%s class=%s location=%s first_wave_kills=%d"),
            *Room.Module, *Monster->GetClass()->GetPathName(), *Monster->GetActorLocation().ToCompactString(), FirstWaveKills);
    if(Slot.bFinalBoss)SpawnPumpControls(Cast<AHeQueMonster>(Monster));
    return true;
}

void AFacilityHallEncounter::RecordDefeat(AActor* Actor)
{
    if (bStopping || !HasAuthority() || !Actor) return;
    const auto* Combat = Actor->FindComponentByClass<UMonsterCombatComponent>();
    float Health = 0.f, MaxHealth = 0.f;
    FText Name;
    // Both staff and Bellow update health before broadcasting OnTakeAnyDamage;
    // their death-state enums may still be transitioning inside that callback.
    if (!Combat || !Combat->GetVitals(Health, MaxHealth, Name) || Health > 0.f) return;
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
    {
        auto& Slot = Slots[Index];
        if (Slot.Monster.Get() != Actor || Slot.bDefeated) continue;
        Slot.bDefeated = true;
        UFPSPerformanceMetricsSubsystem::RecordMarker(this,TEXT("Hall.Defeated"),
            FString::Printf(TEXT("room=%d slot=%d elite=%d actor=%s"),Room.Id,Index,Slot.bObjectiveElite?1:0,*Actor->GetPathName()),true);
        if(Run.IsValid())
        {
            Run->RecordRoomDefeat(Room.Id);
            // Any player's authoritative kill completes the same team objective.
            if(Slot.bObjectiveElite || Slot.bMedicalBoss || Slot.bFreightBoss || Slot.bEcologyBoss || Slot.bPowerBoss || Slot.bIncinerationBoss || Slot.bFinalBoss || Slot.bStaffLivingBoss)Run->PublishSharedProgress();
        }
        if (Index < FirstWaveCount && !Slot.bObjectiveElite) ++FirstWaveKills;
        const int32 OrdinaryFirstWaveCount = FirstWaveCount - (ObjectiveEliteSlot != INDEX_NONE ? 1 : 0);
        const bool bOriginalHallWaves = IsHall(Room.Module);
        const bool bReinforcementsDue = bOriginalHallWaves
            ? FirstWaveKills * 2 > OrdinaryFirstWaveCount : FirstWaveKills >= OrdinaryFirstWaveCount;
        if (!bSecondWave && bReinforcementsDue)
        {
            bSecondWave = true;
            ReinforcementReleaseAt=PacingClock+(bOriginalHallWaves?0.:6.);
            UFPSPerformanceMetricsSubsystem::RecordMarker(this,TEXT("Hall.Wave2Triggered"),FString::Printf(TEXT("room=%d killed=%d first=%d"),Room.Id,FirstWaveKills,OrdinaryFirstWaveCount),true);
            UE_LOG(LogTemp, Log, TEXT("[HallWaves] %s wave2 triggered: killed=%d/%d count=%d"),
                *Room.Module, FirstWaveKills, FirstWaveCount, Slots.Num() - FirstWaveCount);
        }
        return;
    }
}

void AFacilityHallEncounter::MonsterDamaged(AActor* Actor, float, const UDamageType*, AController*, AActor*)
{
    // Species health is authoritative before Super::TakeDamage broadcasts this event.
    // Schedule on the timer; never spawn or commit profile state inside the damage stack.
    RecordDefeat(Actor);
}

void AFacilityHallEncounter::MonsterDestroyed(AActor* Actor)
{
    if (bStopping) return;
    RecordDefeat(Actor);
    for (auto& Slot : Slots)
        if (Slot.Monster.Get() == Actor) { Slot.Monster.Reset(); break; }
    // Non-lethal deletion leaves the same slot pending, never counts as a kill.
}

void AFacilityHallEncounter::DungeonDestroyed(AActor*)
{
    Destroy();
}

bool AFacilityHallEncounter::DoorOccupied(const FFacilityHallDoor& Door) const
{
    FCollisionObjectQueryParams Pawns(ECC_Pawn);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FacilityHallDoor), false, this);
    return GetWorld()->OverlapAnyTestByObjectType(Door.FloorCenter - Door.Inward * 20. + FVector(0,0,140),
        Door.Inward.Rotation().Quaternion(), Pawns, FCollisionShape::MakeBox(FVector(150,105,140)), Query);
}

void AFacilityHallEncounter::ApplyDoorPose(FFacilityHallDoor& Door)
{
    // Ease the complete open/close motion; each leaf rotates around its real hinge.
    const float A = FMath::SmoothStep(0.f, 1.f, Door.OpenAlpha);
    if (Door.Left.IsValid()) Door.Left->SetActorRotation(Door.ClosedLeft.GetRotation() * FQuat(FVector::UpVector, FMath::DegreesToRadians(85.f * A)));
    if (Door.Right.IsValid()) Door.Right->SetActorRotation(Door.ClosedRight.GetRotation() * FQuat(FVector::UpVector, FMath::DegreesToRadians(-85.f * A)));
}

void AFacilityHallEncounter::Tick(float Dt)
{
    Super::Tick(Dt);
    if(GetNetMode()==NM_Client){PresentFreightDoors();return;}
    bool Moving = false;
    for (auto& Door : Doors)
    {
        const float Target = Door.bWantOpen ? 1.f : 0.f;
        if (Door.OpenAlpha == Target) continue;
        if (!Door.bWantOpen && DoorOccupied(Door)) { Moving = true; continue; }
        Door.OpenAlpha = FMath::FInterpConstantTo(Door.OpenAlpha, Target, Dt, 1.f / .7f);
        ApplyDoorPose(Door);
        Moving |= Door.OpenAlpha != Target;
    }
    PublishFreightDoors();
    SetActorTickEnabled(Moving);
}

void AFacilityHallEncounter::UpdateEncounter()
{
    if (bStopping) return;
    if (!Run.IsValid() || !Run->IsRunActive() || !Generator.IsValid()) { Destroy(); return; }
    // The area's update is the single owner of optional preparation requests.
    // This room timer only advances its existing gameplay/wave state.
    if (!bConfigured || Generator->IsPreparationPending() || !Theme.IsValid() || !Theme->HasStarted()) return;
    // Entering the approach starts spawning, not omniscient aggro. Each monster
    // acquires through sight/damage or investigates a nearby ally's warning.
    if (PlayerInHall()) Run->MarkRoomExplored(Room.Id);
    if (bIncineration) UpdateIncinerationBasement();
    // Death delegates handle the normal path; this also observes non-damage death transitions.
    for (auto& Slot : Slots)
        if (!Slot.bDefeated && Slot.Monster.IsValid()) RecordDefeat(Slot.Monster.Get());
    UpdatePacing();
    if(bFreight&&FreightBossSlot!=INDEX_NONE&&Theme->HasEnteredArea())UpdateFreightReinforcements();
    bool PendingReinforcements = false;
    for (int32 Index = FirstWaveCount; Index < Slots.Num(); ++Index)
        PendingReinforcements |= !Slots[Index].bDefeated && !Slots[Index].Monster.IsValid();
    double AreaDistance=0.;const int32 AreaPriority=Theme->PreparationPriority(AreaDistance);
    for (auto& Door : Doors)
    {
        bool WantOpen = bSecondWave && PacingClock>=ReinforcementReleaseAt && PendingReinforcements && (AreaPriority==0||AreaPriority==1);
        if(bFreight)
        {
            const int32 DoorIndex=int32(&Door-Doors.GetData());
            WantOpen=GetWorld()->GetTimeSeconds()<Door.HoldOpenUntil;
            if(!IsFreightBossDefeated()&&FreightTargetNear(Door.FloorCenter))
                WantOpen|=Slots.ContainsByPredicate([DoorIndex](const auto& S)
                    {return S.FreightDoor==DoorIndex&&!S.bDefeated&&!S.Monster.IsValid();});
        }
        if (Door.bWantOpen != WantOpen)
        { Door.bWantOpen = WantOpen; SetActorTickEnabled(true); }
    }
    // Keep per-hall cadence and composition; a world queue separates halls which
    // otherwise fire on the same frame and accumulate render registration work.
    const int32 Eligible = bSecondWave ? Slots.Num() : FirstWaveCount;
    for (int32 Index = 0; Index < Eligible; ++Index)
        if (IsSlotReleased(Slots[Index]) && !Slots[Index].bDefeated && !Slots[Index].Monster.IsValid())
        {
            if(SpawnPriority()!=INDEX_NONE)GetWorld()->GetSubsystem<UFacilityHallSpawnSubsystem>()->Request(this);
            break;
        }
    if (!bCleared && bSecondWave && !Slots.ContainsByPredicate([](const auto& S) { return !S.bDefeated; }))
    {
        bCleared = true;
        if(bFreight)for(auto& Door:Doors)
        {Door.HoldOpenUntil=0.;Door.bWantOpen=false;SetActorTickEnabled(true);}
        Run->MarkRoomCleared(Room.Id);
        GetWorldTimerManager().ClearTimer(EncounterTimer);
        UE_LOG(LogTemp, Log, TEXT("[HallWaves] %s cleared: waves=%d kills=%d"), *Room.Module,(bMedical||bFreight||bEcology||bPower||bIncineration||bStaffLiving||bFinalBossRoom)?1:2,Slots.Num());
    }
}

bool AFacilityHallEncounter::TrySpawnObjectiveElite()
{
    const bool bSpawned = SpawnSlot(ObjectiveEliteSlot);
    if (bSpawned)
    {
        ObjectiveEliteFailedAttempts = 0;
        return true;
    }
    // Each attempt already samples up to twelve valid positions. Keep one
    // attempt per scheduler admission, then switch species after three failures.
    auto& Slot = Slots[ObjectiveEliteSlot];
    if (Slot.bDefeated || Slot.Monster.IsValid()
        || ++ObjectiveEliteFailedAttempts < EliteAttemptsBeforeReplacement) return false;
    ObjectiveEliteFailedAttempts = 0;
    if (ObjectiveEliteCandidates.Num() < 2) return false;
    const int32 PreviousMember = Slot.Member;
    ObjectiveEliteCandidate = (ObjectiveEliteCandidate + 1) % ObjectiveEliteCandidates.Num();
    const auto& Candidate = ObjectiveEliteCandidates[ObjectiveEliteCandidate];
    Slot.Member = Candidate.Member;
    ObjectiveEliteFootprint = Candidate.Footprint;
    // Same objective slot and server-owned completion state; no kill/reward on
    // replacement. If all candidates are blocked, retry them at the normal rate.
    UE_LOG(LogTemp, Log, TEXT("[HallWaves] Objective elite replacement: room=%s slot=%d from=%s to=%s failed_attempts=%d"),
        *Room.Module, ObjectiveEliteSlot, *Members[PreviousMember]->GetPathName(),
        *Members[Slot.Member]->GetPathName(), EliteAttemptsBeforeReplacement);
    return false;
}

bool AFacilityHallEncounter::TrySpawnPendingSlot()
{
    // Requests can outlive a theme/run transition. Recheck ownership before any
    // placement RNG, navigation query, actor construction or AI activation.
    if (SpawnPriority()==INDEX_NONE) return false;
    // The welcome objective gets the first spawn attempt when its approach activates the area.
    // Keep its stable slot/reward identity, but bypass ordinary wave order and kill thresholds.
    // A rejected elite placement yields one admission to ordinary monsters before
    // retrying, so a blocked elite cannot stop the entire hall from spawning.
    const bool bElitePending = Slots.IsValidIndex(ObjectiveEliteSlot)
        && !Slots[ObjectiveEliteSlot].bDefeated && !Slots[ObjectiveEliteSlot].Monster.IsValid();
    if (bElitePending && !bYieldObjectiveEliteRetry)
    {
        const bool bSpawned = TrySpawnObjectiveElite();
        bYieldObjectiveEliteRetry = !bSpawned;
        return bSpawned;
    }
    bYieldObjectiveEliteRetry = false;
    const int32 Eligible = bSecondWave ? Slots.Num() : FirstWaveCount;
    for (int32 Offset = 0; Offset < Eligible; ++Offset)
    {
        const int32 Index = (NextSlot + Offset) % Eligible;
        if (Index != ObjectiveEliteSlot && IsSlotReleased(Slots[Index]) && !Slots[Index].bDefeated && !Slots[Index].Monster.IsValid())
        {
            // One bounded attempt per admission. A blocked balcony must not
            // starve the ground-floor slots or service-door reinforcements.
            NextSlot = (Index + 1) % Eligible;
            return SpawnSlot(Index);
        }
    }
    // Nothing ordinary is pending; spend this admission on the objective retry.
    return bElitePending && TrySpawnObjectiveElite();
}

void AFacilityHallEncounter::EndPlay(const EEndPlayReason::Type Reason)
{
    bStopping = true;
    if(GetNetMode()==NM_Client){Super::EndPlay(Reason);return;}
    for(auto& Control:PumpControls)if(Control.IsValid())Control->Destroy();
    PumpControls.Reset();
    DiscardPreparedMonster();
    if (auto* Scheduler = GetWorld()->GetSubsystem<UFacilityHallSpawnSubsystem>()) Scheduler->Cancel(this);
    GetWorldTimerManager().ClearTimer(EncounterTimer);
    if (Generator.IsValid()) Generator->OnDestroyed.RemoveDynamic(this, &AFacilityHallEncounter::DungeonDestroyed);
    for (auto& Slot : Slots)
        if (auto* Monster = Slot.Monster.Get())
        {
            Monster->OnTakeAnyDamage.RemoveDynamic(this, &AFacilityHallEncounter::MonsterDamaged);
            Monster->OnDestroyed.RemoveDynamic(this, &AFacilityHallEncounter::MonsterDestroyed);
            Monster->Destroy();
        }
    // Recycled reinforcement slots can leave presentation-only corpses behind.
    // They retain this owner and are retired with the encounter, without a kill.
    if(bFreight)for(TActorIterator<ACharacter> It(GetWorld());It;++It)
        if(It->GetOwner()==this&&It->ActorHasTag(TEXT("FacilityFreightReinforcement")))It->Destroy();
    for (auto& Door : Doors)
    {
        if (Door.Left.IsValid()) Door.Left->SetActorTransform(Door.ClosedLeft);
        if (Door.Right.IsValid()) Door.Right->SetActorTransform(Door.ClosedRight);
    }
    Super::EndPlay(Reason);
}
