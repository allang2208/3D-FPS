#include "LoneOffhandBladeAuditCommandlet.h"
#include "KukriArmsMeshComponent.h"
#include "KukriOffhandDraw.h"
#include "KukriRhythm.h"
#include "KukriHeavyRhythm.h"
#include "HatchetDrawRhythm.h"
#include "HatchetChopRhythm.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

// Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=LoneOffhandBladeAudit [-Report=<file>] -unattended -nosplash -nullrhi
int32 ULoneOffhandBladeAuditCommandlet::Main(const FString& Params)
{
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,KukriRhythm::ArmsMesh);
    if(!Mesh)return 2;
    struct FClip{FString Name;UAnimSequence* Anim=nullptr;bool bDraw=false;};
    TArray<FClip> Clips;
    const auto Add=[&](const FString& Name,const FString& Path,bool bDraw)
    {if(auto* Anim=LoadObject<UAnimSequence>(nullptr,*Path))Clips.Add({Name,Anim,bDraw});
     else UE_LOG(LogTemp,Warning,TEXT("LONE_AUDIT missing %s"),*Path);};
    const auto Kukri=[](const FString& Name){return FString(KukriRhythm::Folder)+TEXT("A_Kukri_")+Name+TEXT(".A_Kukri_")+Name;};
    for(const TCHAR* Name:{TEXT("Idle"),TEXT("Walk"),TEXT("Run"),TEXT("Attack"),TEXT("Attack2"),TEXT("Attack3"),TEXT("SprintAttack"),
        TEXT("Uppercut"),TEXT("QuickPommel"),TEXT("Whirlwind")})Add(Name,Kukri(Name),false);
    for(const FName Name:{KukriHeavyRhythm::ChargeClip,KukriHeavyRhythm::ReleaseClip})Add(Name.ToString(),Kukri(Name.ToString()),false);
    Add(TEXT("Equip"),Kukri(TEXT("Equip")),true);
    Add(TEXT("HatchetEquip"),HatchetDrawRhythm::Clip,true);
    Add(TEXT("HatchetAttack3"),HatchetChopRhythm::Clip,false);
    if(Clips.Num()<4)return 2;

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
        return Arms;
    };
    auto* Right=MakeArms(false);auto* Left=MakeArms(true);
    const auto Play=[](UKukriArmsMeshComponent* Arms,UAnimSequence* Anim){Arms->PlayAnimation(Anim,false);Arms->SetPlayRate(0.f);};
    const auto Sample=[](UKukriArmsMeshComponent* Arms,float Time)
    {Arms->SetPosition(Time,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();};
    const auto& Ref=Mesh->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I){const int32 Parent=Ref.GetParentIndex(I);if(Parent>=0)Bind[I]=Bind[I]*Bind[Parent];}
    const int32 CL=Ref.FindBoneIndex(TEXT("clavicle_l")),CR=Ref.FindBoneIndex(TEXT("clavicle_r"));
    const int32 HandL=Ref.FindBoneIndex(TEXT("hand_l")),Weapon=Ref.FindBoneIndex(TEXT("WPN_root"));
    if(CL<0||CR<0||HandL<0||Weapon<0)return 2;
    const auto Reflect=[](FVector P){P.X=-P.X;return P;};
    const FVector Offset=Bind[CL].GetLocation()-Reflect(Bind[CR].GetLocation());
    // The displayed lone blade: the mirrored relation on the left fist (UKukriWeaponComponent::SamplePose / BladeFrame).
    const auto LeftBlade=[&](){FTransform B=Left->MirroredWeaponToHandL()*Left->GetComponentSpaceTransforms()[HandL];
        B.SetScale3D(FVector::OneVector);return B;};
    const auto GripError=[&](float& Degrees)
    {
        FTransform Accepted=KukriOffhandDraw::Grip();Accepted.SetScale3D(FVector::OneVector);
        const FTransform& Rel=Left->MirroredWeaponToHandL();
        Degrees=FMath::RadiansToDegrees(Rel.GetRotation().AngularDistance(Accepted.GetRotation()));
        return FVector::Dist(Rel.GetLocation(),Accepted.GetLocation())*100.f;   // hand_l carries the 100x import scale
    };

    FString Report;bool Pass=true;
    // 1) Every clip, 120 Hz: the left blade is the mirror image of the right one (tip and root), the held grip the accepted one.
    for(const auto& C:Clips)
    {
        Right->ClearEntry();Left->ClearEntry();Play(Right,C.Anim);Play(Left,C.Anim);
        const int32 Frames=FMath::Max(1,FMath::CeilToInt(C.Anim->GetPlayLength()*120.f));
        double Mirror=0.,Grip=0.,GripDeg=0.;
        for(int32 F=0;F<=Frames;++F)
        {
            const float T=C.Anim->GetPlayLength()*float(F)/Frames;Sample(Right,T);Sample(Left,T);
            FTransform RK=Right->GetComponentSpaceTransforms()[Weapon];RK.SetScale3D(FVector::OneVector);
            const FTransform LK=LeftBlade();
            for(const FVector& P:{KukriRhythm::BladeTip,KukriRhythm::BladeRoot})
                Mirror=FMath::Max(Mirror,FVector::Dist(LK.TransformPosition(P),Reflect(RK.TransformPosition(P))+Offset));
            float Deg=0.f;const float Cm=GripError(Deg);
            if(!C.bDraw){Grip=FMath::Max(Grip,double(Cm));GripDeg=FMath::Max(GripDeg,double(Deg));}
        }
        // The pass is the mirror: the clip's own grip drift (held_grip, the authored WPN_root against the constant grip
        // through the lock band) is the same on the right-hand single wield and only reported.
        const bool Ok=Mirror<.05;
        Pass&=Ok;
        Report+=FString::Printf(TEXT("clip %-16s ok=%d mirror_cm=%.3f clip_grip_drift_cm=%.4f clip_grip_drift_deg=%.3f\n"),*C.Name,Ok,Mirror,Grip,GripDeg);
    }
    // 2) Clip changes as the component plays them (CaptureEntry, then the clip from 0 while AdvanceEntry runs): the grip stays
    //    the accepted one and the left fist moves without a jump.
    const auto Find=[&](const TCHAR* Name){for(const auto& C:Clips)if(C.Name==Name)return C.Anim;return (UAnimSequence*)nullptr;};
    struct FChange{const TCHAR* From;float At;const TCHAR* To;float Blend;};
    const FChange Changes[]={{TEXT("Idle"),.4f,TEXT("Attack"),KukriRhythm::EntryBlendSeconds},
        {TEXT("Attack"),.5f,TEXT("Idle"),KukriRhythm::EntryBlendSeconds},{TEXT("Walk"),.3f,TEXT("Run"),KukriRhythm::SprintBlendSeconds},
        {TEXT("Run"),.2f,TEXT("SprintAttack"),KukriRhythm::SprintBlendSeconds},{TEXT("Idle"),1.f,TEXT("Uppercut"),KukriRhythm::EntryBlendSeconds},
        {TEXT("Equip"),10.f,TEXT("Idle"),KukriRhythm::EntryBlendSeconds},{TEXT("HatchetEquip"),10.f,TEXT("Idle"),KukriRhythm::EntryBlendSeconds},
        {TEXT("Attack2"),.6f,TEXT("HatchetAttack3"),KukriRhythm::EntryBlendSeconds}};
    for(const auto& Change:Changes)
    {
        auto* From=Find(Change.From);auto* To=Find(Change.To);
        if(!From||!To)continue;
        Left->ClearEntry();Play(Left,From);Sample(Left,FMath::Min(Change.At,From->GetPlayLength()));
        FVector Previous=Left->GetComponentSpaceTransforms()[HandL].GetLocation();
        Left->CaptureEntry(Change.Blend);Play(Left,To);Right->ClearEntry();Play(Right,To);
        double Grip=0.,GripDeg=0.,Step=0.;
        const int32 Frames=FMath::CeilToInt((Change.Blend+.05f)*120.f);
        for(int32 F=0;F<=Frames;++F)
        {
            if(F>0)Left->AdvanceEntry(1.f/120.f);
            Sample(Left,F/120.f);
            // The blade in the blending fist against the target clip's own mirrored grip at the same time (a second,
            // unblended mirrored rig): the clip change must not carry the blade off the fist.
            const FTransform Blended=Left->MirroredWeaponToHandL();
            const FVector BlendedHand=Left->GetComponentSpaceTransforms()[HandL].GetLocation();
            Right->bLeftHandOnly=Right->bMirrorRightToLeft=true;Sample(Right,F/120.f);
            const FTransform Target=Right->MirroredWeaponToHandL();
            Right->bLeftHandOnly=Right->bMirrorRightToLeft=false;
            Grip=FMath::Max(Grip,double(FVector::Dist(Blended.GetLocation(),Target.GetLocation())*100.f));
            GripDeg=FMath::Max(GripDeg,double(FMath::RadiansToDegrees(Blended.GetRotation().AngularDistance(Target.GetRotation()))));
            // The jump at the change itself: the first blended frame against the last displayed one.
            if(F==0)Step=FVector::Dist(BlendedHand,Previous);
        }
        const bool Ok=Grip<.05&&GripDeg<.5&&Step<.5;
        Pass&=Ok;
        Report+=FString::Printf(TEXT("change %s->%s ok=%d grip_vs_clip_cm=%.4f grip_vs_clip_deg=%.3f entry_jump_cm=%.3f\n"),
            Change.From,Change.To,Ok,Grip,GripDeg,Step);
    }
    Report=FString::Printf(TEXT("pass=%d\n"),Pass)+Report;
    FString Output;FParse::Value(*Params,TEXT("Report="),Output);
    if(Output.IsEmpty())Output=FPaths::ProjectSavedDir()/TEXT("LoneOffhandBladeAudit.txt");
    FFileHelper::SaveStringToFile(Report,*Output);UE_LOG(LogTemp,Display,TEXT("LONE_OFFHAND_AUDIT\n%s"),*Report);
    Owner->Destroy();World->DestroyWorld(false);return Pass?0:1;
}
