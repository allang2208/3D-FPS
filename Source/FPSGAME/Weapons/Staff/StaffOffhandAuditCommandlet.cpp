#include "StaffOffhandAuditCommandlet.h"
#include "../Kukri/KukriArmsMeshComponent.h"
#include "../Kukri/KukriOffhandDraw.h"
#include "../Kukri/KukriRhythm.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

int32 UStaffOffhandAuditCommandlet::Main(const FString& Params)
{
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,KukriRhythm::ArmsMesh);
    const auto Clip=[](const TCHAR* Name)
    {return LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+Name+TEXT(".")+Name));};
    auto* Spin=Clip(TEXT("A_Kukri_Whirlwind"));
    auto* Idle=Clip(TEXT("A_Kukri_DualIdle"));
    auto* Equip=Clip(TEXT("A_Kukri_DualEquip"));
    if(!Mesh||!Spin||!Idle||!Equip)return 2;
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Init);
    auto* Owner=World->SpawnActor<AActor>();
    const auto MakeArms=[&](bool Mirrored)
    {
        auto* Arms=NewObject<UKukriArmsMeshComponent>(Owner);
        Owner->AddInstanceComponent(Arms);Arms->SetSkeletalMesh(Mesh);
        Arms->bLeftHandOnly=Mirrored;Arms->bMirrorRightToLeft=Mirrored;
        Arms->RegisterComponent();Arms->SetComponentTickEnabled(false);
        Arms->PlayAnimation(Spin,false);Arms->SetPlayRate(0.f);return Arms;
    };
    auto* Right=MakeArms(false);auto* Left=MakeArms(true);
    const auto Sample=[](UKukriArmsMeshComponent* Arms,float Time)
    {Arms->SetPosition(Time,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();};
    const auto Reflect=[](FVector P){P.X=-P.X;return P;};
    const auto& Ref=Mesh->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)
    {const int32 Parent=Ref.GetParentIndex(I);if(Parent>=0)Bind[I]=Bind[I]*Bind[Parent];}
    const int32 CL=Ref.FindBoneIndex(TEXT("clavicle_l")),CR=Ref.FindBoneIndex(TEXT("clavicle_r"));
    const int32 Hand=Ref.FindBoneIndex(TEXT("hand_l")),Weapon=Ref.FindBoneIndex(TEXT("WPN_root"));
    if(CL<0||CR<0||Hand<0||Weapon<0)return 2;
    const FVector Offset=Bind[CL].GetLocation()-Reflect(Bind[CR].GetLocation());
    double BoneError=0.,LengthError=0.,TipError=0.,ScaleError=0.;FName WorstBone;
    const int32 Frames=FMath::CeilToInt(Spin->GetPlayLength()*120.f);
    for(int32 F=0;F<=Frames;++F)
    {
        const float T=Spin->GetPlayLength()*float(F)/Frames;Sample(Right,T);Sample(Left,T);
        const auto& R=Right->GetComponentSpaceTransforms();const auto& L=Left->GetComponentSpaceTransforms();
        for(int32 I=0;I<Ref.GetNum();++I)
        {
            if(I!=CL&&!Ref.BoneIsChildOf(I,CL))continue;
            const FString Name=Ref.GetBoneName(I).ToString();
            const int32 RI=Name.EndsWith(TEXT("_l"))?Ref.FindBoneIndex(FName(Name.LeftChop(2)+TEXT("_r"))):INDEX_NONE;
            if(RI<0)continue;
            const double Error=FVector::Dist(L[I].GetLocation(),Reflect(R[RI].GetLocation())+Offset);
            if(Error>BoneError){BoneError=Error;WorstBone=Ref.GetBoneName(I);}
            const int32 Parent=Ref.GetParentIndex(I);
            if(I!=CL&&Parent>=0)
                LengthError=FMath::Max(LengthError,FMath::Abs(FVector::Dist(L[I].GetLocation(),L[Parent].GetLocation())-
                    FVector::Dist(Bind[I].GetLocation(),Bind[Parent].GetLocation())));
            ScaleError=FMath::Max(ScaleError,FVector::Dist(L[I].GetScale3D(),Bind[I].GetScale3D()));
        }
        FTransform RK=R[Weapon];RK.SetScale3D(FVector::OneVector);
        const FTransform LK=KukriOffhandDraw::Grip()*L[Hand];
        TipError=FMath::Max(TipError,FVector::Dist(LK.TransformPosition(KukriRhythm::BladeTip),
            Reflect(RK.TransformPosition(KukriRhythm::BladeTip))+Offset));
    }
    // Entry and cancellation must begin on the last displayed left pose, even though the donor right chain is collapsed.
    const auto Transition=[&](UAnimSequence* From,bool MirrorFrom,UAnimSequence* To,bool MirrorTo,float Time)
    {
        Left->ClearEntry();Left->bMirrorRightToLeft=MirrorFrom;Left->PlayAnimation(From,false);Left->SetPlayRate(0.f);
        Sample(Left,Time);const auto Before=Left->GetComponentSpaceTransforms();
        Left->CaptureLeftEntry(.18f);Left->bMirrorRightToLeft=MirrorTo;
        Left->PlayAnimation(To,false);Left->SetPlayRate(0.f);Sample(Left,0.f);
        double Error=0.;const auto& After=Left->GetComponentSpaceTransforms();
        for(int32 I=0;I<Ref.GetNum();++I)if(I==CL||Ref.BoneIsChildOf(I,CL))
            Error=FMath::Max(Error,FVector::Dist(Before[I].GetLocation(),After[I].GetLocation()));
        return Error;
    };
    const double Entry=Transition(Idle,false,Spin,true,.37f);
    const double Cancel=Transition(Spin,true,Idle,false,.93f);
    const double Finish=Transition(Spin,true,Idle,false,Spin->GetPlayLength());
    const bool Pass=BoneError<1.&&LengthError<.01&&TipError<1.&&ScaleError<.001&&Entry<.001&&Cancel<.001&&Finish<.001;
    const FString Report=FString::Printf(TEXT("pass=%d samples=%d\nmax_mirrored_bone_error_cm=%.6f worst_bone=%s\nmax_segment_length_error_cm=%.6f\nmax_blade_tip_error_cm=%.6f\nmax_scale_error=%.6f\nentry_jump_cm=%.6f\ncancel_jump_cm=%.6f\nfinish_jump_cm=%.6f\n"),
        Pass,Frames+1,BoneError,*WorstBone.ToString(),LengthError,TipError,ScaleError,Entry,Cancel,Finish);
    FString Output;FParse::Value(*Params,TEXT("Report="),Output);
    if(Output.IsEmpty())Output=FPaths::ProjectSavedDir()/TEXT("StaffOffhandPoseAudit.txt");
    FFileHelper::SaveStringToFile(Report,*Output);UE_LOG(LogTemp,Display,TEXT("STAFF_OFFHAND_AUDIT %s"),*Report);
    Owner->Destroy();World->DestroyWorld(false);return Pass?0:1;
}
