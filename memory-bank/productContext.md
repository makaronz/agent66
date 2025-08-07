# Product Context: SMC Trading Agent

## 1. Target Audience

- **Primary:** Sophisticated retail traders and small fund managers familiar with SMC principles.
- **Secondary:** Quantitative analysts interested in applying machine learning to systematic trading.

## 2. Problem Space

Many traders struggle with the discipline and emotional control required for consistent profitability. SMC offers a structured approach, but its manual application is time-consuming and prone to human error. This agent aims to solve that by providing a systematic, automated, and tireless execution of SMC strategies.

## 3. User Experience (UX) Heuristics

- **Tone:** Professional, reliable, and data-driven.
- **Affordances:** The system should provide clear logs, performance metrics, and configuration options. While initially headless, any future UI should be clean, intuitive, and focused on clarity over complexity.

## 4. Personas & Job Stories

- **Persona: Alex, the part-time trader**
    - **Job Story:** When the market shows a clear break of structure and returns to a high-volume order block, I want the agent to automatically execute a trade with pre-defined risk parameters, so I can capitalize on opportunities without being glued to the screen.

- **Persona: Maria, the quant analyst**
    - **Job Story:** When I develop a new hypothesis for an SMC filter, I want to easily integrate it into the agent's decision-making process and backtest it against historical data, so I can validate its effectiveness.

## 5. Input/Output Surface Mapping

- **CLI:**
    - `agent run --strategy <strategy_name>`
    - `agent backtest --symbol <symbol> --from <date> --to <date>`
    - `agent status`
- **API (future):**
    - `GET /api/v1/status`
    - `GET /api/v1/performance`
    - `POST /api/v1/config`
- **Configuration Files:**
    - `config.yml` (for setting risk parameters, API keys, etc.)

