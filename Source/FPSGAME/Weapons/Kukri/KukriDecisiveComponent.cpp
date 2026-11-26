#include "KukriDecisiveComponent.h"
#include "KukriRelentlessComponent.h"
#include "KukriWeaponComponent.h"
#include "OffhandKukriComponent.h"
#include "../SwordTasselMeshComponent.h"
#include "../MeleeWeaponStats.h"
#include "../../FPSGAMECharacter.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "Components/PointLightComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Net/UnrealNetwork.h"

UKukriDecisiveComponent::UKukriDecisiveComponent()
{
    SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
double UKukriDecisiveComponent::Clock() const
{const auto* W=GetWorld();const auto* GS=W?W->GetGameState():nullptr;return GS?GS->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;}
void UKukriDecisiveComponent::Configure(const UColdSteelStatusModel* Model)
{
    Profile=Model;TArray<FString> Next;
    const auto* Main=Model?Model->ActiveKukriWeapon():nullptr;
    const auto* Tool=Model?Model->ActiveProductionTool():nullptr;
    const auto* Pair=Main&&Main==Model->Equipped()?Model->Equipped(Main->Cell==6?8:11):nullptr;
    const FString Key=FString::Printf(TEXT("%d|%s|%s|%s"),Main?Main->Cell:-1,
        Main?*Main->InstanceId:TEXT(""),Pair?*Pair->InstanceId:TEXT(""),Tool?*Tool->InstanceId:TEXT(""));
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* G=Model&&Model->GetGameInstance()?Model->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    if(G&&!Tool&&(!Health||!Health->IsDead()))
        for(const auto* Item:{Main,ColdSteelMelee::PairedOneHandedWeapon(Main,Model)})
            if(Item&&Item->Definition==TEXT("ue_kukri")&&G->Installed(*Item).FindRef(TEXT("lanyard"))==TEXT("kukri_lanyard_decisive"))Next.Add(Item->InstanceId);
    TArray<FString> Replicated;for(const auto& B:State.Blades)Replicated.Add(B.Instance);
    if(bConfigured&&(Next!=Equipped||Key!=EquipmentKey))
    {
        if(!GetOwner()->HasAuthority())RequiredRevision=FMath::Max(RequiredRevision,State.Revision+uint32(State.EquipmentKey!=Key||Replicated!=Next));
        Attacks.Reset();LocalActive.Reset();for(auto& A:Pending)A={};ResolveAge=0.f;
    }
    // A lone off-hand blade (main hand empty) is held and shown in the left hand: it counts as the off-hand.
    Equipped=Next;EquipmentKey=Key;MainHandInstance=Main&&Main==Model->Equipped()?Main->InstanceId:FString();bConfigured=true;
    if(GetOwner()->HasAuthority()&&(Replicated!=Next||State.EquipmentKey!=Key))
    {
        State.Blades.Reset();State.EquipmentKey=Key;++State.Revision;
        for(const auto& Instance:Next){FKukriDecisiveBlade B;B.Instance=Instance;B.ReadyAt=Clock()+2.5;State.Blades.Add(B);}
        GetOwner()->ForceNetUpdate();
    }
    if(auto* K=GetOwner()->FindComponentByClass<UKukriWeaponComponent>())AddTickPrerequisiteComponent(K);
    if(auto* K=GetOwner()->FindComponentByClass<UOffhandKukriComponent>())AddTickPrerequisiteComponent(K);
    SetComponentTickEnabled(!Equipped.IsEmpty());Present();
}
bool UKukriDecisiveComponent::Matches(const FString& Instance) const
{
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return false;
    const auto* Pawn=Cast<APawn>(GetOwner());
    return Pawn&&!Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()?true:
        Equipped.Contains(Instance)&&State.EquipmentKey==EquipmentKey&&State.Revision>=RequiredRevision;
}
float UKukriDecisiveComponent::Charge(const FString& Instance) const
{
    if(!Matches(Instance))return 0.f;
    const auto* B=State.Blades.FindByPredicate([&](const auto& V){return V.Instance==Instance;});
    return B?FMath::Clamp(float(1.-(B->ReadyAt-Clock())/2.5),0.f,1.f):0.f;
}
bool UKukriDecisiveComponent::PreparationForHand(bool bOffhand,float& Progress) const
{
    Progress=0.f;
    for(const auto& Instance:Equipped)
    {
        if((Instance!=MainHandInstance)!=bOffhand||!Matches(Instance))continue;
        const auto* Blade=State.Blades.FindByPredicate([&](const auto& B){return B.Instance==Instance;});
        const double Now=Clock();
        if(!Blade||Blade->ReadyAt>Now+2.5)return false;
        // Hide an in-flight local swing immediately, including while its server receipt is travelling.
        const auto* Main=GetOwner()->FindComponentByClass<UKukriWeaponComponent>();
        const auto* Off=GetOwner()->FindComponentByClass<UOffhandKukriComponent>();
        if((Main&&Main->IsPendantAttackActive(Instance))||(Off&&Off->IsPendantAttackActive(Instance)))return false;
        Progress=FMath::Clamp(float(1.-(Blade->ReadyAt-Now)/2.5),0.f,1.f);return true;
    }
    return false;
}
UKukriDecisiveComponent::FAttack UKukriDecisiveComponent::Start(const FString& First,const FString& Second,bool Martial,double EndAt)
{
    FAttack A;A.Key=EquipmentKey;A.bMartial=Martial;
    const auto* M=Profile.Get();const auto* Main=M?M->ActiveKukriWeapon():nullptr;
    for(const auto* Item:{Main,ColdSteelMelee::PairedOneHandedWeapon(Main,M)})if(Item&&Item->Definition==TEXT("ue_kukri"))
    {
        const auto Stats=ColdSteelMelee::Evaluate(*Item,M);FBlade B;B.Instance=Item->InstanceId;
        B.DamageWeight=Stats.DamageParts.Total()*Stats.Modifiers.MartialDamage;
        B.ToughnessWeight=(Stats.DamageParts.BasePhysical+Stats.DamageParts.AddedPhysical)*Stats.Modifiers.MartialDamage*Stats.Modifiers.ToughnessDamage;
        B.bParticipating=B.Instance==First||B.Instance==Second;
        if(B.bParticipating)if(auto* Current=State.Blades.FindByPredicate([&](const auto& V){return V.Instance==B.Instance;}))
        {
            B.bReady=Charge(B.Instance)>=1.f;
            if(B.bReady)Current->ReleaseAt=Clock();
            Current->ReadyAt=EndAt+2.5;
        }
        A.Blades.Add(B);
    }
    GetOwner()->ForceNetUpdate();Present();return A;
}
void UKukriDecisiveComponent::Store(FAttack Attack)
{
    if(auto* A=Attacks.FindByPredicate([&](const auto& V){return V.Serial==Attack.Serial;}))*A=MoveTemp(Attack);
    else {if(Attacks.Num()>=64)Attacks.RemoveAt(0);Attacks.Add(MoveTemp(Attack));}
}
void UKukriDecisiveComponent::BeginLocal(const FColdSteelSkillShot& Shot,bool Martial,const FString& Second)
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||(!Pawn->IsLocallyControlled()&&GetNetMode()!=NM_Standalone))return;
    Configure(ColdSteelAuthority::ForPawn(Pawn));
    if(Equipped.IsEmpty()||!Shot.MasteryAttackSerial)return;
    auto A=Start(Shot.ItemInstance,Second,Martial,1.e12);A.Serial=Shot.MasteryAttackSerial;
    for(const auto& B:A.Blades)if(B.bParticipating&&Equipped.Contains(B.Instance))LocalActive.Add(B.Instance);
    Store(MoveTemp(A));
}
void UKukriDecisiveComponent::BeginServer(int32 Family,const FString& First,const FString& Second,bool Martial,float Duration)
{
    if(!GetOwner()->HasAuthority()||Family<0||Family>=5)return;
    Configure(ColdSteelAuthority::ForPawn(Cast<AFPSGAMECharacter>(GetOwner())));
    if(Equipped.IsEmpty()){Pending[Family]={};return;}
    FString Weapon=First;
    if(Weapon.IsEmpty())
    {
        const auto* M=Profile.Get();const auto* Main=M?M->ActiveKukriWeapon():nullptr;
        const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,M);
        if(Main&&Main->Definition==TEXT("ue_kukri"))Weapon=Main->InstanceId;
        else if(Off&&Off->Definition==TEXT("ue_kukri"))Weapon=Off->InstanceId;
    }
    Pending[Family]=Start(Weapon,Second,Martial,Clock()+FMath::Max(0.f,Duration));
}
void UKukriDecisiveComponent::EndServer(int32 Family)
{
    if(!GetOwner()->HasAuthority()||Family<0||Family>=5)return;
    auto& A=Pending[Family];if(A.bEnded||A.Key!=EquipmentKey)return;A.bEnded=true;
    for(const auto& B:A.Blades)if(B.bParticipating)
        if(auto* Current=State.Blades.FindByPredicate([&](const auto& V){return V.Instance==B.Instance;}))
            Current->ReadyAt=FMath::Min(Current->ReadyAt,Clock()+2.5);
    GetOwner()->ForceNetUpdate();
}
void UKukriDecisiveComponent::BindServerAttack(int32 Family,uint32 Serial)
{
    if(Family<0||Family>=5||!Serial||Pending[Family].Key!=EquipmentKey)return;
    auto A=Pending[Family];A.Serial=Serial;Store(MoveTemp(A));
}
FVector2D UKukriDecisiveComponent::Multipliers(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model)
{
    const auto* Pawn=Model?Model->RuntimePawn():nullptr;
    const auto* Self=Pawn?Pawn->FindComponentByClass<UKukriDecisiveComponent>():nullptr;
    const auto* A=Self?Self->Attacks.FindByPredicate([&](const auto& V){return V.Serial==Shot.MasteryAttackSerial;}):nullptr;
    if(!Shot.bMelee||Shot.bRicochet||(Shot.AttackMeta&0x40)||!A||A->Key!=Self->EquipmentKey)
        return UKukriRelentlessComponent::Multipliers(Shot,Model);
    double D=0,T=0,DW=0,TW=0;
    for(const auto& B:A->Blades)
    {
        if(!B.bParticipating||(Shot.AttackMeta!=0x16&&B.Instance!=Shot.ItemInstance))continue;
        // Compose per blade before combining a paired dash. Multiplying two
        // already-averaged pendant bonuses would incorrectly amplify the other hand.
        auto PerBlade=Shot;PerBlade.ItemInstance=B.Instance;if(PerBlade.AttackMeta==0x16)PerBlade.AttackMeta=0;
        const auto R=UKukriRelentlessComponent::Multipliers(PerBlade,Model);
        const bool Active=B.bReady&&Shot.MeleeDamagePhase==0&&Self->Matches(B.Instance);
        const double DM=Active?(A->bMartial?1.70:1.35):1.,TM=Active?(A->bMartial?2.:1.5):1.;
        D+=B.DamageWeight*DM*R.X;T+=B.ToughnessWeight*TM*R.Y;DW+=B.DamageWeight;TW+=B.ToughnessWeight;
    }
    return FVector2D(DW>0?D/DW:1.,TW>0?T/TW:1.);
}
void UKukriDecisiveComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(GetOwner()->HasAuthority())
    {
        if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())
        {Configure(Profile.Get());return;}
        const auto* Main=GetOwner()->FindComponentByClass<UKukriWeaponComponent>();
        const auto* Off=GetOwner()->FindComponentByClass<UOffhandKukriComponent>();
        for(auto It=LocalActive.CreateIterator();It;++It)
            if(!(Main&&Main->IsPendantAttackActive(*It))&&!(Off&&Off->IsPendantAttackActive(*It)))
            {
                if(auto* B=State.Blades.FindByPredicate([&](const auto& V){return V.Instance==*It;}))B->ReadyAt=Clock()+2.5;
                It.RemoveCurrent();GetOwner()->ForceNetUpdate();
            }
    }
    if(GetNetMode()!=NM_DedicatedServer){ResolveAge-=Delta;if(ResolveAge<=0.f){ResolveVisuals();ResolveAge=.2f;}Present();}
}
void UKukriDecisiveComponent::OnRep_State()
{ResolveAge=0.f;SetComponentTickEnabled(!State.Blades.IsEmpty()||!Equipped.IsEmpty());Present();}
void UKukriDecisiveComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UKukriDecisiveComponent,State);}
void UKukriDecisiveComponent::EndPlay(const EEndPlayReason::Type Reason)
{for(const auto& Light:Lights)if(Light)Light->DestroyComponent();Lights.Reset();Super::EndPlay(Reason);}

void UKukriDecisiveComponent::ResolveVisuals()
{
    for(auto& V:Visuals)if(auto* Mesh=V.Mesh.Get())
    {
        RemoveTickPrerequisiteComponent(Mesh);
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)if(auto* M=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(I)))
        {M->SetScalarParameterValue(TEXT("DecisiveCharge"),0.f);M->SetScalarParameterValue(TEXT("DecisiveFlash"),0.f);M->SetScalarParameterValue(TEXT("DecisiveReadyPulse"),0.f);M->SetScalarParameterValue(TEXT("DecisiveBreath"),0.f);}
    }
    Visuals.Reset();const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();if(!Body)return;
    TArray<FFPSWeatherWeaponMesh> Meshes,WorldMeshes;Body->GetWeatherWeaponMeshes(Meshes,false);Body->GetWeatherWeaponMeshes(WorldMeshes,true);
    for(const auto& Entry:Meshes)
        if(auto* Mesh=Cast<USwordTasselMeshComponent>(Entry.Mesh);Mesh&&Mesh->GetStaticMesh()&&Mesh->GetStaticMesh()->GetFName()==TEXT("SM_Kukri_DecisivePendant"))
        {Visuals.Add({Mesh,Entry.Instance,WorldMeshes.ContainsByPredicate([Mesh](const auto& W){return W.Mesh==Mesh;})});AddTickPrerequisiteComponent(Mesh);}
}
void UKukriDecisiveComponent::Present()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const auto* Pawn=Cast<APawn>(GetOwner());const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool World=Pawn&&(!Pawn->IsLocallyControlled()||(Body&&Body->IsThirdPersonViewEnabled()));
    int32 LightIndex=0;TArray<FString,TInlineAllocator<2>> Lit;
    for(auto& V:Visuals)if(auto* Mesh=V.Mesh.Get())
    {
        const float Level=Charge(V.Instance);const auto* B=State.Blades.FindByPredicate([&](const auto& Blade){return Blade.Instance==V.Instance;});
        const float Age=B?float(Clock()-B->ReleaseAt):100.f;
        const float Flash=Matches(V.Instance)&&Age>=0.f&&Age<.32f?(Age<.12f?1.f:1.f-(Age-.12f)/.2f):0.f;
        const float ReadyAge=B?float(Clock()-B->ReadyAt):-1.f;
        const float ReadyPulse=Level>=1.f&&ReadyAge>=0.f?FMath::Square(FMath::Clamp(1.f-ReadyAge/.55f,0.f,1.f)):0.f;
        // Drive all material layers and the local light from the same replicated
        // ready clock. The initial flash decays into a clearly visible 2.4 s breath.
        const float Breath=Level>=1.f?.5f-.5f*FMath::Cos(FMath::Max(0.f,ReadyAge)*(2.f*PI/2.4f)):0.f;
        const float ReadyGlow=Level>=1.f?.2f+.6f*Breath+1.2f*ReadyPulse:0.f;
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)if(auto* M=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(I)))
        {M->SetScalarParameterValue(TEXT("DecisiveCharge"),Level);M->SetScalarParameterValue(TEXT("DecisiveFlash"),Flash);M->SetScalarParameterValue(TEXT("DecisiveReadyPulse"),ReadyPulse);M->SetScalarParameterValue(TEXT("DecisiveBreath"),Breath);}
        if((Level<1.f&&Flash<=0.f)||V.bWorld!=World||!Mesh->IsVisible()||Mesh->bHiddenInGame||GetOwner()->IsHidden()||Lit.Contains(V.Instance)||LightIndex>=2)continue;
        if(!Lights.IsValidIndex(LightIndex))
        {
            auto* Light=NewObject<UPointLightComponent>(GetOwner());Light->SetupAttachment(GetOwner()->GetRootComponent());
            Light->SetMobility(EComponentMobility::Movable);Light->SetCastShadows(false);
            Light->SetLightColor(FLinearColor(.12f,.38f,1.f));
            Light->SetIndirectLightingIntensity(0.f);Light->SetVolumetricScatteringIntensity(0.f);
            Light->MaxDrawDistance=500.f;Light->MaxDistanceFadeRange=100.f;Light->RegisterComponent();Lights.Add(Light);
        }
        // A tiny decorative fill must not use a near-surface inverse-square
        // hotspot: the crystal/engraving emissive carries the visible blue cue.
        // Set these here as well so already-created lights accept a live patch.
        auto* Light=Lights[LightIndex++].Get();Light->SetUseInverseSquaredFalloff(false);Light->SetIntensityUnits(ELightUnits::Unitless);
        Light->SetInverseExposureBlend(1.f);Light->SetSourceRadius(.2f);Light->SetAttenuationRadius(12.f);
        Light->SetIntensity(ReadyGlow+1.2f*Flash);
        Light->SetWorldLocation(Mesh->DeformedPoint(FVector(2.76604,1.2,-6.4),5));Light->SetVisibility(true);Lit.Add(V.Instance);
    }
    for(int32 I=LightIndex;I<Lights.Num();++I)Lights[I]->SetVisibility(false);
}
