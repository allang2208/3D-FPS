#include "KukriBerserkerComponent.h"
#include "KukriBerserkerVFXComponent.h"
#include "../AzureDragonEnergyComponent.h"
#include "../MeleeWeaponStats.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelItemReadCache.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

UKukriBerserkerComponent::UKukriBerserkerComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickInterval=.05f;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
bool UKukriBerserkerComponent::Installed(const FColdSteelItem& Item)
{
    if(Item.Definition!=TEXT("ue_kukri"))return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Rune;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
        (*Parts)->TryGetStringField(TEXT("blade_2"),Rune)&&Rune==TEXT("berserker_rune");
}
void UKukriBerserkerComponent::Configure(const UColdSteelStatusModel* Model)
{
    Profile=Model;TArray<FString> Next;
    const auto* Main=Model?Model->Equipped():nullptr;
    const auto* Tool=Model?Model->ActiveProductionTool():nullptr;
    const auto* Paired=Main?Model->Equipped(Main->Cell==6?8:11):nullptr;
    // Track the actual ordered loadout, including the non-rune partner. Swapping
    // hands or changing the other weapon must end the shared berserker cycle.
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
double UKukriBerserkerComponent::Clock() const
{
    const auto* W=GetWorld();const auto* GS=W?W->GetGameState():nullptr;
    return GS?GS->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;
}
bool UKukriBerserkerComponent::MatchesEquipment() const
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    // Observers resolve replicated instances against their world weapon meshes.
    if(Pawn&&!Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())return !State.Instances.IsEmpty();
    return !EquippedInstances.IsEmpty()&&State.Instances==EquippedInstances&&State.EquipmentKey==EquippedKey&&
        State.EquipmentRevision>=RequiredEquipmentRevision;
}
float UKukriBerserkerComponent::Remaining() const
{
    const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!MatchesEquipment()||(H&&H->IsDead()))return 0.f;
    return FMath::Max(0.f,float(State.EndsAt-Clock()));
}
bool UKukriBerserkerComponent::Active(const FColdSteelItem* Item,const UColdSteelStatusModel* Model)
{
    const auto* Pawn=Model?Model->RuntimePawn():nullptr;
    const auto* Rune=Pawn?Pawn->FindComponentByClass<UKukriBerserkerComponent>():nullptr;
    return Item&&Rune&&Rune->Remaining()>0.f&&Rune->EquippedInstances.Contains(Item->InstanceId);
}
float UKukriBerserkerComponent::CostMultiplier(const FColdSteelItem* Item,const UColdSteelStatusModel* Model)
{return Active(Item,Model)?0.f:1.f;}
float UKukriBerserkerComponent::DamageMultiplier(const FColdSteelItem* Item,const UColdSteelStatusModel* Model)
{return Active(Item,Model)?1.25f:1.f;}
float UKukriBerserkerComponent::MovementMultiplier(const AActor* Actor)
{
    const auto* Rune=Actor?Actor->FindComponentByClass<UKukriBerserkerComponent>():nullptr;
    return Rune&&Rune->Remaining()>0.f?1.15f:1.f;
}
void UKukriBerserkerComponent::ConfirmHit(const FColdSteelSkillShot& Shot,float AppliedDamage)
{
    if(!GetOwner()->HasAuthority()||!Shot.bMelee||Shot.bRicochet||AppliedDamage<=0.f||!Shot.MasteryAttackSerial)return;
    const auto* Model=ColdSteelAuthority::ForPawn(Cast<AFPSGAMECharacter>(GetOwner()));
    Configure(Model);if(!Model||State.Instances.IsEmpty())return;
    bool Eligible=State.Instances.Contains(Shot.ItemInstance);
    float LeechShare=Eligible?1.f:0.f;
    // The sprint chop is one combined physical receipt; only rune-bearing blades
    // earn charge, and only their contribution can heal when one knife has the rune.
    const auto* Main=Model->Equipped();
    const auto* Off=Shot.AttackMeta==0x16?ColdSteelMelee::PairedOneHandedWeapon(Main,Model):nullptr;
    if(Main&&Off&&Shot.ItemInstance==Main->InstanceId)
    {
        const bool Right=State.Instances.Contains(Main->InstanceId),Left=State.Instances.Contains(Off->InstanceId);
        Eligible=Right||Left;
        if(Right&&Left)LeechShare=1.f;
        else if(Eligible)
        {
            const auto A=ColdSteelMelee::Evaluate(*Main,Model),B=ColdSteelMelee::Evaluate(*Off,Model);
            const double DA=(A.DamageParts.BasePhysical+A.DamageParts.AddedPhysical)*A.Modifiers.MartialDamage;
            const double DB=(B.DamageParts.BasePhysical+B.DamageParts.AddedPhysical)*B.Modifiers.MartialDamage;
            LeechShare=float((Right?DA:DB)/FMath::Max(.001,DA+DB));
        }
    }
    if(!Eligible)return;
    if(Remaining()>0.f)
        if(auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&!H->IsDead())
        {H->Health=FMath::Min(H->MaxHealth,H->Health+AppliedDamage*.10f*LeechShare);GetOwner()->ForceNetUpdate();}
    if(RecentAttacks.Contains(Shot.MasteryAttackSerial))return;
    if(RecentAttacks.Num()>=32)RecentAttacks.RemoveAt(0);
    RecentAttacks.Add(Shot.MasteryAttackSerial);
    if(Remaining()>0.f)return; // Active attacks neither extend nor precharge the next cycle.
    if(State.EndsAt>0.){State.EndsAt=0.;State.Charge=0;}
    State.Charge=FMath::Min(12,State.Charge+1);
    if(State.Charge==12)State.EndsAt=Clock()+20.;
    GetOwner()->ForceNetUpdate();Present();
}
void UKukriBerserkerComponent::Present()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||GetNetMode()==NM_DedicatedServer)return;
    const bool Local=Pawn->IsLocallyControlled();
    const auto& Instances=Local?EquippedInstances:State.Instances;
    const bool Enabled=!Instances.IsEmpty();
    if(Enabled&&!ActiveVFX)
    {ActiveVFX=NewObject<UKukriBerserkerVFXComponent>(GetOwner());ActiveVFX->RegisterComponent();}
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
    if(!Local)return; // Only the wielder receives a gauge and screen-edge effect.
    if(Enabled&&!Hud)
    {
        Hud=NewObject<UAzureDragonEnergyComponent>(GetOwner());
        Hud->ConfigureMaterial(FSoftObjectPath(TEXT("/Game/Weapons/Kukri20261020/Berserker20261028/M_BerserkerEnergyHud.M_BerserkerEnergyHud")));
        Hud->RegisterComponent();
    }
    if(!Hud)return;
    Hud->Configure(Enabled);
    const int32 Charge=MatchesEquipment()?State.Charge:0;
    const bool Activated=Seconds>0.f&&ShownActivation!=State.EndsAt;
    Hud->SetEnergy(Seconds>0.f?Seconds/20.f:float(Charge)/12.f,Activated,ShownCharge!=Charge||Activated);
    ShownCharge=Charge;ShownActivation=State.EndsAt;
}
void UKukriBerserkerComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
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
void UKukriBerserkerComponent::OnRep_State()
{SetComponentTickEnabled(!State.Instances.IsEmpty()||!EquippedInstances.IsEmpty());Present();}
void UKukriBerserkerComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UKukriBerserkerComponent,State);}
void UKukriBerserkerComponent::EndPlay(const EEndPlayReason::Type Reason)
{if(ActiveVFX){ActiveVFX->DestroyComponent();ActiveVFX=nullptr;}if(Hud){Hud->DestroyComponent();Hud=nullptr;}Super::EndPlay(Reason);}
