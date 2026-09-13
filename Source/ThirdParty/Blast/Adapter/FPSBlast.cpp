#include "FPSBlast.h"
#include "stress.h"
#include <vector>
#include <cstring>

bool FPSBlastSolve(const FPSBlastNode* input, uint32_t count, const FPSBlastBond* inputBonds,
    uint32_t bondCount, uint32_t iterations, FPSBlastForce* forces)
{
    if (!count || !bondCount) return true;
    std::vector<SolverNodeS> nodes(count);
    std::vector<SolverBond> bonds(bondCount);
    // C++17 std::allocator supports these over-aligned 32-byte elements.
    std::vector<AngLin6> velocity(count), impulse(bondCount);
    for (uint32_t i=0; i<count; ++i)
    {
        const auto& src=input[i];
        nodes[i]={{src.position[0],src.position[1],src.position[2]},src.mass,src.inertia};
        velocity[i].ang={0,0,0};
        velocity[i].lin={src.acceleration[0],src.acceleration[1],src.acceleration[2]};
    }
    for (uint32_t i=0; i<bondCount; ++i)
    {
        const auto& src=inputBonds[i];
        bonds[i]={{src.centroid[0],src.centroid[1],src.centroid[2]},{src.nodes[0],src.nodes[1]}};
    }
    StressProcessor solver;
    StressProcessor::DataParams data;
    // Preserve the actual mass distribution and partial-face lever arms.
    solver.prepare(nodes.data(),count,bonds.data(),bondCount,data);
    StressProcessor::SolverParams params;
    params.maxIter=iterations; params.tolerance=0.001f;
    const bool converged=solver.solve(impulse.data(),velocity.data(),params)>=0;
    for (uint32_t i=0; i<bondCount; ++i)
    {
        std::memcpy(forces[i].linear,&impulse[i].lin.x,3*sizeof(float));
        std::memcpy(forces[i].angular,&impulse[i].ang.x,3*sizeof(float));
    }
    return converged;
}
