#include "HatchetCharmComponent.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../SwordTasselMeshComponent.h"
#include "../MeleeWeaponStats.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

UHatchetCharmComponent::UHatchetCharmComponent()
{
    SetIsReplicatedByDefault(true);
    static ConstructorHelpers::FObjectFinder<USoundBase> Metal(TEXT("/Game/Weapons/TacticalHatchet20261101/ExclusivePendants/S_Hatchet_EmberClink"));
    static ConstructorHelpers::FObjectFinder<USoundBase> Air(TEXT("/Game/Weapons/TacticalHatchet20261101/ExclusivePendants/S_Hatchet_RavenChirp"));
    Clink=Metal.Object;Chirp=Air.Object;
    Attenuation=CreateDefaultSubobject<USoundAttenuation>(TEXT("CharmAttenuation"));
    Attenuation->Attenuation.bAttenuate=true;
    Attenuation->Attenuation.AttenuationShapeExtents=FVector(120.f,0,0);
    Attenuation->Attenuation.FalloffDistance=1000.f;
}
void UHatchetCharmComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UHatchetCharmComponent,Step,COND_OwnerOnly);
}
double UHatchetCharmComponent::Clock() const
{
    const auto* World=GetWorld();
    const auto* GS=World?World->GetGameState():nullptr;
    return GS?GS->GetServerWorldTimeSeconds():World?World->GetTimeSeconds():0.;
}
void UHatchetCharmComponent::Configure(const UColdSteelStatusModel* Model)
{
    TArray<FString> Steel,Wind;
    const auto* Main=Model&&!Model->ActiveProductionTool()?Model->ActiveKukriWeapon():nullptr;
    const auto* Other=ColdSteelMelee::PairedOneHandedWeapon(Main,Model);
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Model&&(!Health||!Health->IsDead()))
    {
        const auto* Guns=Model->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        for(const auto* Item:{Main,Other})
        {
            if(!Guns||!Item||Item->Definition!=TEXT("ue_tactical_hatchet"))continue;
            const FString Lanyard=Guns->Installed(*Item).FindRef(TEXT("lanyard"));
            if(Lanyard==TEXT("hatchet_lanyard_ember_wedge"))Steel.Add(Item->InstanceId);
            if(Lanyard==TEXT("hatchet_lanyard_raven_whistle"))Wind.Add(Item->InstanceId);
        }
    }
    Wedges=MoveTemp(Steel);Whistles=MoveTemp(Wind);
    if(!DodgeSource.IsEmpty()&&!Whistles.Contains(DodgeSource))DodgeSource.Reset();
    if(GetOwner()->HasAuthority()&&!Step.Source.IsEmpty()&&!Whistles.Contains(Step.Source))
    {
        Step={};GetOwner()->ForceNetUpdate();
    }
}
bool UHatchetCharmComponent::CanWedge(const FColdSteelSkillShot& S,AActor* Target) const
{
    if(!S.bEmberWedge||S.AttackMeta!=0x10||!S.MasteryAttackSerial||!Wedges.Contains(S.ItemInstance))return false;
    const auto* Contact=HeavyContacts.FindByPredicate([&](const auto& C){return C.Serial==S.MasteryAttackSerial&&C.Hand==S.ItemInstance;});
    return !Contact||!Contact->Targets.Contains(Target);
}
void UHatchetCharmComponent::Confirm(const FColdSteelSkillShot& S,AActor* Target,bool Wedge,bool Broke,UColdSteelStatusModel* Model)
{
    if(!GetOwner()->HasAuthority())return;
    if(Wedge)
    {
        auto* Contact=HeavyContacts.FindByPredicate([&](const auto& C){return C.Serial==S.MasteryAttackSerial&&C.Hand==S.ItemInstance;});
        if(!Contact)
        {
            if(HeavyContacts.Num()>=8)HeavyContacts.RemoveAt(0);
            Contact=&HeavyContacts.AddDefaulted_GetRef();Contact->Serial=S.MasteryAttackSerial;Contact->Hand=S.ItemInstance;
        }
        Contact->Targets.Add(Target);
        if(Broke&&Clock()>=NextRefund)
        {
            NextRefund=Clock()+4.;Model->RestoreCombatStamina(6.f);
        }
        if(Broke&&LastBreakCueSerial!=S.MasteryAttackSerial)
        {
            LastBreakCueSerial=S.MasteryAttackSerial;
            MulticastCharmCue(true,S.ItemInstance);
        }
    }
    if(S.bRavenWhistle&&S.AttackMeta<=3&&S.MasteryAttackSerial&&Whistles.Contains(S.ItemInstance)&&Clock()>=NextWhistle)
    {
        const double Now=Clock();NextWhistle=Now+4.;Step.Source=S.ItemInstance;Step.ReadyUntil=Now+3.;
        GetOwner()->ForceNetUpdate();
    }
}
bool UHatchetCharmComponent::HasLiveStep() const
{
    if(Step.Source.IsEmpty()||!Whistles.Contains(Step.Source))return false;
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    return !Health||!Health->IsDead();
}
bool UHatchetCharmComponent::StepReady() const
{
    return Step.ReadyUntil>0.&&Step.ReadyUntil!=PredictedSpent&&Step.ReadyUntil>Clock()&&HasLiveStep();
}
float UHatchetCharmComponent::MoveScale() const
{
    return Step.SpeedUntil>0.&&Step.SpeedUntil>Clock()&&HasLiveStep()?1.12f:1.f;
}
void UHatchetCharmComponent::SpendStep()
{
    if(!StepReady())return;
    if(GetOwner()->HasAuthority())
    {
        DodgeSource=Step.Source;Step.ReadyUntil=0.;GetOwner()->ForceNetUpdate();
        MulticastCharmCue(false,DodgeSource);
    }
    else PredictedSpent=Step.ReadyUntil;
}
void UHatchetCharmComponent::FinishDodge(bool Completed)
{
    if(Completed&&GetOwner()->HasAuthority()&&!DodgeSource.IsEmpty()&&Whistles.Contains(DodgeSource))
    {
        Step.Source=DodgeSource;Step.SpeedUntil=Clock()+1.5;GetOwner()->ForceNetUpdate();
    }
    DodgeSource.Reset();
}
void UHatchetCharmComponent::RejectDodge(){PredictedSpent=-1.;}
void UHatchetCharmComponent::MulticastCharmCue_Implementation(bool Wedge,const FString& Instance)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    USoundBase* Sound=Wedge?Clink.Get():Chirp.Get();
    if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound,GetOwner()->GetActorLocation(),.66f,1.f,0.f,Attenuation);
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Wedge||!Body)return;
    TArray<FFPSWeatherWeaponMesh> Meshes;Body->GetWeatherWeaponMeshes(Meshes);
    for(const auto& Entry:Meshes)if(Entry.Instance==Instance)
        if(auto* Mesh=Cast<USwordTasselMeshComponent>(Entry.Mesh);Mesh&&Mesh->GetStaticMesh()&&Mesh->GetStaticMesh()->GetFName()==TEXT("SM_Hatchet_EmberWedge"))
            if(auto* Mat=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)))
                Mat->SetScalarParameterValue(TEXT("EmberFlashAt"),GetWorld()->GetTimeSeconds());
}
