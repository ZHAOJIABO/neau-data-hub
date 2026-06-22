#pragma once
#include <string>
#include <vector>

#include "Channel.h"
#include "Solver.h"
#include "Branch.h"

namespace CanalSim {

// 聚合 Channel / Solver / Branches 三段配置
struct SimulationConfig {
    ChannelConfig  channel;
    SolverConfig   solver;
    std::vector<BranchConfig> branches;
};

// 输入 JSON -> SimulationConfig, 结果 JSON <- 模拟结果
class ConfigIO {
public:
    // 从 input.json 读入配置; 关键字段缺失时抛 std::runtime_error
    static SimulationConfig load(const std::string& path);

    // 把模拟结果 (channel final state + time series + branches) 序列化为 result.json
    // timeSeries, branches, elapsed_s 由调用方从 main 中的 Output 缓冲与计时得到
    struct TimeSeries {
        std::vector<double> t;            // 时间序列 (s)
        std::vector<double> Q_upstream;   // 上游流量
        std::vector<double> Q_downstream; // 下游流量
        std::vector<double> y_upstream;   // 上游水位
        std::vector<double> y_downstream; // 下游水位
    };

    // 时空快照矩阵（由 Output.recordSnapshot 定期采集）
    struct SpacetimeSnapshot {
        std::vector<double> times;             // 各快照时刻 (s)
        std::vector<double> waterLevelMatrix;   // [nSteps][nx] 水深矩阵, 展平
        std::vector<double> flowRateMatrix;     // [nSteps][nx] 流量矩阵, 展平
        int nx = 0;                             // 每个快照的节点数
        int n_steps = 0;                        // 快照数量
    };

    static void saveResult(const std::string& path,
                           const Channel& ch,
                           const std::vector<BranchConfig>& branches,
                           const TimeSeries& ts,
                           double elapsed_s,
                           const SpacetimeSnapshot& spacetime);
};

}
