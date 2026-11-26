#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"

namespace FacilityEncounterPacing
{
bool IsObjective(const FFacilityHallSlot& S)
{
    return S.bObjectiveElite||S.bMedicalBoss||S.bFreightBoss||S.bEcologyBoss
        ||S.bPowerBoss||S.bIncinerationBoss||S.bStaffLivingBoss||S.bFinalBoss;
}
}

void AFacilityHallEncounter::ConfigurePacing()
{
    // Welcome halls retain their original complete first wave. Preparation is
    // optional work ahead of activation, never a new kill-gated release rule.
    if(bFinalBossRoom||IsHall(Room.Module))return;
    // Stable slots retain their original placement, rewards, floor and boss identity.
    // Divide ordinary front-line, ranged/control and flanking roles among small mixed groups.
    TArray<int32> Roles[3];
    int32 Ordinary=0;
    for(int32 I=0;I<FirstWaveCount;++I)
    {
        const auto& S=Slots[I];
        if(FacilityEncounterPacing::IsObjective(S)||S.bIncinerationBasement)continue;
        // Use the same stable member identities as Configure*, independent of display names.
        const bool Control=S.bCeiling||S.BellowPosition!=INDEX_NONE||(bFreight&&S.Member==3)
            ||(bEcology&&S.Member==1)||(bIncineration&&S.Member==2);
        const bool Flank=(bMedical&&S.Member==3)||(bFreight&&S.Member==2)
            ||(bStaffLiving&&(S.Member==3||S.Member==4))||(bIncineration&&S.Member==3);
        const int32 PacingRole=Control?1:Flank?2:0;
        Roles[PacingRole].Add(I);++Ordinary;
    }
    // Small rooms remain a single encounter; do not turn eight staff into two tiny waves.
    const int32 Groups=Ordinary<=9?1:FMath::DivideAndRoundUp(Ordinary,8);
    LastReleaseGroup=Groups-1;
    FRandomStream Draw=Run->GameplayStream(DungeonRunDomains::EncounterGroups^Run->NodeRandomSalt(Room.Id));
    TArray<int32> Sizes;Sizes.Init(0,Groups);
    // A separate stream varies which special role accompanies the opening group.
    for(int32 PacingRole:{1,2,0})
    {
        auto& Pool=Roles[PacingRole];
        for(int32 I=Pool.Num()-1;I>0;--I)Pool.Swap(I,Draw.RandRange(0,I));
        int32 Next=Draw.RandRange(0,Groups-1);
        for(int32 Index:Pool)
        {
            int32 Group=Next;
            for(int32 Offset=1;Offset<Groups;++Offset)
            {const int32 Candidate=(Next+Offset)%Groups;if(Sizes[Candidate]<Sizes[Group])Group=Candidate;}
            Slots[Index].ReleaseGroup=Group;++Sizes[Group];Next=(Group+1)%Groups;
        }
    }
}

bool AFacilityHallEncounter::IsSlotReleased(const FFacilityHallSlot& Slot) const
{
    if(Slot.bIncinerationBasement&&!bIncinerationBasementEntered)return false;
    if(Slot.ReleaseGroup>CurrentReleaseGroup)return false;
    const int32 Index=int32(&Slot-Slots.GetData());
    return Index<FirstWaveCount||(bSecondWave&&PacingClock>=ReinforcementReleaseAt);
}

void AFacilityHallEncounter::UpdatePacing()
{
    const double Now=GetWorld()->GetTimeSeconds();
    const double Delta=LastPacingUpdate<0.?0.:FMath::Clamp(Now-LastPacingUpdate,0.,.5);
    LastPacingUpdate=Now;
    // Leaving the room pauses the breather and never drains the entire schedule off screen.
    if(!PlayerInHall())return;
    PacingClock+=Delta;
    if(CurrentReleaseGroup>=LastReleaseGroup)return;
    int32 Alive=0;bool Pending=false;
    for(int32 I=0;I<FirstWaveCount;++I)
    {
        const auto& S=Slots[I];
        if(FacilityEncounterPacing::IsObjective(S)||S.bIncinerationBasement||S.ReleaseGroup>CurrentReleaseGroup||S.bDefeated)continue;
        if(S.Monster.IsValid())++Alive;else Pending=true;
    }
    // A rejected balcony/large-body placement keeps retrying in its original slot,
    // but must not monopolize the entire room's later groups indefinitely.
    if(Alive>2||(Pending&&PacingClock-LastGroupReleasedAt<18.)){GroupReleaseAt=-1.;return;}
    if(GroupReleaseAt<0.)GroupReleaseAt=PacingClock+6.;
    if(PacingClock>=GroupReleaseAt){++CurrentReleaseGroup;LastGroupReleasedAt=PacingClock;GroupReleaseAt=-1.;}
}
