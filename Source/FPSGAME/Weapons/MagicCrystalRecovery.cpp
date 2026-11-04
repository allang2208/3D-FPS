#include "MagicCrystalMana.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Engine/GameInstance.h"

void UColdSteelStatusModel::RestoreMagicCrystalResources(AActor* Shooter,float HealthAmount,float ManaAmount)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(Shooter);
    auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Pawn||!Pawn->HasAuthority()||!Health||Health->IsDead())return;
    bool Changed=false;
    if(HealthAmount>0.f)
    {
        const float Before=Health->Health;
        Health->Health=FMath::Min(Health->MaxHealth,Before+HealthAmount);
        Current.Health=Health->Health;
        Changed=Health->Health>Before;
        if(Changed)Pawn->ForceNetUpdate();
    }
    if(ManaAmount>0.f&&!HasInfiniteMana())
    {
        const float Before=Current.Mana;
        Current.Mana=FMath::Clamp(Before+ManaAmount,0.f,Derived(TEXT("maxMp")));
        const float Restored=Current.Mana-Before;
        if(Restored>0.f)
        {
            Current.MagicCrystalManaRestored+=Restored;
            Changed=true;
            if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())
                PS->NotifyMagicCrystalMana(Pawn,Current.MagicCrystalManaRestored);
        }
    }
    // Use the combat save queue; never write a save slot for each target hit.
    if(Changed){bTrainingDirty=true;TrainingFlushAccumulator=0.f;OnChanged.Broadcast();}
}

void UColdSteelStatusModel::ReconcileMagicCrystalMana(double Total)
{
    if(!FMath::IsFinite(Total)||Total<=Current.MagicCrystalManaRestored)return;
    MagicCrystalMana::Merge(Current,Total,Derived(TEXT("maxMp")));
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;OnChanged.Broadcast();
}

void AColdSteelPlayerState::NotifyMagicCrystalMana(AFPSGAMECharacter* Character,double Total)
{
    if(!HasAuthority()||!Character||Character!=GetPawn())return;
    bServerDirty=true;ShadowMirrorTimer=3.f;
    if(!Character->IsLocallyControlled())ClientMagicCrystalMana(Character,Total);
}

void AColdSteelPlayerState::ClientMagicCrystalMana_Implementation(AFPSGAMECharacter* Character,double Total)
{
    if(!Character||Character!=GetPawn())return;
    if(auto* GI=GetGameInstance())if(auto* Model=GI->GetSubsystem<UColdSteelStatusModel>())
        Model->ReconcileMagicCrystalMana(Total);
}
