#include "Saiga12KMagazineAssets.h"
#include "Saiga12KAttachments.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

UStaticMeshComponent* Saiga12KMagazineAssets::Configure(AActor* Owner,USkeletalMeshComponent* Host,
 UStaticMeshComponent* PartComponent,const FString& Variant,bool Enabled)
{
 if(!Host||!Host->GetSkeletalMeshAsset())Enabled=false;
 if(Enabled)
 {
  if(auto* Mesh=LoadObject<UStaticMesh>(nullptr,Variant==DrumPart?DrumMeshPath:MeshPath))
  {
   if(!PartComponent)
   {
    PartComponent=NewObject<UStaticMeshComponent>(Owner);
    PartComponent->SetupAttachment(Host,TEXT("WPN_SOCKET_Magazine"));
    PartComponent->RegisterComponent();
   }
   else PartComponent->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_SOCKET_Magazine"));
   PartComponent->EmptyOverrideMaterials();PartComponent->SetStaticMesh(Mesh);
   // Authored in the original magazine bone's centimetre frame. This bone
   // inherits the native weapon's 100x scale and owns both reload trajectories.
   PartComponent->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
   PartComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);PartComponent->SetCastShadow(false);
   PartComponent->bReceivesDecals=false;PartComponent->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
   PartComponent->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
  }
  else Enabled=false;
 }
 if(PartComponent)
 {
  if(!Enabled)PartComponent->SetStaticMesh(nullptr);
  PartComponent->SetVisibility(Enabled);
 }
 Saiga12KAttachments::FactorySection(Host,TEXT("Saiga12K_Magazine"),!Enabled);
 return PartComponent;
}
