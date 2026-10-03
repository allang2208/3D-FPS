#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Items/PotionVisuals.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

bool UFPSPlayerBodyComponent::PresentConsumableDiscard(UStaticMeshComponent* Source,const FVector& Velocity,float)
{
    if(FPSPlayerBodyWorldBodySuppressed()||!BodyAnimation)return false;
    auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();if(!Potion)return false;
    if(LocalConsumableSerial!=Potion->PresentationSerial){LocalConsumableSerial=Potion->PresentationSerial;PendingDiscardFlags=0;bPendingBottleDrop=false;}
    if(Source==Potion->Bottle)bPendingBottleDrop=Velocity.Z<0.f;
    PendingDiscardFlags|=Source==Potion->Stopper?4:1;PendingDiscardUntil=ServerClock()+.3f;
    // Keep the accepted first-person release origin. Remote viewers and F6 use
    // the body's achieved hand; neither path spawns a second local bottle.
    return IsThirdPersonViewEnabled();
}
void UFPSPlayerBodyComponent::CreateConsumable(FName Definition)
{
    ++ConsumableRequest;if(ConsumableLoad){ConsumableLoad->CancelHandle();ConsumableLoad.Reset();}
    for(const auto& Part:ConsumableParts)if(Part)Part->DestroyComponent();ConsumableParts.Reset();ConsumableLiquid=nullptr;
    WorldConsumable=Definition;LastLiquidLevel=-10000.f;
    if(Definition.IsNone())return;
    TArray<FSoftObjectPath> Paths;const FString Name=Definition.ToString();
    const int32 Tier=PotionVisuals::FindTier(Name);
    if(Tier!=INDEX_NONE)
    {
        const auto& V=PotionVisuals::Tiers()[Tier];
        Paths={FSoftObjectPath(V.Shell),FSoftObjectPath(V.Liquid),FSoftObjectPath(V.Stopper),
            FSoftObjectPath(V.LiquidMaterial.IsEmpty()?PotionVisuals::LiquidMaterial(Name.StartsWith(TEXT("mp_"))):V.LiquidMaterial)};
    }
    else if(Name==TEXT("bread")||Name==TEXT("baguette_bread"))
        Paths={FSoftObjectPath(Name==TEXT("bread")?TEXT("/Game/Items/Consumables/Bread20261003/SM_Bread.SM_Bread")
            :TEXT("/Game/Items/Consumables/Baguette20261003/SM_Baguette.SM_Baguette"))};
    else if(Name==TEXT("soda_can"))Paths={FSoftObjectPath(TEXT("/Game/Items/Consumables/SodaCan20261003/SM_SodaCan.SM_SodaCan"))};
    else return;
    const uint32 Request=ConsumableRequest;
    TArray<FSoftObjectPath> Wanted;for(const auto& P:Paths)if(!P.IsNull())Wanted.AddUnique(P);
    ConsumableLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Wanted,FStreamableDelegate::CreateWeakLambda(this,[this,Paths,Request]()
    {
        if(Request!=ConsumableRequest||!GetBodyMesh())return;
        ConsumableParts.SetNum(3);
        for(int32 I=0;I<3&&I<Paths.Num();++I)if(auto* Asset=Cast<UStaticMesh>(Paths[I].ResolveObject()))
        {
            auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);GetOwner()->AddInstanceComponent(Part);
            Part->SetStaticMesh(Asset);Part->SetupAttachment(GetBodyMesh(),TEXT("hand_l"));
            Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCanEverAffectNavigation(false);Part->SetVisibility(false);
            Part->RegisterComponent();ConsumableParts[I]=Part;
            if(I==1&&Paths.Num()>3)if(auto* Material=Cast<UMaterialInterface>(Paths[3].ResolveObject()))
            {ConsumableLiquid=UMaterialInstanceDynamic::Create(Material,this);Part->SetMaterial(0,ConsumableLiquid);}
        }
        UpdateConsumable(DisplayState.Contacts);
    }));
}
void UFPSPlayerBodyComponent::UpdateConsumable(const FFPSBodyMotionSample& Sample)
{
    if(WorldConsumable!=Sample.Consumable)CreateConsumable(Sample.Consumable);
    if(WorldConsumableSerial!=Sample.ConsumableSerial){WorldConsumableSerial=Sample.ConsumableSerial;WorldDiscardFlags=0;QueuedWorldDiscards=0;}
    const bool OwnerFirst=Character.IsValid()&&Character->IsLocallyControlled()&&!IsThirdPersonViewEnabled();
    for(int32 I=0;I<ConsumableParts.Num();++I)if(auto* Part=ConsumableParts[I].Get())
    {
        Part->SetRelativeTransform(Sample.Props[I]);
        const bool Show=(Sample.PropVisibility&(1<<I))&&!FPSPlayerBodyWorldBodyHidden();
        if(Part->IsVisible()!=Show)Part->SetVisibility(Show);
        FPSBodyEquipment::ApplyOwnerVisibilityFlags(Part,false,OwnerFirst);
        FPSBodyEquipment::ApplyShadowFlags(Part,Show&&ShouldWorldBodyCastShadow());
        if((Sample.DiscardFlags&(1<<I))&&!(WorldDiscardFlags&(1<<I)))
        {
            // Delay detachment until the body has published this frame's achieved
            // hand IK. The attached transform then matches the last held frame.
            QueuedWorldDiscards|=1<<I;WorldDiscardFlags|=1<<I;
            if(I==0)bQueuedBottleDrop=Sample.DroppedBottle;
        }
    }
    if(ConsumableLiquid&&LastLiquidLevel!=Sample.LiquidLevel)
    {LastLiquidLevel=Sample.LiquidLevel;ConsumableLiquid->SetScalarParameterValue(TEXT("FillHeightCm"),Sample.LiquidLevel);}
}
void UFPSPlayerBodyComponent::OnBodyPoseFinalized()
{
    if(!QueuedWorldDiscards)return;
    if(GetBodyMesh())GetBodyMesh()->UpdateChildTransforms();
    for(int32 I=0;I<3;++I)if(QueuedWorldDiscards&(1<<I))
        ReleaseConsumable(I,I==2?FVector(80,-140,160):bQueuedBottleDrop?FVector(40,-40,-50):FVector(540,-360,190),I==2?2.5f:bQueuedBottleDrop?5.f:7.f);
    QueuedWorldDiscards=0;
}
void UFPSPlayerBodyComponent::ReleaseConsumable(int32 Index,const FVector& Velocity,float Lifetime)
{
    if(Character.IsValid()&&Character->IsLocallyControlled()&&!IsThirdPersonViewEnabled())return;
    auto* Part=ConsumableParts.IsValidIndex(Index)?ConsumableParts[Index].Get():nullptr;if(!Part||!Part->GetStaticMesh())return;
    FActorSpawnParameters Params;Params.Owner=GetOwner();Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Prop=GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),Part->GetComponentTransform(),Params);if(!Prop)return;
    auto* Mesh=Prop->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetStaticMesh(Part->GetStaticMesh());
    for(int32 M=0;M<Part->GetNumMaterials();++M)Mesh->SetMaterial(M,Part->GetMaterial(M));
    Mesh->SetCanEverAffectNavigation(false);Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Mesh->SetCollisionObjectType(ECC_PhysicsBody);Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
    Mesh->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);Mesh->SetCollisionResponseToChannel(ECC_WorldDynamic,ECR_Block);
    Mesh->IgnoreActorWhenMoving(GetOwner(),true);Mesh->SetSimulatePhysics(true);
    Mesh->SetPhysicsLinearVelocity(GetOwner()->GetActorQuat().RotateVector(Velocity));
    Mesh->SetPhysicsAngularVelocityInDegrees(GetOwner()->GetActorQuat().RotateVector(FVector(-210,360,180)));
    Prop->SetLifeSpan(Lifetime);
}
void UFPSPlayerBodyComponent::ClearMotion()
{
    if(GetBodyMesh()&&BodyPoseFinalizedHandle.IsValid())GetBodyMesh()->UnregisterOnBoneTransformsFinalizedDelegate(BodyPoseFinalizedHandle);
    CreateConsumable(NAME_None);MotionBindings.Reset();MotionMaps.Reset();
    if(WorldStaffLight){WorldStaffLight->DestroyComponent();WorldStaffLight=nullptr;}WorldStaffMaterials.Reset();
}
