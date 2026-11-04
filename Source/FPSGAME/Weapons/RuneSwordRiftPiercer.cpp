#include "RuneSwordComponent.h"
#include "RiftPiercerThrust.h"
#include "StarfallImpactCameraShake.h"
#include "GunsmithSystem.h"
#include "ModularSwordVisual.h"
#include "MeleeWeaponStats.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/Paths.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"

namespace
{
    bool HasRiftPiercer(const FColdSteelItem* Item,const UColdSteelStatusModel* Model)
    {
        const auto* Gunsmith=Model?Model->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
        return Item&&Gunsmith&&Item->Definition==TEXT("ue_frost_crystal_sword")&&
            Gunsmith->Installed(*Item).FindRef(TEXT("blade_1"))==TEXT("rift_piercer");
    }
}
void URuneSwordComponent::ReleaseRiftPiercer(const FTransform& Aim)
{
    if(!bRiftPiercerSwing||bHeavyAttack||bQuickCombatStrike||bDashAttack||!Character.IsValid())return;
    const auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Item=Model&&!Model->ActiveProductionTool()?Model->Equipped():nullptr;
    if(!HasRiftPiercer(Item,Model)||Item->InstanceId!=InstanceId)return;
    const uint8 Stage=SwingSkills.AttackMeta&0x0F;
    FTransform HiltFrame=Aim;
    if(Stage==3&&bThrustAttack)
    {
        // The release callback precedes the normal substep sampling. Sample the
        // actual contact pose so the imprint begins at this sword's hilt, not the eye.
        SamplePose(ContactStart);
        if(ModularSword&&ModularSword->GetStaticMesh())HiltFrame.SetLocation(ModularSword->GetComponentLocation());
        SpawnRiftPiercer(HiltFrame,*Item,SwingDamage,SwingReach,SwingSkills);
        if(auto* PC=Cast<APlayerController>(Character->GetController());PC&&PC->PlayerCameraManager)
        {
            const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Camera.Shake"));
            const float Scale=Setting?Setting->GetFloat():1.f;
            if(Scale>0)PC->PlayerCameraManager->StartCameraShake(UStarfallImpactCameraShake::StaticClass(),1.6f*Scale);
        }
    }
    if(!Character->HasAuthority())
    {
        if(++RiftPiercerSerial==0)++RiftPiercerSerial;
        ServerRiftPiercerRelease(RiftPiercerSerial,InstanceId,Stage,HiltFrame.GetLocation(),HiltFrame.GetUnitAxis(EAxis::X),SwingSkills.AzureDragonPhysicalMultiplier>1.f);
    }
}
void URuneSwordComponent::ServerRiftPiercerRelease_Implementation(uint32 Serial,const FString& Weapon,uint8 Stage,
    FVector_NetQuantize Origin,FVector_NetQuantizeNormal Direction,bool AzureDragon)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model&&!Model->ActiveProductionTool()?Model->Equipped():nullptr;
    if(!Pawn||!HasRiftPiercer(Item,Model)||Item->InstanceId!=Weapon||!Serial||Stage<1||Stage>3||
        Origin.ContainsNaN()||Direction.ContainsNaN()||Direction.IsNearlyZero())return;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(Pawn->IsCastBlockingLeftHandAction()||FVector::DistSquared(Origin,Pawn->GetPawnViewLocation())>FMath::Square(250.f))return;
    if(int32(Serial-RiftPiercerAcceptedSerial)<=0)return;
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Model);const double Now=GetWorld()->GetTimeSeconds();
    // The reliable channel receives all three committed ordinary releases, including misses.
    // Remote callers cannot submit an isolated stage 3 or duplicate its instant strike.
    if(Weapon!=RiftPiercerAcceptedWeapon||Item->Data!=RiftPiercerAcceptedData||Now-RiftPiercerAcceptedAt>Stats.AttackSeconds+1.2)
        RiftPiercerAcceptedStage=0;
    if(Stage!=1&&Stage!=RiftPiercerAcceptedStage+1)return;
    if(Now-RiftPiercerAcceptedAt<FMath::Max(.04,.55*FMath::Min(Stats.AttackSeconds,Stats.ThrustSeconds)))return;
    RiftPiercerAcceptedSerial=Serial;RiftPiercerAcceptedStage=Stage==3?0:Stage;RiftPiercerAcceptedAt=Now;
    RiftPiercerAcceptedWeapon=Weapon;RiftPiercerAcceptedData=Item->Data;
    if(Stage!=3)return;
    auto Shot=ColdSteelSkills::Snapshot(Pawn,Item,false);Shot.bMelee=true;Shot.bRifle=Shot.bPistol=false;
    Shot.AttackMeta=3;Shot.AttackForm=EMonsterAttackForm::Blade;
    Shot.ToughnessDamageMultiplier*=Stats.Modifiers.ComboThirdToughness;
    if(AzureDragon)if(const auto* Enchant=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();Enchant&&Enchant->Effect(*Item,TEXT("azureDragonClaw"))>0.)
    {
        Shot.AzureDragonPhysicalMultiplier=FMath::Max(1.f,float(Enchant->Effect(*Item,TEXT("azureDragonPhysicalMultiplier"),2.)));
        Shot.AzureDragonMagicDamage=FMath::Max(0.f,Model->Derived(TEXT("atk")))*FMath::Max(0.f,float(Enchant->Effect(*Item,TEXT("azureDragonMagicAttackScale"),1.)));
    }
    SpawnRiftPiercer(FTransform(Direction.Rotation(),Origin),*Item,Stats.ComboThirdDamage,Stats.ThrustReach,Shot);
}
void URuneSwordComponent::SpawnRiftPiercer(const FTransform& Aim,const FColdSteelItem& Item,float ThirdDamage,float ThrustReach,const FColdSteelSkillShot& Snapshot)
{
    auto* Pawn=Cast<APawn>(GetOwner());if(!Pawn)return;
    FRiftPiercerThrustState State;State.HiltFrame=Aim;State.Reach=ThrustReach*4.f;
    State.bOwnerPredicted=!Pawn->IsLocallyControlled();
    State.HitSound=FSoftObjectPath(ColdSteelInventory::Text(Item,TEXT("hit_sound")));
    // Copy only the selected blade. The module recipe is also available on dedicated servers.
    for(const auto& Part:ColdSteelModularSword::DescribeGeometry(Item))if(Part.Slot==TEXT("blade_1"))
    {
        const FString Path=Part.Mesh.Contains(TEXT("."))?Part.Mesh:Part.Mesh+TEXT(".")+FPaths::GetCleanFilename(Part.Mesh);
        State.Blade=FSoftObjectPath(Path);break;
    }
    if(Pawn->IsLocallyControlled()&&ModularSword&&ModularSword->GetStaticMesh())
        State.Blade=FSoftObjectPath(ModularSword->GetStaticMesh());
    if(!State.Blade.IsValid())return;
    if(ColdSteelModularSword::BladeFinishMode(Item)==8)State.Tint=FLinearColor(1.f,.10f,.18f);
    FActorSpawnParameters Params;Params.Owner=Pawn;Params.Instigator=Pawn;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Thrust=GetWorld()->SpawnActor<ARiftPiercerThrust>(Aim.GetLocation(),Aim.Rotator(),Params))
        Thrust->Activate(State,ThirdDamage,Snapshot,!Pawn->HasAuthority());
}
