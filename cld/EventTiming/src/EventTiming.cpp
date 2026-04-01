/**
 * Per-event per-algorithm timing for Gaudi/k4FWCore pipelines.
 *
 * EventTimingAuditor  - records wall-clock time around every algorithm execute()
 * EventTimingWriter   - collects the recorded times and writes a "timing" TTree
 *
 * During execute(), timing data is written to a temporary ROOT file.
 * At finalize() — which runs AFTER PodioOutput has closed the main file
 * (Gaudi finalizes in reverse TopAlg order) — the timing TTree is merged
 * into the main output file if MergeInto is set.
 *
 * Usage:  see --enableTimings flag in CLDReconstruction.py
 */

#include "Gaudi/Auditor.h"
#include "GaudiKernel/Algorithm.h"
#include "GaudiKernel/EventContext.h"
#include "GaudiKernel/StatusCode.h"

#include "TFile.h"
#include "TTree.h"

#include <chrono>
#include <cstdio>
#include <map>
#include <memory>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Shared timing store (single-threaded Gaudi only)
// ---------------------------------------------------------------------------
namespace {
struct TimingStore {
  std::map<std::string, std::chrono::steady_clock::time_point> start_times;
  std::map<std::string, double> current_event;  // algo name -> wall ms
  std::vector<std::string> algo_order;
  bool order_locked = false;
};

TimingStore& store() {
  static TimingStore s;
  return s;
}
}  // namespace

// ---------------------------------------------------------------------------
// Auditor – hooks into every algorithm's execute()
// ---------------------------------------------------------------------------
class EventTimingAuditor : public Gaudi::Auditor {
public:
  using Gaudi::Auditor::Auditor;

  void before(const std::string& evt_type, const std::string& caller,
              const EventContext& /*ctx*/) override {
    if (evt_type != "Execute") return;
    store().start_times[caller] = std::chrono::steady_clock::now();
  }

  void after(const std::string& evt_type, const std::string& caller,
             const EventContext& /*ctx*/,
             const StatusCode& /*sc*/) override {
    if (evt_type != "Execute") return;
    auto end = std::chrono::steady_clock::now();
    auto& s  = store();
    auto  it = s.start_times.find(caller);
    if (it != s.start_times.end()) {
      s.current_event[caller] =
          std::chrono::duration<double, std::milli>(end - it->second).count();
      if (!s.order_locked) {
        s.algo_order.push_back(caller);
      }
    }
  }
};

DECLARE_COMPONENT(EventTimingAuditor)

// ---------------------------------------------------------------------------
// Writer – collects timing per event and writes a ROOT TTree
// ---------------------------------------------------------------------------
class EventTimingWriter : public Gaudi::Algorithm {
public:
  EventTimingWriter(const std::string& name, ISvcLocator* svcLoc)
      : Gaudi::Algorithm(name, svcLoc) {
    declareProperty("OutputFile", m_filename = "timing_tmp.root",
                    "Temporary ROOT file for timing data during execution");
    declareProperty("MergeInto", m_mergeFile = "",
                    "Main output ROOT file to merge timing TTree into at finalize. "
                    "If empty, timing stays in OutputFile.");
  }

  StatusCode initialize() override {
    return Gaudi::Algorithm::initialize();
  }

  StatusCode execute(const EventContext& /*ctx*/) const override {
    auto& s = store();

    // First event: lock order, create file/tree/branches
    if (!s.order_locked) {
      s.order_locked = true;
      setupTree(s);
    }

    // Fill branch values
    for (size_t i = 0; i < s.algo_order.size(); ++i) {
      auto it = s.current_event.find(s.algo_order[i]);
      m_values[i] = (it != s.current_event.end()) ? it->second : -1.0;
    }
    m_event_num++;
    m_tree->Fill();

    s.current_event.clear();
    return StatusCode::SUCCESS;
  }

  StatusCode finalize() override {
    // Write and close the temporary timing file
    if (m_file) {
      m_file->cd();
      m_tree->Write();
      m_file->Close();
      m_file.reset();
    }

    // Merge into main output file if requested
    // EventTimingWriter must be AFTER PodioOutput in algList so that
    // Gaudi finalizes it after PodioOutput has closed the file
    bool merged = false;
    if (!m_mergeFile.empty()) {
      auto* src = TFile::Open(m_filename.c_str(), "READ");
      if (src && !src->IsZombie()) {
        auto* srcTree = src->Get<TTree>("timing");
        if (srcTree) {
          auto* dst = TFile::Open(m_mergeFile.c_str(), "UPDATE");
          if (dst && !dst->IsZombie()) {
            dst->cd();
            auto* clone = srcTree->CloneTree();
            clone->Write();
            dst->Close();
            merged = true;
            info() << "Merged timing TTree into " << m_mergeFile << endmsg;
          } else {
            warning() << "Could not open " << m_mergeFile
                      << " for UPDATE — timing kept in " << m_filename << endmsg;
          }
        }
        src->Close();
      }
      if (merged) std::remove(m_filename.c_str());
    } else {
      info() << "Wrote timing data to " << m_filename << endmsg;
    }

    auto& s = store();
    info() << "=== EventTimings branch mapping ===" << endmsg;
    for (size_t i = 0; i < s.algo_order.size(); ++i) {
      info() << "  " << s.algo_order[i] << endmsg;
    }
    return Gaudi::Algorithm::finalize();
  }

private:
  void setupTree(const TimingStore& s) const {
    info() << "=== EventTimings branch mapping ===" << endmsg;
    for (size_t i = 0; i < s.algo_order.size(); ++i) {
      info() << "  [" << i << "] " << s.algo_order[i] << endmsg;
    }

    m_file.reset(TFile::Open(m_filename.c_str(), "RECREATE"));
    m_tree = new TTree("timing", "Per-event per-algorithm wall time (ms)");

    m_values.resize(s.algo_order.size(), 0.0);
    m_event_num = 0;
    m_tree->Branch("event", &m_event_num, "event/I");

    for (size_t i = 0; i < s.algo_order.size(); ++i) {
      std::string bname = s.algo_order[i];
      for (auto& c : bname) {
        if (!std::isalnum(c) && c != '_') c = '_';
      }
      m_tree->Branch(bname.c_str(), &m_values[i],
                     (bname + "/D").c_str());
    }
  }

  std::string m_filename;
  std::string m_mergeFile;
  mutable std::unique_ptr<TFile> m_file;
  mutable TTree* m_tree = nullptr;        // owned by m_file
  mutable std::vector<double> m_values;
  mutable int m_event_num = 0;
};

DECLARE_COMPONENT(EventTimingWriter)
