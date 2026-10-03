#include "HumanoidRagdollBudget.h"
#include "HumanoidKnockdownComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "HundredEyedSlagMonster.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

static TAutoConsoleVariable<int32> CVarHumanoidRagdolls(TEXT("fps.MonsterRagdoll.MaxActive"),8,TEXT("Maximum simultaneously simulated humanoid/corpse budget clients."));
static TAutoConsoleVariable<int32> CVarHumanoidBodies(TEXT("fps.MonsterRagdoll.MaxBodies"),128,TEXT("Maximum active rigid bodies in the shared humanoid/corpse budget."));
static TAutoConsoleVariable<int32> CVarHumanoidCorpses(TEXT("fps.MonsterRagdoll.MaxCorpses"),4,TEXT("Admission cap for new corpse simulations. Already airborne living ragdolls retain their slot if killed."));

bool UHumanoidRagdollBudget::Acquire(UObject* Candidate, int32 BodyCount, bool bCorpse)
{
    if (!Candidate || (!Cast<UHumanoidKnockdownComponent>(Candidate) &&
        !Cast<UMonsterCorpseRagdollComponent>(Candidate) && !Cast<AHundredEyedSlagMonster>(Candidate))) return false;
    Active.RemoveAll([](const auto& Entry){ return !Entry.IsValid(); });
    if (Active.Contains(Candidate)) return true;
    auto Fits = [&]()
    {
        int32 Bodies=BodyCount, Corpses=bCorpse?1:0;
        for (const auto& Entry:Active)
        {
            if (const auto* Humanoid=Cast<UHumanoidKnockdownComponent>(Entry.Get()))
            { Bodies+=Humanoid->SimulatedBodyCount(); Corpses+=Humanoid->IsCorpse()?1:0; }
            else if (const auto* Corpse=Cast<UMonsterCorpseRagdollComponent>(Entry.Get()))
            { Bodies+=Corpse->SimulatedBodyCount(); ++Corpses; }
            else if (const auto* Slag=Cast<AHundredEyedSlagMonster>(Entry.Get()))
            { Bodies+=Slag->SimulatedBodyCount(); ++Corpses; }
        }
        return Active.Num()<FMath::Max(0,CVarHumanoidRagdolls.GetValueOnGameThread()) &&
            Bodies<=FMath::Max(0,CVarHumanoidBodies.GetValueOnGameThread()) &&
            (!bCorpse || Corpses<=FMath::Max(0,CVarHumanoidCorpses.GetValueOnGameThread()));
    };
    if (!Fits() && !bCorpse)
    {
        // A live control may retire a grounded corpse, never another airborne/live body.
        const auto Retire=Active;
        for (const auto& Entry:Retire)
        {
            if (auto* Humanoid=Cast<UHumanoidKnockdownComponent>(Entry.Get()))
            { if (Humanoid->CanReleaseCorpseBudget()) Humanoid->FreezeForBudget(); }
            else if (auto* Corpse=Cast<UMonsterCorpseRagdollComponent>(Entry.Get()))
            { if (Corpse->CanReleaseCorpseBudget()) Corpse->FreezeForBudget(); }
            else if (auto* Slag=Cast<AHundredEyedSlagMonster>(Entry.Get()))
            { if (Slag->CanReleaseCorpseBudget()) Slag->FreezeForBudget(); }
            if (Fits()) break;
        }
    }
    if (!Fits()) return false;
    Active.Add(Candidate);
    return true;
}

void UHumanoidRagdollBudget::Release(UObject* Candidate)
{
    Active.RemoveAll([Candidate](const auto& Entry){return !Entry.IsValid() || Entry.Get()==Candidate;});
}

void UHumanoidRagdollBudget::RegisterFrozenMesh(USkeletalMeshComponent* Mesh)
{
    if (!Mesh || GetWorld()->GetNetMode() == NM_DedicatedServer) return;
    Mesh->SetForcedLOD(0);
    if (Mesh->GetNumLODs() <= 1) return;
    FrozenMeshes.AddUnique(Mesh);
    if (!GetWorld()->GetTimerManager().IsTimerActive(FrozenLODTimer))
        GetWorld()->GetTimerManager().SetTimer(FrozenLODTimer, this,
            &UHumanoidRagdollBudget::UpdateFrozenLODs, .5f, true);
}

void UHumanoidRagdollBudget::UpdateFrozenLODs()
{
    FrozenMeshes.RemoveAll([](const auto& Entry)
    {
        const auto* Mesh = Entry.Get();
        return !Mesh || Mesh->IsComponentTickEnabled() || Mesh->IsSimulatingPhysics();
    });
    for (const auto& Entry : FrozenMeshes)
    {
        auto* Mesh = Entry.Get();
        if (!Mesh->UpdateLODStatus()) continue;
        // Use the renderer's screen-size/streaming choice for every view. The
        // original full snapshot remains held, including when LOD0 returns.
        Mesh->TickAnimation(0.f, false);
        Mesh->RefreshBoneTransforms();
    }
    if (FrozenMeshes.IsEmpty()) GetWorld()->GetTimerManager().ClearTimer(FrozenLODTimer);
}

void UHumanoidRagdollBudget::Deinitialize()
{
    GetWorld()->GetTimerManager().ClearTimer(FrozenLODTimer);
    FrozenMeshes.Reset(); Active.Reset();
    Super::Deinitialize();
}
