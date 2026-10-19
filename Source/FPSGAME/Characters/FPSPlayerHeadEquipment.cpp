#include "FPSPlayerBodyComponent.h"
#include "FPSHeadEquipmentMeshComponent.h"
#include "../UI/FPSHelmetVisorWidget.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Texture2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Dom/JsonObject.h"

namespace FPSHeadEquipment
{
TSharedPtr<FJsonObject> Object(const TSharedPtr<FJsonObject>& Root,const FString& Key)
{const TSharedPtr<FJsonObject>* Value=nullptr;return Root&&Root->TryGetObjectField(Key,Value)?*Value:nullptr;}
FString Text(const TSharedPtr<FJsonObject>& Root,const TCHAR* Key)
{FString Value;if(Root)Root->TryGetStringField(Key,Value);return Value;}
float Number(const TSharedPtr<FJsonObject>& Root,const TCHAR* Key,float Default)
{double Value=Default;if(Root)Root->TryGetNumberField(Key,Value);return float(Value);}
FVector Vector(const TSharedPtr<FJsonObject>& Root,const TCHAR* Key,const FVector& Default)
{
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    return Root&&Root->TryGetArrayField(Key,Values)&&Values->Num()==3
        ?FVector((*Values)[0]->AsNumber(),(*Values)[1]->AsNumber(),(*Values)[2]->AsNumber()):Default;
}
}
void UFPSPlayerBodyComponent::ClearHeadEquipment()
{
    ++HeadEquipmentRequest;
    if(HeadEquipmentLoad){HeadEquipmentLoad->CancelHandle();HeadEquipmentLoad.Reset();}
    if(HeadEquipment){HeadEquipment->DestroyComponent();HeadEquipment=nullptr;}
    if(HelmetVisor){HelmetVisor->RemoveFromParent();HelmetVisor=nullptr;}
    HeadEquipmentKey.Reset();bHeadEquipmentCoversHair=false;
}
bool UFPSPlayerBodyComponent::ShouldShowHelmetVisor() const
{
    return HelmetVisor&&Character.IsValid()&&Character->IsLocallyControlled()&&
        !IsThirdPersonViewEnabled()&&!IsDeathViewActive()&&!Character->IsHidden();
}
void UFPSPlayerBodyComponent::UpdateHeadEquipment(FName Definition)
{
    using namespace FPSHeadEquipment;
    HeadEquipmentDefinition=Definition;
    auto* Body=GetBodyMesh();if(!Body||GetNetMode()==NM_DedicatedServer)return;
    const FName Head=ResolveAppearance(AppliedAppearance).HeadId;
    const auto Recipe=Object(Object(Configuration,TEXT("head_equipment")),Definition.ToString());
    const auto Fit=Object(Object(Recipe,TEXT("fits")),Head.ToString());
    if(!Recipe||!Fit){ClearHeadEquipment();UpdateAppearanceVisibility();return;}
    const bool bLocalOwner=Character.IsValid()&&Character->IsLocallyControlled();
    const FString Key=Definition.ToString()+TEXT("|")+Head.ToString()+(bLocalOwner?TEXT("|owner"):TEXT("|world"));
    if(Key==HeadEquipmentKey)return;
    if(HelmetVisor){HelmetVisor->RemoveFromParent();HelmetVisor=nullptr;}
    HeadEquipmentKey=Key;const uint32 Request=++HeadEquipmentRequest;
    if(HeadEquipmentLoad){HeadEquipmentLoad->CancelHandle();HeadEquipmentLoad.Reset();}
    const FString SkeletalPath=Text(Recipe,TEXT("skeletal_mesh")),StaticPath=Text(Recipe,TEXT("static_mesh"));
    const FString Path=SkeletalPath.IsEmpty()?StaticPath:SkeletalPath;
    if(Path.IsEmpty())return;
    const FString VisorPath=Character.IsValid()&&Character->IsLocallyControlled()
        ?Text(Recipe,TEXT("first_person_overlay")):FString();
    TArray<FSoftObjectPath> Assets{FSoftObjectPath(Path)};
    if(!VisorPath.IsEmpty())Assets.Add(FSoftObjectPath(VisorPath));
    HeadEquipmentLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets,
        FStreamableDelegate::CreateWeakLambda(this,[this,Request,Recipe,Fit,Path,SkeletalPath,VisorPath]()
    {
        if(Request!=HeadEquipmentRequest)return;
        auto* Parent=GetBodyMesh();if(!Parent)return;
        UMeshComponent* Part=nullptr;
        if(!SkeletalPath.IsEmpty())
        {
            if(auto* Mesh=Cast<USkeletalMesh>(FSoftObjectPath(Path).ResolveObject()))
            {auto* Dynamic=NewObject<UFPSHeadEquipmentMeshComponent>(GetOwner(),NAME_None,RF_Transient);Dynamic->SetSkinnedAssetAndUpdate(Mesh);Part=Dynamic;}
        }
        else if(auto* Mesh=Cast<UStaticMesh>(FSoftObjectPath(Path).ResolveObject()))
        {auto* Static=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);Static->SetStaticMesh(Mesh);Part=Static;}
        if(!Part){UE_LOG(LogTemp,Warning,TEXT("Head equipment unavailable: %s"),*Path);HeadEquipmentLoad.Reset();return;}
        const FString Bone=Text(Recipe,TEXT("attach_bone"));
        GetOwner()->AddInstanceComponent(Part);Part->ComponentTags.Add(TEXT("HeadEquipment"));
        Part->SetupAttachment(Parent,Bone.IsEmpty()?FName(TEXT("head")):FName(*Bone));
        const FVector Location=Vector(Fit,TEXT("location"),FVector::ZeroVector);
        const FVector Rotation=Vector(Fit,TEXT("rotation"),FVector::ZeroVector);
        const FVector Scale=Vector(Fit,TEXT("scale"),FVector::OneVector);
        Part->SetRelativeTransform(FTransform(FRotator(Rotation.X,Rotation.Y,Rotation.Z),Location,Scale));
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetGenerateOverlapEvents(false);Part->SetVisibility(false);
        Part->RegisterComponent();Part->AddTickPrerequisiteComponent(Parent);
        if(auto* Dynamic=Cast<UFPSHeadEquipmentMeshComponent>(Part))
        {
            TArray<FName> Bones;const TArray<TSharedPtr<FJsonValue>>* Names=nullptr;
            if(Recipe->TryGetArrayField(TEXT("tip_bones"),Names))for(const auto& Name:*Names)Bones.Add(FName(*Name->AsString()));
            Dynamic->ConfigureTip(Bones,Number(Recipe,TEXT("tip_limit_degrees"),10.f),Number(Recipe,TEXT("tip_frequency_hz"),2.5f),Number(Recipe,TEXT("tip_damping"),.6f));
        }
        if(HeadEquipment)HeadEquipment->DestroyComponent();HeadEquipment=Part;
        bHeadEquipmentCoversHair=false;Recipe->TryGetBoolField(TEXT("covers_scalp_hair"),bHeadEquipmentCoversHair);
        if(!VisorPath.IsEmpty()&&Character.IsValid()&&Character->IsLocallyControlled())
        {
            auto* PC=Cast<APlayerController>(Character->GetController());
            auto* Texture=Cast<UTexture2D>(FSoftObjectPath(VisorPath).ResolveObject());
            if(PC&&Texture)
            {
                HelmetVisor=CreateWidget<UFPSHelmetVisorWidget>(PC);
                if(HelmetVisor){HelmetVisor->Configure(this,Texture);HelmetVisor->AddToPlayerScreen(15);}
            }
        }
        HeadEquipmentLoad.Reset();UpdateAppearanceVisibility();
    }));
}
