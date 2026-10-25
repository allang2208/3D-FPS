#include "AncientBreakingSealComponent.h"
#include "../Weapons/AncientSealSeat.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Character.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"

namespace
{
const FSoftObjectPath MarkPath(TEXT("/Game/Weapons/CommonHammerSeats20261024/AncientSealV1/SM_AncientSeal_TargetMark.SM_AncientSeal_TargetMark"));
const FSoftObjectPath MaterialPath(TEXT("/Game/Weapons/CommonHammerSeats20261024/AncientSealV1/M_AncientSeal_TargetMark.M_AncientSeal_TargetMark"));
const FSoftObjectPath SoundPath(TEXT("/Game/Weapons/CommonHammerSeats20261024/AncientSealV1/S_AncientSeal_Impact.S_AncientSeal_Impact"));
}

bool AncientSealSeat::Installed(const FColdSteelItem& Item)
{
    if(!Supports(Item.Definition))return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Seat;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&(*Parts)->TryGetStringField(TEXT("head_mount"),Seat)&&Seat==Part;
}

UAncientBreakingSealComponent::UAncientBreakingSealComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void UAncientBreakingSealComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UAncientBreakingSealComponent,LocalPoint);DOREPLIFETIME(UAncientBreakingSealComponent,SourceActor);
    DOREPLIFETIME(UAncientBreakingSealComponent,ExpiresAt);DOREPLIFETIME(UAncientBreakingSealComponent,Revision);
}
double UAncientBreakingSealComponent::Clock() const
{
    const auto* World=GetWorld();if(const auto* GS=World?World->GetGameState():nullptr)return GS->GetServerWorldTimeSeconds();
    return World?World->GetTimeSeconds():0.;
}
float UAncientBreakingSealComponent::Remaining() const{return float(FMath::Max(0.,ExpiresAt-Clock()));}
UAncientBreakingSealComponent* UAncientBreakingSealComponent::Apply(AActor* Target,AActor* Source,const FVector& Point,float Seconds)
{
    if(!IsValid(Target)||!Target->HasAuthority()||Seconds<=0.f)return nullptr;
    auto* Seal=Target->FindComponentByClass<UAncientBreakingSealComponent>();
    if(!Seal){Seal=NewObject<UAncientBreakingSealComponent>(Target);Target->AddInstanceComponent(Seal);Seal->RegisterComponent();}
    Seal->SourceActor=Source;Seal->LocalPoint=Target->GetActorTransform().InverseTransformPosition(Point);
    Seal->ExpiresAt=Seal->Clock()+Seconds;++Seal->Revision;
    Seal->GetWorld()->GetTimerManager().SetTimer(Seal->ExpireTimer,Seal,&UAncientBreakingSealComponent::Clear,Seconds,false);
    UStatusEffectsComponent::GetOrCreate(Target)->SetTimed(TEXT("breakingSeal"),Seconds,1);
    Seal->OnRep_State();Target->ForceNetUpdate();return Seal;
}
void UAncientBreakingSealComponent::Clear()
{
    if(!GetOwner()->HasAuthority())return;
    ExpiresAt=0.;GetWorld()->GetTimerManager().ClearTimer(ExpireTimer);
    if(auto* Display=GetOwner()->FindComponentByClass<UStatusEffectsComponent>())Display->Remove(TEXT("breakingSeal"));
    OnRep_State();GetOwner()->ForceNetUpdate();
}
void UAncientBreakingSealComponent::PulseSeat(AActor* Source)
{
    if(!IsValid(Source)||!Source->GetWorld())return;
    TInlineComponentArray<UStaticMeshComponent*> Parts(Source);
    for(auto* Part:Parts)if(Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName().Contains(TEXT("AncientSeal")))
        for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)
            if(auto* Mat=Part->GetMaterial(Slot);Mat&&Mat->GetMaterial()->GetName()==TEXT("M_AncientSeal_Inlay"))
            {
                auto* MID=Cast<UMaterialInstanceDynamic>(Mat);if(!MID)MID=Part->CreateDynamicMaterialInstance(Slot);
                if(MID)MID->SetScalarParameterValue(TEXT("SealHitAt"),Source->GetWorld()->GetTimeSeconds());
            }
}
void UAncientBreakingSealComponent::OnRep_State()
{
    const bool Active=Remaining()>0.f;
    if(!GetOwner()->HasAuthority())
    {
        if(Active)UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("breakingSeal"),Remaining(),1);
        else if(auto* Display=GetOwner()->FindComponentByClass<UStatusEffectsComponent>())Display->Remove(TEXT("breakingSeal"));
    }
    if(!Active){HideVisuals();SetComponentTickEnabled(false);return;}
    if(GetNetMode()==NM_DedicatedServer)return;
    if(ShownRevision!=Revision){ShownRevision=Revision;VisualAge=0.f;bPlayedSound=false;PulseSeat(SourceActor);}
    SetComponentTickEnabled(true);RequestVisuals();CreateVisual();
}
void UAncientBreakingSealComponent::RequestVisuals()
{
    if(bRequested)return;bRequested=true;
    TWeakObjectPtr<UAncientBreakingSealComponent> Weak(this);
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{MarkPath,MaterialPath,SoundPath},FStreamableDelegate::CreateLambda([Weak]()
    {
        if(!Weak.IsValid())return;auto* Self=Weak.Get();
        Self->MarkMesh=Cast<UStaticMesh>(MarkPath.ResolveObject());Self->MarkMaterial=Cast<UMaterialInterface>(MaterialPath.ResolveObject());
        Self->HitSound=Cast<USoundBase>(SoundPath.ResolveObject());Self->CreateVisual();
    }));
}
void UAncientBreakingSealComponent::CreateVisual()
{
    if(Remaining()<=0.f||!MarkMesh||!MarkMaterial)return;
    if(const auto* Combat=GetOwner()->FindComponentByClass<UMonsterCombatComponent>();Combat&&Combat->IsDead())return;
    if(!Mark)
    {
        Mark=NewObject<UStaticMeshComponent>(GetOwner());GetOwner()->AddInstanceComponent(Mark);
        Mark->SetupAttachment(GetOwner()->GetRootComponent());Mark->SetAbsolute(false,false,true);
        Mark->SetStaticMesh(MarkMesh);Mark->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mark->SetCastShadow(false);Mark->bReceivesDecals=false;
        MarkMID=UMaterialInstanceDynamic::Create(MarkMaterial,this);Mark->SetMaterial(0,MarkMID);Mark->RegisterComponent();
    }
    if(!OverheadMark)
    {
        // Only colliding body components determine the initial size. The seal
        // meshes have no collision, so they never raise their own anchor.
        FVector Origin,Extent;GetOwner()->GetActorBounds(true,Origin,Extent);
        FallbackLocalTop=GetOwner()->GetActorTransform().InverseTransformPosition(Origin+FVector(0,0,Extent.Z));
        const float Height=FMath::Clamp(float(Extent.Z)*.32f,26.f,44.f);
        OverheadScale=Height/FMath::Max(1.f,float(MarkMesh->GetBounds().BoxExtent.Z)*2.f);
        OverheadHalfHeight=Height*.5f;
        OverheadMark=NewObject<UStaticMeshComponent>(GetOwner());GetOwner()->AddInstanceComponent(OverheadMark);
        OverheadMark->SetupAttachment(GetOwner()->GetRootComponent());OverheadMark->SetAbsolute(false,false,true);
        OverheadMark->SetStaticMesh(MarkMesh);OverheadMark->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        OverheadMark->SetCastShadow(false);OverheadMark->bReceivesDecals=false;
        OverheadMark->SetCanEverAffectNavigation(false);
        OverheadMID=UMaterialInstanceDynamic::Create(MarkMaterial,this);
        OverheadMID->SetVectorParameterValue(TEXT("MarkColor"),FLinearColor(4.f,2.4f,.42f));
        OverheadMark->SetMaterial(0,OverheadMID);OverheadMark->RegisterComponent();
    }
    UpdateVisuals();
}
void UAncientBreakingSealComponent::HideVisuals()
{
    if(Mark)Mark->SetVisibility(false);
    if(OverheadMark)OverheadMark->SetVisibility(false);
}
void UAncientBreakingSealComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,Type,Function);
    const float Left=Remaining();const auto* Combat=GetOwner()->FindComponentByClass<UMonsterCombatComponent>();
    if(Left<=0.f||(Combat&&Combat->IsDead()))
    {if(GetOwner()->HasAuthority())Clear();HideVisuals();SetComponentTickEnabled(false);return;}
    VisualAge+=Delta;UpdateVisuals();
}
void UAncientBreakingSealComponent::UpdateVisuals()
{
    if(!Mark||!MarkMID||!OverheadMark||!OverheadMID)return;
    auto* Viewer=UGameplayStatics::GetPlayerCameraManager(this,0);if(!Viewer)return;
    const float Left=Remaining();
    const float TailFade=FMath::Clamp(Left/.7f,0.f,1.f);
    const FVector Point=GetOwner()->GetActorTransform().TransformPosition(LocalPoint);
    const FVector Toward=(Viewer->GetCameraLocation()-Point).GetSafeNormal();
    Mark->SetWorldLocation(Point+Toward*4.f);Mark->SetWorldRotation(FRotationMatrix::MakeFromYZ(-Toward,FVector::UpVector).Rotator());
    Mark->SetWorldScale3D(FVector(.85f+.15f*FMath::Exp(-VisualAge*6.f)));
    MarkMID->SetScalarParameterValue(TEXT("MarkOpacity"),TailFade*(.32f+.68f*FMath::Exp(-VisualAge*8.f)));
    Mark->SetVisibility(true);

    FVector Top=GetOwner()->GetActorTransform().TransformPosition(FallbackLocalTop);
    if(const auto* Character=Cast<ACharacter>(GetOwner()))
    {
        if(const auto* Capsule=Character->GetCapsuleComponent())
            Top=Capsule->GetComponentLocation()+FVector(0,0,Capsule->GetScaledCapsuleHalfHeight());
        // Use only the character's body bounds, never attached weapons or VFX.
        if(const auto* Body=Character->GetMesh();Body&&Body->GetSkeletalMeshAsset())
            Top.Z=FMath::Max(Top.Z,Body->Bounds.Origin.Z+Body->Bounds.BoxExtent.Z);
    }
    const float Phase=float(FMath::Fmod(Clock(),1000.))*2.2f;
    const FVector Hover=Top+FVector(0,0,OverheadHalfHeight+15.f+3.f*FMath::Sin(Phase));
    const FVector Facing=(Viewer->GetCameraLocation()-Hover).GetSafeNormal();
    OverheadMark->SetWorldLocation(Hover);
    OverheadMark->SetWorldRotation(FRotationMatrix::MakeFromYZ(-Facing,FVector::UpVector).Rotator());
    OverheadMark->SetWorldScale3D(FVector(OverheadScale*(1.f+.08f*FMath::Exp(-VisualAge*8.f))));
    OverheadMID->SetScalarParameterValue(TEXT("MarkOpacity"),TailFade*(.82f+.08f*FMath::Sin(Phase)+.10f*FMath::Exp(-VisualAge*8.f)));
    OverheadMark->SetVisibility(true);
    if(!bPlayedSound&&HitSound){bPlayedSound=true;if(VisualAge<.45f)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Point,.22f);}
}
void UAncientBreakingSealComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(ExpireTimer);
    if(AssetLoad)AssetLoad->CancelHandle();AssetLoad.Reset();
    if(IsValid(Mark))Mark->DestroyComponent();Mark=nullptr;MarkMID=nullptr;
    if(IsValid(OverheadMark))OverheadMark->DestroyComponent();OverheadMark=nullptr;OverheadMID=nullptr;
    Super::EndPlay(Reason);
}
