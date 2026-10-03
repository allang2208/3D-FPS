#include "MonsterCorpsePoseAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"

struct FMonsterCorpsePoseProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Pose;
    explicit FMonsterCorpsePoseProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance)
    {
        Pose.Mode = ESnapshotSourceMode::SnapshotPin;
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &Pose; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override { Nodes.Add(&Pose); }
    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        Pose.Snapshot = CastChecked<UMonsterCorpsePoseAnimInstance>(Instance)->FrozenPose;
    }
};

FAnimInstanceProxy* UMonsterCorpsePoseAnimInstance::CreateAnimInstanceProxy()
{
    return new FMonsterCorpsePoseProxy(this);
}
void UMonsterCorpsePoseAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy)
{
    delete Proxy;
}
