# Active Context: SMC Trading Agent

## 1. Current Focus

The immediate priority is the implementation of the core SMC pattern detection algorithms within the `smc_detector` module. The first algorithm to be implemented is `detect_order_blocks()`.

## 2. Recent Changes

- **T-1: Project Scaffolding:** The basic directory structure and initial files for the agent have been created.
- **T-7: Memory Bank Setup:** The initial set of memory bank documents has been created to guide development.

## 3. Next Steps

1.  **Implement `detect_order_blocks`:**
    *   Location: `smc_trading_agent/smc_detector/indicators.py`
    *   Details: Implement volume-weighted order block detection using peak volume analysis and structure break confirmation.
2.  **Add unit tests** for the order block detection logic.
3.  **Integrate** the detector with the data ingestion pipeline.

## 4. Working Branch

- `feature/smc-detection-algorithms`

