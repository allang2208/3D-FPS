#include "ProductionToolComponent.h"
#include "ProductionPickaxeImpactMotion.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
struct FToolElectricAnchor {FVector Base=FVector::ZeroVector,Tip=FVector::ZeroVector;};
TMap<FString,FToolElectricAnchor> ElectricAnchors;
}

void UProductionToolComponent::LoadEnchantmentAnchors()
{
    static bool bLoaded=false;if(bLoaded)return;bLoaded=true;
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/electrified-tool-anchors.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return;
    for(const auto& Entry:Root->Values)
    {
        const auto Data=Entry.Value->AsObject();if(!Data)continue;
        const TArray<TSharedPtr<FJsonValue>> *Base=nullptr,*Tip=nullptr;
        if(Data->TryGetArrayField(TEXT("base_local"),Base)&&Data->TryGetArrayField(TEXT("tip_local"),Tip)&&Base->Num()==3&&Tip->Num()==3)
        {
            FToolElectricAnchor Anchor;
            Anchor.Base=FVector((*Base)[0]->AsNumber(),(*Base)[1]->AsNumber(),(*Base)[2]->AsNumber());
            Anchor.Tip=FVector((*Tip)[0]->AsNumber(),(*Tip)[1]->AsNumber(),(*Tip)[2]->AsNumber());
            ElectricAnchors.Add(FString(*Entry.Key),Anchor);
        }
    }
}

static TAutoConsoleVariable<float> PickaxeImpactCameraScale(TEXT("fps.Tool.PickaxeCamera"),1.f,
    TEXT("Pickaxe windup and single heavy confirmed-impact camera strength. 0 disables this camera layer."));

bool UProductionToolComponent::HasReadyPresentation() const
{
    if(!bUsesArms)return ToolMesh && ToolMesh->GetStaticMesh();
    if(!Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return false;
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Swing"),TEXT("HitRecover")})
        if(((Kind!=TEXT("axe") && Kind!=TEXT("pickaxe")) || FName(Clip)!=TEXT("Walk")) && !Motions.FindRef(FName(Clip)))return false;
    return true;
}

bool UProductionToolComponent::GetEnchantmentBladeAttachment(USceneComponent*& Parent,FName& Socket,FTransform& LocalFrame,float& Length) const
{
    if(!IsEquipped()||!Viewmodel||!Viewmodel->IsVisible()||Viewmodel->bHiddenInGame||!Viewmodel->DoesSocketExist(TEXT("WPN_root")))return false;
    // Derived from the imported rigid tool vertices; cached before combat begins.
    const auto* Anchor=ElectricAnchors.Find(Kind);if(!Anchor)return false;
    const FTransform Weapon=Viewmodel->GetSocketTransform(TEXT("WPN_root"));
    const FVector Base=Weapon.TransformPosition(Anchor->Base),Tip=Weapon.TransformPosition(Anchor->Tip);
    Length=FVector::Distance(Base,Tip);if(Length<1.f)return false;
    const FTransform WorldFrame(FRotationMatrix::MakeFromXZ(Tip-Base,Weapon.GetUnitAxis(EAxis::Z)).ToQuat(),Base);
    Parent=Viewmodel;Socket=TEXT("WPN_root");LocalFrame=WorldFrame.GetRelativeTransform(Weapon);
    return true;
}

void UProductionToolComponent::SampleMotion(FName Clip,float Seconds)
{
    UAnimSequence* Motion=Motions.FindRef(Clip);
    if(!Motion || !Viewmodel)return;
    if(CurrentMotion!=Motion)
    {
        CurrentMotion=Motion;
        Viewmodel->PlayAnimation(Motion,false);
        Viewmodel->SetPlayRate(0.f);
    }
    Viewmodel->SetPosition(FMath::Clamp(Seconds,0.f,Motion->GetPlayLength()),false);
    Viewmodel->TickAnimation(0.f,false);
    Viewmodel->RefreshBoneTransforms();
}

void UProductionToolComponent::UpdateHandPresentation(float Delta)
{
    VisualTime+=Delta;
    const float Speed=Character->GetVelocity().Size2D();
    const bool bTwoHand=Kind==TEXT("axe") || Kind==TEXT("pickaxe");
    if(!bTwoHand)
    {
        const float SprintTarget=Elapsed<0 && Speed>650.f?1.f:0.f;
        SprintBlend=FMath::Lerp(SprintBlend,SprintTarget,1.f-FMath::Exp(-14.f*Delta));
        Viewmodel->SetRelativeLocation(FVector(-3,0,-6)*SprintBlend);
    }
    if(Elapsed>=0)
    {
        // Pose, whoosh and the one authoritative contact share the same clock.
        // Only a confirmed resource/enemy hit chooses braced recovery; misses follow through.
        // 挥砍速度改造只压缩真实时钟：动画仍按作者时间采样，RateScale=1 时逐帧等价。
        const float Authored=AuthoredElapsed();
        if(bHitConfirmed)
            SampleMotion(TEXT("HitRecover"),Kind==TEXT("pickaxe")?
                ProductionPickaxeImpact::SourceHitTime(Authored-ContactSeconds):
                .44f*(Authored-ContactSeconds)/(Kind==TEXT("axe")?AxeMotion.HitRecoverSeconds:SwingSeconds-ContactSeconds));
        else
            SampleMotion(TEXT("Swing"),Authored<ContactSeconds?
                .24f*Authored/ContactSeconds:.24f+.44f*(Authored-ContactSeconds)/(SwingSeconds-ContactSeconds));
    }
    else if(EquipElapsed>=0)
    {
        EquipElapsed+=Delta;
        SampleMotion(TEXT("Equip"),EquipElapsed);
        if(EquipElapsed>=Motions.FindRef(TEXT("Equip"))->GetPlayLength())
        {
            EquipElapsed=-1.f;
            if(bTwoHand)VisualTime=0.f;
        }
    }
    else
    {
        // Two-hand tools keep the fitted idle grasp at every movement speed.
        const FName Clip=!bTwoHand && Speed>20.f?TEXT("Walk"):TEXT("Idle");
        const float Duration=Motions.FindRef(Clip)->GetPlayLength();
        SampleMotion(Clip,FMath::Fmod(VisualTime,Duration));
    }
    if(bTwoHand)UpdateTwoHandLocomotion(Delta);
}

void UProductionToolComponent::GetCameraMotion(FVector& Location,FRotator& Rotation) const
{
    Location=FVector::ZeroVector; Rotation=FRotator::ZeroRotator;
    if(Elapsed<0.f||!IsEquipped()||!CanUse())return;
    // 镜头关键帧是作者秒；改造后的真实时间先换算回作者时间再采样。
    const float Authored=AuthoredElapsed();
    if(Kind==TEXT("axe"))AxeMotion.Sample(Authored,bHitConfirmed,Location,Rotation);
    else if(Kind==TEXT("pickaxe"))ProductionPickaxeImpact::SampleCamera(Authored,ContactSeconds,SwingSeconds,
        bHitConfirmed,PickaxeImpactCameraScale.GetValueOnGameThread(),Location,Rotation);
}
