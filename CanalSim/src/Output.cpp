#include "Output.h"
#include "Channel.h"

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <string>

namespace CanalSim {

Output::Output() = default;

void Output::recordTimeSeries(const Channel& ch, double t) {
    timeRecord_.push_back(t);
    upstreamY_.push_back(ch.cells[0].y);
    downstreamY_.push_back(ch.cells[ch.nx - 1].y);
    upstreamQ_.push_back(ch.cells[0].Q);
    downstreamQ_.push_back(ch.cells[ch.nx - 1].Q);
}

void Output::printProgress(const Channel& ch, double t) {
    const int barWidth = 40;
    double tPercent = (ch.cfg.tf > 0) ? t / ch.cfg.tf : 0.0;
    int filled = static_cast<int>(tPercent * barWidth);

    std::cout << "\r  ["
              << std::string(filled, '=')
              << std::string(barWidth - filled, '-') << "] "
              << std::fixed << std::setprecision(1) << tPercent * 100 << "%  "
              << "t=" << std::setprecision(1) << t << "s  "
              << "Q_up=" << std::setprecision(2) << ch.cells[0].Q << "  "
              << "Q_down=" << ch.cells[ch.nx - 1].Q << "  "
              << "y_up=" << ch.cells[0].y << "  "
              << "y_down=" << ch.cells[ch.nx - 1].y
              << std::flush;
}

void Output::recordSnapshot(const Channel& ch, double t, int step, int snapshotInterval) {
    (void)step; (void)snapshotInterval;
    if (snapshotNx_ == 0) snapshotNx_ = ch.nx;

    snapshotTimes_.push_back(t);
    for (int i = 0; i < ch.nx; ++i) {
        waterLevelMatrix_.push_back(ch.cells[i].y);
        flowRateMatrix_.push_back(ch.cells[i].Q);
    }
    snapshotNSteps_ = static_cast<int>(snapshotTimes_.size());
}

}
