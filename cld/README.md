# CLD Tracking Fix Validation

## Comparing baseline vs InnerVXDExtend fix

### 1. Generate the two reconstruction samples

Run both test scripts with the same seed and event count (default 10 events):

```bash
NEV=100 bash run_test_baseline.sh   # uses CLDReconstruction_baseline.py
NEV=100 bash run_test_fixed.sh      # uses CLDReconstruction.py (with InnerVXDExtend)
```

This produces `reco_test_baseline.root` and `reco_test_fixed.root` in the current directory.

### 2. Run the comparison

```bash
python compare_tracking.py reco_test_baseline.root reco_test_fixed.root tracking_comparison.pdf
```

The output PDF contains six panels: innermost hit radius, layer-1 doublet pickup, hit multiplicity, d0 resolution, |d0| CDF, and chi2/ndf.
