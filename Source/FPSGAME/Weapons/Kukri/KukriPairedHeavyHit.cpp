#include "KukriPairedHeavyHit.h"
#include "KukriWeaponComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Skills/ColdSteelSkillRules.h"

void UKukriWeaponComponent::FlushPairedHeavyContacts(bool EndWindow)
{
    if(PairedHeavyContacts.IsEmpty())return;
    // Remove pending entries before callbacks can refresh equipment/cancel the
    // action. Two contacts settle immediately; a lone contact waits only until
    // the authored contact window closes (or the release is interrupted).
    TArray<FKukriHeavyContacts,TInlineAllocator<8>> Ready;
    for(auto It=PairedHeavyContacts.CreateIterator();It;++It)
        if(EndWindow||It.Value().Mask==3){Ready.Add(MoveTemp(It.Value()));It.RemoveCurrent();}
    auto* P=Pawn();if(!P)return;
    for(auto& Contacts:Ready)
    {
        const int32 FirstHand=(Contacts.Mask&1)?0:1;
        auto& First=Contacts.Blades[FirstHand];auto* Target=First.Hit.GetActor();
        auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Combat||Combat->IsDead())continue;
        const bool Train=bHeavyTrainingPending&&ColdSteelSkills::IsMasteryTrainingTarget(P,Target);
        FKukriPairedHeavyHit Pair;
        if(Contacts.Mask==3)Pair.Second=Contacts.Blades[1];
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(P,First.Hit,First.Damage,First.Direction,First.Shot,&Receipt,
            Contacts.Mask==3?&Pair:nullptr);
        if(Applied>0.f||Receipt.bKilled)
        {
            if(!Contacts.bContactPresented){ConfirmImpact(First.Hit,false);if(P->HasAuthority())QueueContactFX(First.Hit,false);}
            P->NotifyConfirmedWeaponHit(Target,Applied,&Receipt,false);
            if(Train)CountHeavyVictim(Target,Receipt.bKilled);
        }
    }
}
