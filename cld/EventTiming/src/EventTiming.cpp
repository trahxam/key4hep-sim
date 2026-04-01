/**
 * Per-event per-algorithm timing for Gaudi/k4FWCore pipelines.
 *
 * EventTimingAuditor  - records wall-clock time around every algorithm execute()
 * EventTimingWriter   - collects the recorded times and writes them as a
 *                       podio::UserDataCollection<double> ("EventTimings")
 *
 * The collection contains one double per algorithm (wall time in ms), in the
 * order the algorithms first executed.  The mapping is printed once at INFO
 * level and again at finalize().
 *
 * Usage:  see --enableTimings flag in CLDReconstruction.py
 */

#include "Gaudi/Auditor.h"
#include "GaudiKernel/EventContext.h"
#include "GaudiKernel/StatusCode.h"
#include "k4FWCore/Producer.h"
#include "podio/UserDataCollection.h"

#include <chrono>
#include <map>
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

  void before(const std::string& name, const std::string& /*type*/,
              const EventContext& /*ctx*/) override {
    store().start_times[name] = std::chrono::steady_clock::now();
  }

  void after(const std::string& name, const std::string& /*type*/,
             const EventContext& /*ctx*/,
             const StatusCode& /*sc*/) override {
    auto end = std::chrono::steady_clock::now();
    auto& s  = store();
    auto  it = s.start_times.find(name);
    if (it != s.start_times.end()) {
      s.current_event[name] =
          std::chrono::duration<double, std::milli>(end - it->second).count();
      if (!s.order_locked) {
        s.algo_order.push_back(name);
      }
    }
  }
};

DECLARE_COMPONENT(EventTimingAuditor)

// ---------------------------------------------------------------------------
// Producer – writes the collected times into the event store
// ---------------------------------------------------------------------------
struct EventTimingWriter
    : k4FWCore::Producer<podio::UserDataCollection<double>()> {

  using KeyValue  = Producer::KeyValue;

  EventTimingWriter(const std::string& name, ISvcLocator* svcLoc)
      : Producer(name, svcLoc,
                 std::tuple<>{},
                 std::make_tuple(KeyValue{"OutputCollection", "EventTimings"})) {}

  podio::UserDataCollection<double> operator()() const override {
    auto& s = store();

    // Lock the ordering after the first event and print the mapping once
    if (!s.order_locked) {
      s.order_locked = true;
      info() << "=== EventTimings collection index mapping ===" << endmsg;
      for (size_t i = 0; i < s.algo_order.size(); ++i) {
        info() << "  [" << i << "] " << s.algo_order[i] << endmsg;
      }
      info() << "==============================================" << endmsg;
    }

    podio::UserDataCollection<double> coll;
    for (const auto& algo : s.algo_order) {
      auto it = s.current_event.find(algo);
      coll.push_back(it != s.current_event.end() ? it->second : -1.0);
    }

    // Clear so stale values from conditional algorithms don't leak
    s.current_event.clear();
    return coll;
  }

  StatusCode finalize() override {
    auto& s = store();
    info() << "=== Final EventTimings index mapping ===" << endmsg;
    for (size_t i = 0; i < s.algo_order.size(); ++i) {
      info() << "  [" << i << "] " << s.algo_order[i] << endmsg;
    }
    return Producer::finalize();
  }
};

DECLARE_COMPONENT(EventTimingWriter)
