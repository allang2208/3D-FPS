#include "KukriRelentlessComponent.h"
#include "../../UI/StatusEffectsComponent.h"
#include "../SwordTasselMeshComponent.h"
#include "../MeleeWeaponStats.h"
#include "../../FPSGAMECharacter.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "Components/PointLightComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Net/UnrealNetwork.h"

UKukriRelentlessComponent::UKukriRelentlessComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
bool UKukriRelentlessComponent::Installed(const FColdSteelItem& Item,const UColdSteelStatusModel* Model)
{
    const auto* GI=Model?Model->GetGameInstance():nullptr;
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    return Item.Definition==TEXT("ue_kukri")&&Gunsmith&&
        Gunsmith->Installed(Item).FindRef(TEXT("lanyard"))==TEXT("kukri_lanyard_relentless");
}
double UKukriRelentlessComponent::Clock() const
{
    const auto* W=GetWorld();const auto* GS=W?W->GetGameState():nullptr;
    return GS?GS->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;
}
void UKukriRelentlessComponent::Configure(const UColdSteelStatusModel* Model)
{
    Profile=Model;TArray<FString> Next;
    const auto* Main=Model?Model->ActiveKukriWeapon():nullptr;
    const auto* Tool=Model?Model->ActiveProductionTool():nullptr;
    const auto* Pair=Main&&Main==Model->Equipped()?Model->Equipped(Main->Cell==6?8:11):nullptr;
    const FString Key=FString::Printf(TEXT("%d|%s|%s|%s"),Main?Main->Cell:-1,
        Main?*Main->InstanceId:TEXT(""),Pair?*Pair->InstanceId:TEXT(""),Tool?*Tool->InstanceId:TEXT(""));
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Model&&!Tool&&(!Health||!Health->IsDead()))
    {
        if(Main&&Installed(*Main,Model))Next.Add(Main->InstanceId);
        const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,Model);
        if(Off&&Installed(*Off,Model))Next.Add(Off->InstanceId);
    }
    if(bConfigured&&(Next!=Equipped||Key!=EquipmentKey))
    {
        TArray<FString> Replicated;for(const auto& Blade:State.Blades)Replicated.Add(Blade.Instance);
        if(!GetOwner()->HasAuthority())RequiredRevision=FMath::Max(RequiredRevision,
            State.Revision+uint32(State.EquipmentKey!=Key||Replicated!=Next));
        Attacks.Reset();for(auto& Attack:Pending)Attack={};ResolveAge=0.f;
    }
    Equipped=Next;EquipmentKey=Key;bConfigured=true;
    TArray<FString> Previous;for(const auto& Blade:State.Blades)Previous.Add(Blade.Instance);
    if(GetOwner()->HasAuthority()&&(Previous!=Next||State.EquipmentKey!=Key))
    {
        State.Blades.Reset();State.EquipmentKey=Key;++State.Revision;
        for(const auto& Instance:Next){FKukriRelentlessBlade Blade;Blade.Instance=Instance;State.Blades.Add(Blade);}
        GetOwner()->ForceNetUpdate();UStatusEffectsComponent::Notify(GetOwner());
    }
    SetComponentTickEnabled(!Equipped.IsEmpty());Present();
}
int32 UKukriRelentlessComponent::Stacks(const FString& Instance) const
{
    const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(H&&H->IsDead())return 0;
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(Pawn&&(Pawn->HasAuthority()||Pawn->IsLocallyControlled())&&
        (!Equipped.Contains(Instance)||State.EquipmentKey!=EquipmentKey||State.Revision<RequiredRevision))return 0;
    const auto* Blade=State.Blades.FindByPredicate([&](const auto& B){return B.Instance==Instance;});
    return Blade?FMath::Max(0,Blade->Stacks-FMath::FloorToInt(FMath::Max(0.,Clock()-Blade->LastHit-4.)/.5)):0;
}
UKukriRelentlessComponent::FAttackSnapshot UKukriRelentlessComponent::Freeze(const UColdSteelStatusModel* Model) const
{
    FAttackSnapshot Result;Result.EquipmentKey=EquipmentKey;
    const auto* Main=Model?Model->ActiveKukriWeapon():nullptr;
    const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,Model);
    for(const auto* Item:{Main,Off})if(Item&&Item->Definition==TEXT("ue_kukri"))
    {
        const auto Stats=ColdSteelMelee::Evaluate(*Item,Model);
        FBladeSnapshot Blade;Blade.Instance=Item->InstanceId;Blade.Stacks=Stacks(Blade.Instance);
        Blade.bPendant=Equipped.Contains(Blade.Instance);
        Blade.DamageWeight=Stats.DamageParts.Total()*Stats.Modifiers.MartialDamage;
        Blade.ToughnessWeight=(Stats.DamageParts.BasePhysical+Stats.DamageParts.AddedPhysical)*
            Stats.Modifiers.MartialDamage*Stats.Modifiers.ToughnessDamage;
        Result.Blades.Add(Blade);
    }
    return Result;
}
bool UKukriRelentlessComponent::GetBuff(bool bOffhand,int32& Count,float& Remaining,float& Duration) const
{
    Count=0;Remaining=Duration=0.f;
    const auto* Main=Profile.IsValid()?Profile->ActiveKukriWeapon():nullptr;
    if(!Main)return false;
    // A lone off-hand blade (main hand empty) is held and shown in the left hand: its buff is the off-hand's.
    const bool bLone=Main!=Profile->Equipped();
    for(const auto& Instance:Equipped)
    {
        if((bLone||Instance!=Main->InstanceId)!=bOffhand)continue;
        Count=Stacks(Instance);if(Count<=0)return false;
        const auto* Blade=State.Blades.FindByPredicate([&](const auto& B){return B.Instance==Instance;});
        if(!Blade)return false;
        const double Age=FMath::Max(0.,Clock()-Blade->LastHit);
        const int32 Decayed=FMath::FloorToInt(FMath::Max(0.,Age-4.)/.5);
        Remaining=float(FMath::Max(0.,4.+.5*(Decayed+1)-Age));Duration=Decayed==0?4.5f:.5f;
        return true;
    }
    return false;
}
void UKukriRelentlessComponent::Store(FAttackSnapshot Attack)
{
    if(auto* Existing=Attacks.FindByPredicate([&](const auto& A){return A.Serial==Attack.Serial;}))*Existing=MoveTemp(Attack);
    else {if(Attacks.Num()>=64)Attacks.RemoveAt(0);Attacks.Add(MoveTemp(Attack));}
}
void UKukriRelentlessComponent::CaptureAttack(uint32 Serial,const UColdSteelStatusModel* Model)
{
    Configure(Model);
    // Remote hit reports rebuild ordinary shot data at contact time. Their
    // accepted action-start snapshot is bound by the authority receipt instead.
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(Pawn&&Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()&&GetNetMode()!=NM_Standalone)return;
    if(!Serial||Equipped.IsEmpty()||Attacks.ContainsByPredicate([&](const auto& A){return A.Serial==Serial;}))return;
    auto Attack=Freeze(Model);Attack.Serial=Serial;Store(MoveTemp(Attack));
}
void UKukriRelentlessComponent::PrepareServerAttack(int32 Family)
{
    if(!GetOwner()->HasAuthority()||Family<0||Family>=5)return;
    const auto* Model=ColdSteelAuthority::ForPawn(Cast<AFPSGAMECharacter>(GetOwner()));
    Configure(Model);Pending[Family]=Freeze(Model);
}
void UKukriRelentlessComponent::BindServerAttack(int32 Family,uint32 Serial)
{
    if(Family<0||Family>=5||!Serial||Pending[Family].EquipmentKey!=EquipmentKey)return;
    auto Attack=Pending[Family];Attack.Serial=Serial;Store(MoveTemp(Attack));
}
FVector2D UKukriRelentlessComponent::Multipliers(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model)
{
    if(!Shot.bMelee||Shot.bRicochet||(Shot.AttackMeta&0x40)||Shot.ItemDefinition!=TEXT("ue_kukri"))return FVector2D(1,1);
    const auto* Pawn=Model?Model->RuntimePawn():nullptr;
    const auto* Self=Pawn?Pawn->FindComponentByClass<UKukriRelentlessComponent>():nullptr;
    const auto* Attack=Self?Self->Attacks.FindByPredicate([&](const auto& A){return A.Serial==Shot.MasteryAttackSerial;}):nullptr;
    if(!Attack||Attack->EquipmentKey!=Self->EquipmentKey)return FVector2D(1,1);
    double D=0,T=0,DW=0,TW=0;
    for(const auto& Blade:Attack->Blades)
    {
        if(Shot.AttackMeta!=0x16&&Blade.Instance!=Shot.ItemInstance)continue;
        const int32 Count=Blade.bPendant&&Self->Equipped.Contains(Blade.Instance)?Blade.Stacks:0;
        D+=Blade.DamageWeight*(1.+DamagePerStack*Count);DW+=Blade.DamageWeight;
        T+=Blade.ToughnessWeight*(1.+ToughnessPerStack*Count);TW+=Blade.ToughnessWeight;
    }
    return FVector2D(DW>0?D/DW:1.,TW>0?T/TW:1.);
}
void UKukriRelentlessComponent::ConfirmHit(const FColdSteelSkillShot& Shot,float Damage)
{
    if(!GetOwner()->HasAuthority()||!Shot.bMelee||Shot.bRicochet||(Shot.AttackMeta&0x40)||Damage<=0.f)return;
    auto* Attack=Attacks.FindByPredicate([&](const auto& A){return A.Serial==Shot.MasteryAttackSerial;});
    if(!Attack||Attack->EquipmentKey!=EquipmentKey)return;
    bool Changed=false;
    for(auto& Blade:Attack->Blades)
    {
        if(!Blade.bPendant||Blade.bGranted||!Equipped.Contains(Blade.Instance)||
            (Shot.AttackMeta!=0x16&&Blade.Instance!=Shot.ItemInstance))continue;
        if(auto* Current=State.Blades.FindByPredicate([&](const auto& B){return B.Instance==Blade.Instance;}))
        {
            const int32 Count=Stacks(Blade.Instance);Current->Stacks=FMath::Min(MaximumStacks,Count+1);Current->LastHit=Clock();
            Blade.bGranted=true;Changed=true;
        }
    }
    if(Changed){GetOwner()->ForceNetUpdate();UStatusEffectsComponent::Notify(GetOwner());Present();}
}
void UKukriRelentlessComponent::ResolveVisuals()
{
    for(auto& V:Visuals)if(auto* Mesh=V.Mesh.Get())
    {
        RemoveTickPrerequisiteComponent(Mesh);
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)if(auto* M=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(I)))
            M->SetScalarParameterValue(TEXT("RelentlessStacks"),0.f);
    }
    Visuals.Reset();
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body)return;
    TArray<FFPSWeatherWeaponMesh> Meshes,WorldMeshes;Body->GetWeatherWeaponMeshes(Meshes,false);Body->GetWeatherWeaponMeshes(WorldMeshes,true);
    for(const auto& Entry:Meshes)
        if(auto* Mesh=Cast<USwordTasselMeshComponent>(Entry.Mesh);Mesh&&Mesh->GetStaticMesh()&&
            Mesh->GetStaticMesh()->GetFName()==TEXT("SM_Kukri_RelentlessPendant"))
        {
            const bool World=WorldMeshes.ContainsByPredicate([Mesh](const auto& W){return W.Mesh==Mesh;});
            Visuals.Add({Mesh,Entry.Instance,World});AddTickPrerequisiteComponent(Mesh);
        }
}
void UKukriRelentlessComponent::Present()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const auto* Pawn=Cast<APawn>(GetOwner());
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool World=Pawn&&(!Pawn->IsLocallyControlled()||(Body&&Body->IsThirdPersonViewEnabled()));
    int32 LightIndex=0;TArray<FString,TInlineAllocator<2>> Lit;
    for(auto& V:Visuals)if(auto* Mesh=V.Mesh.Get())
    {
        const int32 Count=Stacks(V.Instance);
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)if(auto* M=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(I)))
            M->SetScalarParameterValue(TEXT("RelentlessStacks"),Count);
        if(Count!=10||V.bWorld!=World||!Mesh->IsVisible()||Mesh->bHiddenInGame||GetOwner()->IsHidden()||Lit.Contains(V.Instance)||LightIndex>=2)continue;
        if(!Lights.IsValidIndex(LightIndex))
        {
            auto* Light=NewObject<UPointLightComponent>(GetOwner());Light->SetupAttachment(GetOwner()->GetRootComponent());
            Light->SetMobility(EComponentMobility::Movable);Light->SetCastShadows(false);
            Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(18.f);
            Light->SetLightColor(FLinearColor(1.f,.63f,.16f));Light->SetAttenuationRadius(75.f);
            Light->SetIndirectLightingIntensity(0.f);Light->SetVolumetricScatteringIntensity(0.f);
            Light->MaxDrawDistance=500.f;Light->MaxDistanceFadeRange=100.f;Light->RegisterComponent();Lights.Add(Light);
        }
        auto* Light=Lights[LightIndex++].Get();Light->SetWorldLocation(Mesh->DeformedPoint(FVector(2.76604,-.20,-6.5),5));
        Light->SetVisibility(true);Lit.Add(V.Instance);
    }
    for(int32 I=LightIndex;I<Lights.Num();++I)Lights[I]->SetVisibility(false);
}
void UKukriRelentlessComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(GetOwner()->HasAuthority())
        if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())
        {Configure(Profile.Get());return;}
    if(GetNetMode()!=NM_DedicatedServer)
    {ResolveAge-=Delta;if(ResolveAge<=0.f){ResolveVisuals();ResolveAge=.2f;}Present();}
}
void UKukriRelentlessComponent::OnRep_State()
{ResolveAge=0.f;SetComponentTickEnabled(!State.Blades.IsEmpty()||!Equipped.IsEmpty());UStatusEffectsComponent::Notify(GetOwner());Present();}
void UKukriRelentlessComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UKukriRelentlessComponent,State);}
void UKukriRelentlessComponent::EndPlay(const EEndPlayReason::Type Reason)
{for(const auto& Light:Lights)if(Light)Light->DestroyComponent();Lights.Reset();Super::EndPlay(Reason);}
