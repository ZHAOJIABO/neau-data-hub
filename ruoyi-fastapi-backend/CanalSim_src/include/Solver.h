#pragma once
#include <vector>
#include <string>

namespace CanalSim {

class Channel;

struct SolverConfig {
    double theta = 0.5;       // 注意: 当前 Kinematic Wave 求解器不使用此参数
    double tolerance = 1e-6; // 迭代收敛容差 (面积增量最大值)
    int max_iterations = 100;
};

class Solver {
public:
    explicit Solver(const SolverConfig& cfg);
    bool solveStep(Channel& ch, double dt);
    std::string getLastError() const { return lastError_; }

private:
    int nx_;
    SolverConfig cfg_;
    std::string lastError_;
};

} // namespace CanalSim
