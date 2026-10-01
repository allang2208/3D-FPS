#include "FPSRiftBladeComponent.h"
#include "RuneSwordComponent.h"
#include "GunsmithSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"

UFPSRiftBladeComponent::UFPSRiftBladeComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    RibbonAsset=TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Weapons/RiftSlash20260930/SM_RiftBladeRibbon.SM_RiftBladeRibbon")));
    DistortionAsset=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Weapons/RiftSlash20260930/M_RiftBladeDistortion.M_RiftBladeDistortion")));
}

void UFPSRiftBladeComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* World=GetWorld();
    if(!World||!World->IsGameWorld()||GetNetMode()!=NM_Standalone||!World->GetGameInstance()||!Cast<APawn>(GetOwner()))return;
    Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>();
    Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Sword.IsValid())return;
    AddTickPrerequisiteActor(GetOwner());AddTickPrerequisiteComponent(Sword.Get());
    Profile=World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(auto* M=Profile.Get())ProfileChanged=M->OnChanged.AddUObject(this,&ThisClass::RefreshEquipment);
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        TArray<FSoftObjectPath>{RibbonAsset.ToSoftObjectPath(),DistortionAsset.ToSoftObjectPath()},
        FStreamableDelegate::CreateWeakLambda(this,[this]()
        {
            RibbonMesh=RibbonAsset.Get();DistortionMaterial=DistortionAsset.Get();
            SetComponentTickEnabled(bEnabled&&RibbonMesh&&DistortionMaterial);
        }));
    RefreshEquipment();
}

void UFPSRiftBladeComponent::RefreshEquipment()
{
    const auto* M=Profile.Get();if(!M)return;
    const auto* Item=M->ActiveProductionTool();if(!Item)Item=M->Equipped();
    const FString Id=Item?Item->InstanceId:FString();const uint32 Hash=Item?GetTypeHash(Item->Data):0;
    if(Id==VisualItem&&Hash==VisualDataHash)return;
    const auto* Enchant=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    const auto* Catalog=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const bool bNext=Item&&Catalog&&Enchant&&Catalog->IsMelee(Item->Definition)&&Enchant->Effect(*Item,TEXT("riftSlash"))>0.;
    if(Id!=VisualItem||bNext!=bEnabled)ClearBlade();
    VisualItem=Id;VisualDataHash=Hash;bEnabled=bNext;
    SetComponentTickEnabled(bEnabled&&RibbonMesh&&DistortionMaterial);
}

void UFPSRiftBladeComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    USceneComponent* Parent=nullptr;FName Socket=NAME_None;FTransform LocalFrame;float Length=0.f;
    if(!bEnabled||!Sword.IsValid()||(Health.IsValid()&&Health->IsDead())
        ||!Sword->GetEnchantmentBladeAttachment(Parent,Socket,LocalFrame,Length)||!IsValid(Parent))
    {ClearBlade();return;}
    if(BladeAnchor&&(BladeAnchor->GetAttachParent()!=Parent||BladeAnchor->GetAttachSocketName()!=Socket))ClearBlade();
    if(!BladeAnchor)
    {
        // Attach to the rendered weapon/socket, including inspection animation.
        // Combat trace points are intentionally not the source of this frame.
        BladeAnchor=NewObject<USceneComponent>(GetOwner());
        BladeAnchor->SetMobility(EComponentMobility::Movable);
        BladeAnchor->SetupAttachment(Parent,Socket);BladeAnchor->SetRelativeTransform(LocalFrame);
        GetOwner()->AddInstanceComponent(BladeAnchor);BladeAnchor->RegisterComponent();
        for(int32 I=0;I<2;++I)
        {
            auto* Ribbon=NewObject<UStaticMeshComponent>(GetOwner());
            Ribbon->SetMobility(EComponentMobility::Movable);Ribbon->SetStaticMesh(RibbonMesh);
            Ribbon->SetCollisionEnabled(ECollisionEnabled::NoCollision);Ribbon->SetGenerateOverlapEvents(false);
            Ribbon->SetCanEverAffectNavigation(false);Ribbon->SetCastShadow(false);Ribbon->SetReceivesDecals(false);
            Ribbon->SetVisibleInRayTracing(false);Ribbon->SetOnlyOwnerSee(true);
            Ribbon->SetupAttachment(BladeAnchor);
            auto* Material=UMaterialInstanceDynamic::Create(DistortionMaterial,Ribbon);
            Material->SetScalarParameterValue(TEXT("Phase"),I*.47f);
            Material->SetScalarParameterValue(TEXT("Opacity"),0.f);
            Ribbon->SetMaterial(0,Material);
            GetOwner()->AddInstanceComponent(Ribbon);Ribbon->RegisterComponent();Ribbons.Add(Ribbon);
        }
    }
    else BladeAnchor->SetRelativeTransform(LocalFrame);
    Age+=Delta;
    const float Radius=FMath::Clamp(Length*.052f,3.5f,6.0f);
    const float Fade=FMath::SmoothStep(0.f,.28f,Age);
    for(int32 I=0;I<Ribbons.Num();++I)
    {
        const float Phase=I*PI;
        const float Spin=Phase+Age*(I==0?.63f:-.47f)+.16f*FMath::Sin(Age*1.7f+Phase);
        const float Breathe=1.f+.06f*FMath::Sin(Age*2.1f+Phase);
        Ribbons[I]->SetRelativeTransform(FTransform(FQuat(FVector::ForwardVector,Spin),FVector::ZeroVector,
            FVector(Length/100.f,Radius/5.f*Breathe,Radius/5.f*Breathe)));
        if(auto* Material=Cast<UMaterialInstanceDynamic>(Ribbons[I]->GetMaterial(0)))
            Material->SetScalarParameterValue(TEXT("Opacity"),Fade);
    }
}

void UFPSRiftBladeComponent::ClearBlade()
{
    for(auto& Ribbon:Ribbons)if(IsValid(Ribbon)){GetOwner()->RemoveInstanceComponent(Ribbon);Ribbon->DestroyComponent();}
    Ribbons.Reset();
    if(BladeAnchor){GetOwner()->RemoveInstanceComponent(BladeAnchor);BladeAnchor->DestroyComponent();BladeAnchor=nullptr;}
    Age=0.f;
}

void UFPSRiftBladeComponent::EndPlay(EEndPlayReason::Type Reason)
{
    if(auto* M=Profile.Get())M->OnChanged.Remove(ProfileChanged);
    if(LoadHandle)LoadHandle->CancelHandle();LoadHandle.Reset();
    ClearBlade();Super::EndPlay(Reason);
}
