#include "EagleTalonGuardComponent.h"
#include "GunsmithSystem.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "Net/UnrealNetwork.h"

namespace
{
constexpr uint8 FullCharge=6;
constexpr float IceStrength=4.5f;
bool IsEnemyAttackSource(AActor* Attacker,AActor* Defender)
{
    if(!IsValid(Attacker)||Attacker==Defender||Attacker->ActorHasTag(TEXT("Friendly"))
        ||Attacker->ActorHasTag(TEXT("Companion"))||Attacker->ActorHasTag(TEXT("Player"))
        ||RangedAttackQuery::IsFriendlyUnit(Defender,Attacker))return false;
    // A projectile can arrive after its monster has died. Its guard result still counts.
    return Attacker->ActorHasTag(TEXT("Enemy"))||Attacker->FindComponentByClass<UMonsterCombatComponent>()!=nullptr;
}
}
bool UEagleTalonGuardComponent::IsEagleMesh(const UStaticMeshComponent* Part)
{
    static const FName Regular(TEXT("SM_ForgedSteelGreatsword_EagleTalonGuard"));
    static const FName Wide(TEXT("SM_ForgedSteelGreatsword_EagleTalonGuard_ExecutionerSeat"));
    const UStaticMesh* Mesh=Part?Part->GetStaticMesh():nullptr;
    return Mesh&&(Mesh->GetFName()==Regular||Mesh->GetFName()==Wide);
}

uint64 UEagleTalonGuardComponent::AttackKey(EEagleStrike Kind,uint32 Serial)
{
    return Serial ? ((uint64(Kind)+1)<<32)|Serial : 0;
}

UEagleTalonGuardComponent::UEagleTalonGuardComponent(){SetIsReplicatedByDefault(true);}
void UEagleTalonGuardComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UEagleTalonGuardComponent,Charge);
}
bool UEagleTalonGuardComponent::Installed(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile)
{
    if(!Item||Item->Definition!=TEXT("ue_forged_steel_greatsword")||!Profile||Profile->ActiveProductionTool())return false;
    const auto* Smith=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    return Smith&&Smith->Installed(*Item).FindRef(TEXT("guard"))==TEXT("eagle_talon_guard");
}
void UEagleTalonGuardComponent::Equip(const UColdSteelStatusModel* Profile)
{
    if(!GetOwner()->HasAuthority())return;
    const FColdSteelItem* Item=Profile?Profile->Equipped():nullptr;
    const FString Equipped=Installed(Item,Profile)?Item->InstanceId:FString();
    if(Equipped==Charge.Weapon)return;
    Charge.Weapon=Equipped;
    ClearCharge();
}
void UEagleTalonGuardComponent::ClearCharge()
{
    if(!GetOwner()->HasAuthority())return;
    Charge.Blocks=0;
    EmpoweredReceipts.Reset();
    Present();
    GetOwner()->ForceNetUpdate();
}
bool UEagleTalonGuardComponent::Ready(const UColdSteelStatusModel* Profile,const FColdSteelItem* Item)
{
    if(!Item||Item->Definition!=TEXT("ue_forged_steel_greatsword")||!Profile||Profile->ActiveProductionTool())return false;
    const auto* Pawn=Profile->RuntimePawn();
    const auto* Guard=Pawn?Pawn->FindComponentByClass<UEagleTalonGuardComponent>():nullptr;
    return Guard&&Guard->Charge.Blocks==FullCharge&&Guard->Charge.Weapon==Item->InstanceId&&Installed(Item,Profile);
}
bool UEagleTalonGuardComponent::Ready(const UColdSteelStatusModel* Profile)
{
    return Profile&&Ready(Profile,Profile->Equipped());
}
void UEagleTalonGuardComponent::Defended(const FString& Weapon,AActor* Attacker,bool Parried)
{
    if(!GetOwner()->HasAuthority()||Charge.Weapon.IsEmpty()||Charge.Weapon!=Weapon||Charge.Blocks>=FullCharge
        ||!IsEnemyAttackSource(Attacker,GetOwner()))return;
    Charge.Blocks=FMath::Min<int32>(FullCharge,Charge.Blocks+(Parried?2:1));
    if(Charge.Blocks==FullCharge)Present();
    GetOwner()->ForceNetUpdate();
}
bool UEagleTalonGuardComponent::Commit(AActor* Owner,const FString& Weapon,EEagleStrike Kind,uint32 Serial)
{
    if(!Owner||!Owner->HasAuthority())return false;
    auto* Guard=Owner->FindComponentByClass<UEagleTalonGuardComponent>();
    if(!Guard||Guard->Charge.Blocks!=FullCharge||Guard->Charge.Weapon!=Weapon)return false;
    Guard->Charge.Blocks=0;
    if(Serial)
    {
        // Each incoming hit must still pass the normal server attack receipt and target window.
        if(Guard->EmpoweredReceipts.Num()==16)Guard->EmpoweredReceipts.RemoveAt(0);
        Guard->EmpoweredReceipts.Add(AttackKey(Kind,Serial));
    }
    Guard->Present();
    Owner->ForceNetUpdate();
    return true;
}
bool UEagleTalonGuardComponent::WasEmpowered(const AActor* Owner,const FString& Weapon,EEagleStrike Kind,uint32 Serial)
{
    const auto* Guard=Owner&&Serial?Owner->FindComponentByClass<UEagleTalonGuardComponent>():nullptr;
    return Guard&&Guard->Charge.Weapon==Weapon&&Guard->EmpoweredReceipts.Contains(AttackKey(Kind,Serial));
}
bool UEagleTalonGuardComponent::ReportEmpowered(const AActor* Owner,const FColdSteelNetHitReport& R)
{
    const auto* Guard=Owner?Owner->FindComponentByClass<UEagleTalonGuardComponent>():nullptr;
    return Guard&&Guard->Charge.Weapon==R.ItemInstance&&Guard->EmpoweredReceipts.Contains(ReportAttackKey(R));
}

uint64 UEagleTalonGuardComponent::ReportAttackKey(const FColdSteelNetHitReport& R)
{
    if(R.ItemDefinition!=TEXT("ue_forged_steel_greatsword"))return 0;
    if(R.AttackMeta&0x80)return AttackKey(EEagleStrike::Quick,R.QuickCombatSerial);
    if(R.AttackMeta&0x20)return AttackKey(EEagleStrike::Whirlwind,R.WhirlwindSerial);
    if(R.AttackMeta==SwordUppercut::AttackMeta)return AttackKey(EEagleStrike::Uppercut,R.UppercutSerial);
    if(R.AttackMeta==0x10)return AttackKey(EEagleStrike::Heavy,R.GuardAttackSerial);
    if(R.AttackMeta==0x16||(R.AttackMeta>=1&&R.AttackMeta<=3))return AttackKey(EEagleStrike::Ordinary,R.GenericMeleeSerial);
    return 0;
}
void UEagleTalonGuardComponent::BindGuard(UStaticMeshComponent* Part)
{
    if(!Part||!Part->GetOwner()||Part->GetOwner()->GetNetMode()==NM_DedicatedServer)return;
    if(auto* Guard=Part->GetOwner()->FindComponentByClass<UEagleTalonGuardComponent>())
    {
        if(!IsEagleMesh(Part))
        {
            if(Guard->Guards.Remove(Part)>0)Part->SetCustomPrimitiveDataFloat(0,0.f);
            return;
        }
        Guard->Guards.RemoveAll([](const auto& Weak){return !Weak.IsValid();});
        Guard->Guards.AddUnique(Part);
        Part->SetCustomPrimitiveDataFloat(0,Guard->Charge.Blocks==FullCharge?IceStrength:0.f);
    }
}
void UEagleTalonGuardComponent::Present()
{
    for(int32 i=Guards.Num()-1;i>=0;--i)
    {
        if(auto* Part=Guards[i].Get();IsEagleMesh(Part))
            Part->SetCustomPrimitiveDataFloat(0,Charge.Blocks==FullCharge?IceStrength:0.f);
        else Guards.RemoveAtSwap(i);
    }
}
