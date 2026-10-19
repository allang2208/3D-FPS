#include "Saiga12KAttachments.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

UStaticMeshComponent* Saiga12KAttachments::Configure(AActor* Owner,USkeletalMeshComponent* Host,
 UStaticMeshComponent* Part,const FString& Key,bool Enabled,const FTransform& Mount)
{
 if(!Host||!Host->GetSkeletalMeshAsset())Enabled=false;
 if(Enabled)
 {
  auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));
  if(Mesh)
  {
   if(!Part){Part=NewObject<UStaticMeshComponent>(Owner);Part->SetupAttachment(Host,TEXT("WPN_root"));Part->RegisterComponent();}
   else Part->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
   Part->EmptyOverrideMaterials();Part->SetStaticMesh(Mesh);Part->SetRelativeTransform(Mount);
   Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;
   Part->SetOnlyOwnerSee(Host->bOnlyOwnerSee);Part->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
  }
  else Enabled=false;
 }
 if(Part)
 {
  // An uninstalled cached component must not remain in the replicated weapon
  // layout. The owner's preview history can differ from the server's history.
  if(!Enabled)Part->SetStaticMesh(nullptr);
  Part->SetVisibility(Enabled);
 }
 return Part;
}
void Saiga12KAttachments::FactorySection(USkeletalMeshComponent* Host,FName Slot,bool Visible)
{
 const auto* Mesh=Host?Host->GetSkeletalMeshAsset():nullptr;if(!Mesh)return;
 if(const auto* Render=Mesh->GetResourceForRendering())
  for(int32 L=0;L<Render->LODRenderData.Num();++L)
   for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
   {
    const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
    if(Mesh->GetMaterials().IsValidIndex(M)
      &&(Mesh->GetMaterials()[M].MaterialSlotName==Slot
       ||(Slot==TEXT("Saiga12K_Stock")&&Mesh->GetMaterials()[M].MaterialSlotName==TEXT("Saiga12K_StockPad"))))
     Host->ShowMaterialSection(M,S,Visible,L);
   }
}
