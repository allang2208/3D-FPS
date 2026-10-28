#include "KukriFrostRavenComponent.h"
#include "../../Combat/CombatStatusFormula.h"
#include "KukriBerserkerVFXComponent.h"
#include "../AzureDragonEnergyComponent.h"
#include "../MeleeWeaponStats.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelItemReadCache.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

UKukriFrostRavenComponent::UKukriFrostRavenComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickInterval=.05f;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
bool UKukriFrostRavenComponent::Installed(const FColdSteelItem& Item)
{
    if(Item.Definition!=TEXT("ue_kukri"))return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Rune;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
        (*Parts)->TryGetStringField(TEXT("blade_2"),Rune)&&Rune==TEXT("frost_raven_rune");
}
void UKukriFrostRavenComponent::Configure(const UColdSteelStatusModel* Model)
{
    Profile=Model;TArray<FString> Next;
    const auto* Main=Model?Model->Equipped():nullptr;
    const auto* Tool=Model?Model->ActiveProductionTool():nullptr;
    const auto* Paired=Main?Model->Equipped(Main->Cell==6?8:11):nullptr;
    // Track the actual ordered loadout, including the non-rune partner. Swapping
    // hands or changing the other weapon must end the shared frost-raven cycle.
    const FString NextKey=FString::Printf(TEXT("%d|%s|%s|%s"),Main?Main->Cell:-1,
        Main?*Main->InstanceId:TEXT(""),Paired?*Paired->InstanceId:TEXT(""),Tool?*Tool->InstanceId:TEXT(""));
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Model&&!Tool&&(!Health||!Health->IsDead()))
    {
        if(Main&&Installed(*Main))Next.Add(Main->InstanceId);
        const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,Model);
        if(Off&&Installed(*Off))Next.Add(Off->InstanceId);
    }
    Next.Sort();
    const bool Changed=bEquipmentConfigured&&(EquippedKey!=NextKey||EquippedInstances!=Next);
    if(Changed)
    {
        // Clear the local display immediately, including when the destination
        // loadout also has a rune. An old replicated state cannot revive a
        // cancelled buff after a quick switch away and back.
        if(!GetOwner()->HasAuthority())
            RequiredEquipmentRevision=FMath::Max(RequiredEquipmentRevision,
                State.EquipmentRevision+uint32(State.EquipmentKey!=NextKey||State.Instances!=Next));
        if(ActiveVFX)ActiveVFX->SetState(false,0.f,0);
        if(Hud)Hud->ClearEnergy();
        ShownCharge=0;ShownActivation=0.;
    }
    EquippedKey=NextKey;EquippedInstances=Next;bEquipmentConfigured=true;
    if(GetOwner()->HasAuthority()&&(State.EquipmentKey!=NextKey||State.Instances!=Next))
    {
        State.EquipmentKey=NextKey;State.Instances=MoveTemp(Next);++State.EquipmentRevision;
        State.Charge=0;State.EndsAt=0.;RecentAttacks.Reset();GetOwner()->ForceNetUpdate();
    }
    SetComponentTickEnabled(!EquippedInstances.IsEmpty());
    Present();
}
double UKukriFrostRavenComponent::Clock() const
{
    const auto* W=GetWorld();const auto* GS=W?W->GetGameState():nullptr;
    return GS?GS->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;
}
bool UKukriFrostRavenComponent::MatchesEquipment() const
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    // Observers have no inventory profile. The VFX resolves the replicated
    // instance IDs against the actual world equipment before drawing anything.
    if(Pawn&&!Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())return !State.Instances.IsEmpty();
    return !EquippedInstances.IsEmpty()&&State.Instances==EquippedInstances&&State.EquipmentKey==EquippedKey&&
        State.EquipmentRevision>=RequiredEquipmentRevision;
}
float UKukriFrostRavenComponent::Remaining() const
{
    const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!MatchesEquipment()||(H&&H->IsDead()))return 0.f;
    return FMath::Max(0.f,float(State.EndsAt-Clock()));
}
bool UKukriFrostRavenComponent::Eligible(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model) const
{
    if(!Shot.bMelee||Shot.bRicochet||Shot.ItemDefinition!=TEXT("ue_kukri"))return false;
    if(EquippedInstances.Contains(Shot.ItemInstance))return true;
    const auto* Main=Model?Model->Equipped():nullptr;
    const auto* Off=Shot.AttackMeta==0x16?ColdSteelMelee::PairedOneHandedWeapon(Main,Model):nullptr;
    return Main&&Off&&Shot.ItemInstance==Main->InstanceId&&EquippedInstances.Contains(Off->InstanceId);
}
float UKukriFrostRavenComponent::ToughnessMultiplier(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model)
{
    const auto* Pawn=Model?Model->RuntimePawn():nullptr;
    const auto* Rune=Pawn?Pawn->FindComponentByClass<UKukriFrostRavenComponent>():nullptr;
    if(!Rune||Rune->Remaining()<=0.f||!Rune->Eligible(Shot,Model))return 1.f;
    // All contacts of the activating swing retain its pre-awakening strength.
    const auto* Contact=Rune->RecentAttacks.FindByPredicate([&](const auto& C){return C.Serial==Shot.MasteryAttackSerial;});
    if(Contact&&!Contact->bAwakened)return 1.f;
    const auto* Main=Model->Equipped();
    const auto* Off=Shot.AttackMeta==0x16?ColdSteelMelee::PairedOneHandedWeapon(Main,Model):nullptr;
    if(Main&&Off&&Shot.ItemInstance==Main->InstanceId)
    {
        const bool Right=Rune->EquippedInstances.Contains(Main->InstanceId),Left=Rune->EquippedInstances.Contains(Off->InstanceId);
        if(Right&&Left)return 1.35f;
        const auto A=ColdSteelMelee::Evaluate(*Main,Model),B=ColdSteelMelee::Evaluate(*Off,Model);
        const double TA=(A.DamageParts.BasePhysical+A.DamageParts.AddedPhysical)*A.Modifiers.MartialDamage*A.Modifiers.ToughnessDamage;
        const double TB=(B.DamageParts.BasePhysical+B.DamageParts.AddedPhysical)*B.Modifiers.MartialDamage*B.Modifiers.ToughnessDamage;
        return 1.f+.35f*float(((Right?TA:0.)+(Left?TB:0.))/FMath::Max(.001,TA+TB));
    }
    return 1.35f;
}
void UKukriFrostRavenComponent::ConfirmHit(const FColdSteelSkillShot& Shot,AActor* Victim,float AppliedDamage)
{
    if(!GetOwner()->HasAuthority()||!Victim||AppliedDamage<=0.f||!Shot.MasteryAttackSerial)return;
    const auto* Model=ColdSteelAuthority::ForPawn(Cast<AFPSGAMECharacter>(GetOwner()));
    Configure(Model);if(!Model||!Eligible(Shot,Model))return;
    auto* Contact=RecentAttacks.FindByPredicate([&](const auto& C){return C.Serial==Shot.MasteryAttackSerial;});
    if(!Contact)
    {
        if(RecentAttacks.Num()>=32)RecentAttacks.RemoveAt(0);
        Contact=&RecentAttacks.AddDefaulted_GetRef();Contact->Serial=Shot.MasteryAttackSerial;
        Contact->bAwakened=Remaining()>0.f;
        if(!Contact->bAwakened)
        {
            if(State.EndsAt>0.){State.EndsAt=0.;State.Charge=0;}
            State.Charge=FMath::Min(8,State.Charge+1);
            if(State.Charge==8)State.EndsAt=Clock()+16.;
            GetOwner()->ForceNetUpdate();Present();
        }
    }
    if(Contact->Victims.Contains(Victim))return;
    Contact->Victims.Add(Victim);
    if(Contact->bAwakened&&Remaining()>0.f)
        if(auto* Combat=Victim->FindComponentByClass<UMonsterCombatComponent>();Combat&&!Combat->IsDead())
            UCombatStatusFormula::GetOrAdd(Victim)->AddChill(4,4.f,true);
}
void UKukriFrostRavenComponent::Present()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||GetNetMode()==NM_DedicatedServer)return;
    const bool Local=Pawn->IsLocallyControlled();
    const auto& Instances=Local?EquippedInstances:State.Instances;
    const bool Enabled=!Instances.IsEmpty();
    if(Enabled&&!ActiveVFX)
    {ActiveVFX=NewObject<UKukriBerserkerVFXComponent>(GetOwner());ActiveVFX->UseFrostRaven();ActiveVFX->RegisterComponent();}
    const float Seconds=Remaining();
    if(ActiveVFX)
    {
        uint8 Hands=0;
        const auto* Model=Profile.Get();const auto* Main=Model?Model->Equipped():nullptr;
        const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,Model);
        if(Main&&EquippedInstances.Contains(Main->InstanceId))Hands|=1;
        if(Off&&EquippedInstances.Contains(Off->InstanceId))Hands|=2;
        ActiveVFX->SetState(Enabled,Seconds,Hands,Instances);
    }
    if(!Local)return; // Gauges remain private to the owning player.
    if(Enabled&&!Hud)
    {
        Hud=NewObject<UAzureDragonEnergyComponent>(GetOwner());
        Hud->ConfigureMaterial(FSoftObjectPath(TEXT("/Game/Weapons/Kukri20261020/FrostRaven20261028/M_FrostRavenEnergyHud.M_FrostRavenEnergyHud")));
        Hud->SetRightAligned(true);
        Hud->RegisterComponent();
    }
    if(!Hud)return;
    Hud->Configure(Enabled);
    const int32 Charge=MatchesEquipment()?State.Charge:0;
    const bool Activated=Seconds>0.f&&ShownActivation!=State.EndsAt;
    Hud->SetEnergy(Seconds>0.f?Seconds/16.f:float(Charge)/8.f,Activated,ShownCharge!=Charge||Activated);
    ShownCharge=Charge;ShownActivation=State.EndsAt;
}
void UKukriFrostRavenComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(GetOwner()->HasAuthority())
    {
        const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
        if(H&&H->IsDead()){Configure(Profile.Get());return;}
        if(State.EndsAt>0.&&State.EndsAt<=Clock())
        {State.EndsAt=0.;State.Charge=0;GetOwner()->ForceNetUpdate();}
    }
    Present();
}
void UKukriFrostRavenComponent::OnRep_State()
{SetComponentTickEnabled(!State.Instances.IsEmpty()||!EquippedInstances.IsEmpty());Present();}
void UKukriFrostRavenComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UKukriFrostRavenComponent,State);}
void UKukriFrostRavenComponent::EndPlay(const EEndPlayReason::Type Reason)
{if(ActiveVFX){ActiveVFX->DestroyComponent();ActiveVFX=nullptr;}if(Hud){Hud->DestroyComponent();Hud=nullptr;}Super::EndPlay(Reason);}
