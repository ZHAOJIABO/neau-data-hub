#pragma once
#include <string>
#include <vector>

#include "Branch.h"

namespace CanalSim {

class Channel;

// 内存中的时间序列 / 断面快照缓冲器.
// 不再写入任何磁盘文件, 由 ConfigIO 在 main 末尾统一序列化到 result.json.
class Output {
public:
    Output();

    // 每个时间步调用一次: 追加当前时刻上下游状态
    void recordTimeSeries(const Channel& ch, double t);

    // 定期调用: 保存全渠道快照 (用于 result.json 中的 spacetime 字段)
    // 每隔 snapshotInterval 步保存一次, 只记录 y 和 Q 两个矩阵
    void recordSnapshot(const Channel& ch, double t, int step, int snapshotInterval);

    // 控制台进度条
    void printProgress(const Channel& ch, double t);

    // getters
    const std::vector<double>& times()         const { return timeRecord_; }
    const std::vector<double>& upstreamY()     const { return upstreamY_; }
    const std::vector<double>& downstreamY()   const { return downstreamY_; }
    const std::vector<double>& upstreamQ()     const { return upstreamQ_; }
    const std::vector<double>& downstreamQ()   const { return downstreamQ_; }

    // spacetime getters (may be empty if no snapshots recorded)
    const std::vector<double>& snapshotTimes() const { return snapshotTimes_; }
    const std::vector<double>& waterLevelMatrix() const { return waterLevelMatrix_; }
    const std::vector<double>& flowRateMatrix() const { return flowRateMatrix_; }
    int snapshotNx() const { return snapshotNx_; }
    int snapshotNSteps() const { return snapshotNSteps_; }

private:
    std::vector<double> timeRecord_;
    std::vector<double> upstreamY_, downstreamY_;
    std::vector<double> upstreamQ_, downstreamQ_;

    // spacetime snapshots (sampled at intervals)
    std::vector<double> snapshotTimes_;
    std::vector<double> waterLevelMatrix_;  // [nSteps][nx] flattened
    std::vector<double> flowRateMatrix_;    // [nSteps][nx] flattened
    int snapshotNx_ = 0;
    int snapshotNSteps_ = 0;
};

}

