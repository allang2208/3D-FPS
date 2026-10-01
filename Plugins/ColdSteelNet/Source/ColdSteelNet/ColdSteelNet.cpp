#include "Modules/ModuleManager.h"
#include "ColdSteelNetLog.h"
#include "Skills/ColdSteelSkillRules.h"
#include "ColdSteelNetChannelComponent.h"

DEFINE_LOG_CATEGORY(LogColdSteelNet);

namespace
{
    ColdSteelSkills::FColdSteelNetHitForward PreviousForward = nullptr;

    bool HitForwardImpl(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot)
    {
        return UColdSteelNetChannelComponent::ForwardHitStatic(Shooter, Hit, Damage, Direction, Shot);
    }
}

class FColdSteelNetModule : public IModuleInterface
{
public:
    virtual void StartupModule() override
    {
        // M3：把客户端命中转发注册进游戏模块的公共汇入点（ApplyHit）。
        PreviousForward = ColdSteelSkills::NetHitForward();
        ColdSteelSkills::NetHitForward() = &HitForwardImpl;
        UE_LOG(LogColdSteelNet, Log, TEXT("ColdSteelNet: combat hit forward registered"));
    }

    virtual void ShutdownModule() override
    {
        if (ColdSteelSkills::NetHitForward() == &HitForwardImpl)
        {
            ColdSteelSkills::NetHitForward() = PreviousForward;
        }
    }
};

IMPLEMENT_MODULE(FColdSteelNetModule, ColdSteelNet);
