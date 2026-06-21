#include "Channel.h"
#include "Solver.h"
#include "Output.h"
#include "ConfigIO.h"

#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace CanalSim;

static void printUsage(const char* prog) {
    std::cout << "Usage: " << prog << " <input.json> <output.json>\n"
              << "\n"
              << "  <input.json>   simulation config (channel / solver / branches)\n"
              << "  <output.json>  result file with summary / timeseries / final_state / branches\n"
              << "\n"
              << "Run 'python python/canalsim_client.py' for a Python wrapper.\n";
}

static void printHeader() {
    std::cout << "==================================================\n";
    std::cout << "  CanalSim v1.1 - 1D Open Channel Flow Solver\n";
    std::cout << "  Kinematic Wave, implicit linearized finite differences\n";
    std::cout << "  CLI mode: <input.json> -> <output.json>\n";
    std::cout << "==================================================\n\n";
}

static void printConfigEcho(const ChannelConfig& cfg,
                            const SolverConfig& solver,
                            const std::vector<BranchConfig>& branches) {
    std::cout << "  Channel parameters:\n";
    std::cout << "    Length L = " << cfg.L << " m\n";
    std::cout << "    Nodes nx = " << cfg.nx << "\n";
    std::cout << "    dx = " << cfg.L / (cfg.nx - 1) << " m\n";
    std::cout << "    Bottom width b = " << cfg.b << " m\n";
    std::cout << "    Side slope m = " << cfg.m << "\n";
    std::cout << "    Manning n = " << cfg.n_Manning << "\n";
    std::cout << "    Bed slope S0 = " << cfg.S0 << "\n";
    std::cout << "    Upstream Q_in = " << cfg.Q_upstream << " m3/s\n";
    std::cout << "    Initial Q_0 = "
              << (cfg.Q_initial > 0 ? cfg.Q_initial : cfg.Q_upstream)
              << " m3/s\n";
    std::cout << "    Total time tf = " << cfg.tf << " s\n";
    std::cout << "    Time step dt = " << cfg.dt << " s\n\n";

    std::cout << "  Solver: Kinematic Wave, tolerance="
              << solver.tolerance
              << ", max_iterations=" << solver.max_iterations << "\n\n";

    if (branches.empty()) {
        std::cout << "  Branch canals: (none)\n\n";
    } else {
        std::cout << "  Branch canals (lateral offtakes):\n";
        double total = 0.0;
        for (const auto& br : branches) {
            std::cout << "    x=" << br.x_position << " m, Q_offtake="
                      << br.Q_offtake << " m3/s\n";
            total += br.Q_offtake;
        }
        std::cout << "  Total offtake: " << total << " m^3/s\n\n";
    }
}

static void printFinalResults(const Channel& ch, double t) {
    std::cout << "\n\n  Simulation complete! Final time t = "
              << std::fixed << std::setprecision(2) << t << " s\n";
    std::cout << "  ===============================================\n";
    std::cout << "  Cross-section data (x, y, A, Q, V, Fr):\n";
    std::cout << "  " << std::string(70, '-') << "\n";
    std::cout << "  " << std::setw(8) << "x(m)" << " " << std::setw(8) << "y(m)"
              << " " << std::setw(10) << "A(m2)" << " " << std::setw(10) << "Q(m3/s)"
              << " " << std::setw(8) << "V(m/s)" << " " << std::setw(8) << "Fr\n";
    std::cout << "  " << std::string(70, '-') << "\n";

    int printEvery = std::max(1, ch.nx / 10);
    for (int i = 0; i < ch.nx; i += printEvery) {
        std::cout << "  " << std::setw(8) << std::setprecision(2) << ch.cells[i].x << " "
                  << std::setw(8) << std::setprecision(4) << ch.cells[i].y << " "
                  << std::setw(10) << std::setprecision(4) << ch.cells[i].A << " "
                  << std::setw(10) << std::setprecision(4) << ch.cells[i].Q << " "
                  << std::setw(8) << std::setprecision(4) << ch.cells[i].V << " "
                  << std::setw(8) << std::setprecision(4) << ch.cells[i].Fr << "\n";
    }
    int last = ch.nx - 1;
    std::cout << "  " << std::setw(8) << std::setprecision(2) << ch.cells[last].x << " "
              << std::setw(8) << std::setprecision(4) << ch.cells[last].y << " "
              << std::setw(10) << std::setprecision(4) << ch.cells[last].A << " "
              << std::setw(10) << std::setprecision(4) << ch.cells[last].Q << " "
              << std::setw(8) << std::setprecision(4) << ch.cells[last].V << " "
              << std::setw(8) << std::setprecision(4) << ch.cells[last].Fr << "\n";
    std::cout << "  " << std::string(70, '-') << "\n";
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printUsage(argv[0]);
        return 1;
    }

    const std::string inputPath  = argv[1];
    const std::string outputPath = argv[2];

    SimulationConfig simCfg;
    try {
        simCfg = ConfigIO::load(inputPath);
    } catch (const std::exception& e) {
        std::cerr << "Error loading config: " << e.what() << "\n";
        return 2;
    }

    // 注入支渠到 ChannelConfig
    for (const auto& br : simCfg.branches) {
        simCfg.channel.branches.addBranch(br);
    }

    printHeader();
    printConfigEcho(simCfg.channel, simCfg.solver, simCfg.branches);

    Channel ch(simCfg.channel);
    ch.initialize();
    Solver solver(simCfg.solver);
    Output output;

    const double dt = ch.cfg.dt;
    const double tf = ch.cfg.tf;
    const int totalSteps = static_cast<int>(tf / dt);
    const int printInterval  = std::max(1, totalSteps / 20);
    const int snapshotEvery   = std::max(1, totalSteps / 60); // ~60 snapshots for 3D

    std::cout << "  Total steps: " << totalSteps << "\n";
    std::cout << "  Starting simulation...\n\n";

    auto startTime = std::chrono::high_resolution_clock::now();

    for (int step = 0; step <= totalSteps; ++step) {
        const double t = step * dt;

        ch.applyBoundaryConditions(t);

        if (step > 0) {
            if (!solver.solveStep(ch, dt)) {
                std::cerr << "\n  Warning: Solver failed at step " << step
                          << " (" << solver.getLastError() << "), continuing...\n";
            }
        }

        if (step % printInterval == 0 || step == totalSteps) {
            output.printProgress(ch, t);
        }

        // timeseries: every step (for accurate Q/y plots)
        output.recordTimeSeries(ch, t);

        // spacetime snapshots: sampled at intervals (for 3D surface plots)
        if (step % snapshotEvery == 0) {
            output.recordSnapshot(ch, t, step, snapshotEvery);
        }
    }

    auto endTime = std::chrono::high_resolution_clock::now();
    const double elapsed = std::chrono::duration<double>(endTime - startTime).count();

    std::cout << "\n\n";

    printFinalResults(ch, tf);

    std::cout << "  Branch locations (x): ";
    for (const auto& br : ch.cfg.branches.branches()) {
        std::cout << br.x_position << " ";
    }
    std::cout << "\n\n  Elapsed: " << std::fixed << std::setprecision(2)
              << elapsed << " s\n";

    // 序列化结果
    ConfigIO::TimeSeries ts;
    ts.t            = output.times();
    ts.Q_upstream   = output.upstreamQ();
    ts.Q_downstream = output.downstreamQ();
    ts.y_upstream   = output.upstreamY();
    ts.y_downstream = output.downstreamY();

    ConfigIO::SpacetimeSnapshot st;
    st.times             = output.snapshotTimes();
    st.waterLevelMatrix  = output.waterLevelMatrix();
    st.flowRateMatrix    = output.flowRateMatrix();
    st.nx                = output.snapshotNx();
    st.n_steps           = output.snapshotNSteps();

    try {
        ConfigIO::saveResult(outputPath, ch, simCfg.branches, ts, elapsed, st);
        std::cout << "  Result written to: " << outputPath << "\n";
    } catch (const std::exception& e) {
        std::cerr << "Error writing result: " << e.what() << "\n";
        return 3;
    }

    std::cout << "==================================================\n";
    return 0;
}
