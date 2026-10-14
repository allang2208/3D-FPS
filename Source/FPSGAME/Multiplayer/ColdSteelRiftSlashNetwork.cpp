#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/SwordWaveTuning.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

void AColdSteelPlayerState::ServerReleaseRiftSlash_Implementation(uint32 Sequence,const FString& Weapon,
    FVector_NetQuantize Origin,FVector_NetQuantizeNormal Direction,uint32 GuardSerial,bool bAzureDragon,bool bClovenCounter)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(!Pawn||!ShadowModel||!Sequence||Origin.ContainsNaN()||Direction.ContainsNaN()||Direction.IsNearlyZero())return;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(RiftPawn.Get()!=Pawn){RiftPawn=Pawn;LastRiftSequence=0;LastRiftReleasedAt=-100.;}
    const double Now=GetWorld()->GetTimeSeconds();
    if(Sequence<=LastRiftSequence||Now-LastRiftReleasedAt<.75)return;
    const auto* Item=ShadowModel->Equipped();
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    const auto* Enchant=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    if(!Item||Item->InstanceId!=Weapon||!ColdSteelInventory::IsMeleeWeapon(*Item)||!Sword||!Enchant
        ||Enchant->Effect(*Item,TEXT("riftSlash"))<=0.||FVector::DistSquared(Origin,Pawn->GetPawnViewLocation())>FMath::Square(250.f))return;
    const auto Flight=SwordWaveTuning::RiftFlight(Enchant,Item);
    if(Flight.RangeCM<=0.f||Flight.SpeedCM<=0.f)return;
    auto Shot=ColdSteelSkills::Snapshot(Pawn,Item,false);
    Shot.AttackMeta=0x50;Shot.bMelee=true;Shot.bRifle=false;Shot.bPistol=false;
    Shot.GuardAttackSerial=GuardSerial;Shot.GuardSourceInstance=Item->InstanceId;
    Shot.ToughnessDamageMultiplier*=ColdSteelMelee::Evaluate(*Item,ShadowModel).Modifiers.HeavyToughness;
    if(bClovenCounter&&!Sword->ApplyNetworkClovenAttack(Shot))return;
    if(bAzureDragon&&Enchant->Effect(*Item,TEXT("azureDragonClaw"))>0.)
    {
        Shot.AzureDragonPhysicalMultiplier=FMath::Max(1.f,float(Enchant->Effect(*Item,TEXT("azureDragonPhysicalMultiplier"),2.)));
        Shot.AzureDragonMagicDamage=FMath::Max(0.f,ShadowModel->Derived(TEXT("atk")))*FMath::Max(0.f,float(Enchant->Effect(*Item,TEXT("azureDragonMagicAttackScale"),1.)));
    }
    FColdSteelNetHitReport Report;Report.AttackMeta=Shot.AttackMeta;
    const float Damage=ComputeServerDamage(Pawn,Report,Shot,Item,1.f);
    if(Damage<=0.f)return;
    LastRiftSequence=Sequence;LastRiftReleasedAt=Now;
    Sword->SpawnAuthoritySlashWave(FTransform(Direction.Rotation(),Origin),Damage,Flight.RangeCM,Flight.SpeedCM,Shot);
}
