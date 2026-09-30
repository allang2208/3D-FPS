#include "HumanoidRagdollBudget.h"
#include "HumanoidKnockdownComponent.h"
#include "HAL/IConsoleManager.h"

static TAutoConsoleVariable<int32> CVarHumanoidRagdolls(TEXT("fps.MonsterRagdoll.MaxActive"),8,TEXT("Maximum simultaneously simulated humanoids."));
static TAutoConsoleVariable<int32> CVarHumanoidBodies(TEXT("fps.MonsterRagdoll.MaxBodies"),128,TEXT("Maximum active humanoid rigid bodies."));
static TAutoConsoleVariable<int32> CVarHumanoidCorpses(TEXT("fps.MonsterRagdoll.MaxCorpses"),4,TEXT("Admission cap for new corpse simulations. Already airborne living ragdolls retain their slot if killed."));

bool UHumanoidRagdollBudget::Acquire(UHumanoidKnockdownComponent* Candidate, int32 BodyCount, bool bCorpse)
{
    Active.RemoveAll([](const auto& Entry){ return !Entry.IsValid(); });
    if (Active.Contains(Candidate)) return true;
    auto Fits = [&]()
    {
        int32 Bodies=BodyCount, Corpses=bCorpse?1:0;
        for (const auto& Entry:Active) { Bodies+=Entry->SimulatedBodyCount(); Corpses+=Entry->IsCorpse()?1:0; }
        return Active.Num()<FMath::Max(0,CVarHumanoidRagdolls.GetValueOnGameThread()) &&
            Bodies<=FMath::Max(0,CVarHumanoidBodies.GetValueOnGameThread()) &&
            (!bCorpse || Corpses<=FMath::Max(0,CVarHumanoidCorpses.GetValueOnGameThread()));
    };
    if (!Fits() && !bCorpse)
    {
        // A live control may retire a grounded corpse, never another airborne/live body.
        const auto Retire=Active;
        for (const auto& Entry:Retire)
            if (Entry.IsValid() && Entry->CanReleaseCorpseBudget())
            { Entry->FreezeForBudget(); if (Fits()) break; }
    }
    if (!Fits()) return false;
    Active.Add(Candidate);
    return true;
}

void UHumanoidRagdollBudget::Release(UHumanoidKnockdownComponent* Candidate)
{
    Active.RemoveAll([Candidate](const auto& Entry){return !Entry.IsValid() || Entry.Get()==Candidate;});
}
