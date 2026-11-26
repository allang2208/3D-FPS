#include "StableRidingHorse.h"
#include "StableHorseGear.h"
#include "StableHorseClaimSave.h"
#include "StableHorseAppearance.h"
#include "StableManeComponent.h"
#include "StableHorseGroundMesh.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "TimerManager.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/LevelStreaming.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

FStableTackBonuses AStableRidingHorse::TackBonuses() const
{
    return StableHorseGear::BonusesFromMask(EquippedTackMask);
}

float AStableRidingHorse::MountedDamageReduction() const
{
    return TackBonuses().MountedDamageReduction;
}

void AStableRidingHorse::RefreshTackLimits(bool bScaleCurrentVitals)
{
    const auto B=TackBonuses();
    const float OldMaxHealth=FMath::Max(1.f,MaxHealth);
    const float OldMaxStamina=FMath::Max(1.f,MaxStamina);
    const float NewMaxHealth=Traits.HealthLimit()*AffixBonuses.HealthMultiplier+B.MaxHealthAdd;
    const float NewMaxStamina=Traits.StaminaLimit()*AffixBonuses.StaminaMultiplier+B.MaxStaminaAdd;
    MaxHealth=NewMaxHealth;
    MaxStamina=NewMaxStamina;
    if(bScaleCurrentVitals && HasAuthority() && !IsRetreating())
    {
        const float PrevHealth=Health;
        Health=FMath::Clamp(NewMaxHealth*(Health/OldMaxHealth),0.f,NewMaxHealth);
        if(PrevHealth>0.f && Health<1.f)Health=1.f;
        Stamina=FMath::Clamp(NewMaxStamina*(Stamina/OldMaxStamina),0.f,NewMaxStamina);
    }
}

void AStableRidingHorse::SetEquippedTackMask(uint8 NewMask)
{
    if(!HasAuthority())return;
    const uint8 CleanMask=NewMask&0x0Fu;
    if(EquippedTackMask==CleanMask)
    {
        RefreshTackLimits(false);
        RefreshTackVisuals();
        return;
    }
    EquippedTackMask=CleanMask;
    RefreshTackLimits(true);
    RefreshTackVisuals();
    ForceNetUpdate();
}

void AStableRidingHorse::OnRep_EquippedTack()
{
    RefreshTackLimits(false);
    RefreshTackVisuals();
}

void AStableRidingHorse::RefreshTackVisuals()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* Skin=GetMesh();
    if(!Skin || !Skin->GetSkeletalMeshAsset())return;
    const bool bVisibleByFade=LastHorseFade<0.995f;
    if(TackVisuals.Num()<TackSlotCount)TackVisuals.SetNum(TackSlotCount);
    for(int32 Slot=0;Slot<TackSlotCount;++Slot)
    {
        const bool bEquipped=(EquippedTackMask&(1u<<Slot))!=0;
        const bool bShow=bEquipped && bVisibleByFade;
        USkeletalMeshComponent* Comp=TackVisuals[Slot].Get();
        if(!Comp && bEquipped)
        {
            USkeletalMesh* MeshAsset=TackMeshAssets[Slot].Get();
            if(!MeshAsset)continue;
            Comp=NewObject<USkeletalMeshComponent>(this,USkeletalMeshComponent::StaticClass(),
                FName(*FString::Printf(TEXT("HorseTackSkin_%d"),Slot)));
            Comp->SetSkeletalMeshAsset(MeshAsset);
            Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Comp->SetCollisionResponseToAllChannels(ECR_Ignore);
            Comp->SetGenerateOverlapEvents(false);
            Comp->SetCanEverAffectNavigation(false);
            Comp->SetCastShadow(true);
            Comp->BoundsScale=1.15f;
            Comp->RegisterComponent();
            Comp->AttachToComponent(Skin,FAttachmentTransformRules::SnapToTargetNotIncludingScale);
            Comp->SetLeaderPoseComponent(Skin,true);
            Comp->SetCustomPrimitiveDataFloat(0,LastHorseFade);
            TackVisuals[Slot]=Comp;
        }
        if(Comp)
        {
            Comp->SetCustomPrimitiveDataFloat(0,LastHorseFade);
            Comp->SetVisibility(bShow,true);
            Comp->SetHiddenInGame(!bShow,true);
        }
    }
    AppliedTackVisualMask=EquippedTackMask;
    SyncCoatMaterialAndFade();
}

void AStableRidingHorse::OnRep_Individual()
{
    Traits=FStableHorseTraits::FromId(IndividualId,BirthVersion,HorseLevel);
    AffixBonuses=StableHorseAffixes::Bonuses(IndividualId);
    RefreshTackLimits(false);
    ApplyIndividualAppearance();
    RefreshTackVisuals();
}

void AStableRidingHorse::ApplyIndividualAppearance()
{
    if(!Mane)return;
    // A streamed resident may be visible before the world's identity arrives.
    const FGuid VisualId=IndividualId.IsValid()?IndividualId:FGuid(0,0,0,0x523330);
    if(AppliedAppearance==VisualId)return;
    const auto A=FStableHorseAppearance::FromId(VisualId);
    if(auto* Skin=Cast<UStableHorseGroundMesh>(GetMesh()))
        Skin->SetTailShape(A.TailLength,A.TailWidth,A.TailSweepCm);
    if(GetNetMode()!=NM_DedicatedServer)
    {
        Mane->SetHairStyle(uint8(A.Mane));
        A.ApplyPigment(*GetMesh(),*Mane);
        bFadeMaterialsApplied=false;
        SyncCoatMaterialAndFade();
    }
    AppliedAppearance=VisualId;
}

void AStableRidingHorse::ResolveInitialIdentity()
{
    if(!ResolveIdentity())return;
    GetWorldTimerManager().ClearTimer(IdentityRetry);
    OnRep_Individual();
    if(!KeeperProfile.IsValid())return;
    for(TActorIterator<AStableRidingHorse> It(GetWorld());It;++It)
        if(*It!=this && It->HasActiveKeeper() && It->Identity()==IndividualId)
        {
            Destroy();return;
        }
}

bool AStableRidingHorse::ResolveIdentity()
{
    if(IndividualId.IsValid())return true;
    if(!HasAuthority())return false;
    if(!IsNetStartupActor() && !HasAnyFlags(RF_WasLoaded) && !ActorHasTag(TEXT("VillageStable.Horses")))
    {
        IndividualId=FGuid::NewGuid();
        FStableMountRecord Initial=Condition();
        Initial.ApplyBirthLimits();
        OnRep_Individual();
        Health=Initial.Health;Stamina=Initial.Stamina;
        ForceNetUpdate();return true;
    }
    FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    for(const auto& Streaming:GetWorld()->GetStreamingLevels())
        if(Streaming && Streaming->GetLoadedLevel()==GetLevel())
        {
            Map=Streaming->PackageNameToLoad.IsNone()?Streaming->GetWorldAssetPackageName():Streaming->PackageNameToLoad.ToString();
            break;
        }
    Map=UWorld::RemovePIEPrefix(Map);
    FGuid WorldId;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
    {
        WorldId=It->WorldId;
        if(!WorldId.IsValid())
        {
            if(!GetWorldTimerManager().IsTimerActive(IdentityRetry))
                GetWorldTimerManager().SetTimer(IdentityRetry,this,&AStableRidingHorse::ResolveInitialIdentity,1.f,true);
            return false;
        }
        break;
    }
    GetWorldTimerManager().ClearTimer(IdentityRetry);
    // Placed UObject names are serialized in the level. PIE prefixes and animated poses
    // are deliberately excluded from the source identity.
    OriginId=FGuid::NewDeterministicGuid(Map+TEXT("/")+GetName()+TEXT("/")+WorldId.ToString());
    ClaimSlot=TEXT("StableResident_")+OriginId.ToString(EGuidFormats::Digits);
    if(UGameplayStatics::DoesSaveGameExist(ClaimSlot,0))
    {
        auto* Title=Cast<UStableHorseClaimSave>(UGameplayStatics::LoadGameFromSlot(ClaimSlot,0));
        if(!Title||!Title->Individual.IsValid()||!Title->Profile.IsValid())return false;
        IndividualId=Title->Individual;KeeperProfile=Title->Profile;BirthVersion=Title->BirthVersion;
    }
    else IndividualId=OriginId;
    // Terrain identity can become available after BeginPlay, including after an injury.
    FStableMountRecord Initial=Condition();
    Initial.ApplyBirthLimits();
    OnRep_Individual();
    Health=Initial.Health;Stamina=Initial.Stamina;
    ForceNetUpdate();return true;
}
bool AStableRidingHorse::RecordClaim(FGuid OwnerId,FGuid Id,uint8 EntryBirthVersion)
{
    if(!HasAuthority()||!OwnerId.IsValid()||!Id.IsValid()||!ResolveIdentity())return false;
    if(KeeperProfile.IsValid())return KeeperProfile==OwnerId && IndividualId==Id;
    if(!ClaimSlot.IsEmpty())
    {
        auto* Title=NewObject<UStableHorseClaimSave>();Title->Profile=OwnerId;Title->Individual=Id;Title->BirthVersion=EntryBirthVersion;
        if(!UGameplayStatics::SaveGameToSlot(Title,ClaimSlot,0))return false;
    }
    KeeperProfile=OwnerId;IndividualId=Id;BirthVersion=EntryBirthVersion;OnRep_Individual();ForceNetUpdate();return true;
}
