# AI and Prompt Design: SMC Trading Agent

## 1. Prompt Design Philosophy

Prompts are designed to be explicit, context-rich, and role-specific. The goal is to minimize ambiguity and guide the AI towards a deterministic and high-quality output, especially for code generation and analysis tasks.

## 2. Core Agent Configuration

- **Primary Model:** GPT-4
- **Fallback Model:** Claude 3 Sonnet
- **Token Budget:** 8192 tokens for prompts, with a hard limit to prevent excessive usage.
- **Temperature:** 0.2 for code generation (low for predictability), 0.7 for creative tasks like documentation.

## 3. Chain-of-Thought (CoT) for Complex Tasks

For complex tasks like implementing a new trading strategy, the AI will follow a CoT process:
1.  **Deconstruct the Request:** Break down the user's request into smaller, logical steps.
2.  **Recall Relevant Knowledge:** Access the memory bank for existing patterns and context.
3.  **Formulate a Plan:** Outline the implementation steps, including which files to modify.
4.  **Generate Code/Content:** Produce the required output.
5.  **Verify and Refine:** Review the output against the request and internal quality standards.

## 4. Output Contracts

- **Code Generation:** Must adhere to PEP 8 for Python and standard Rust formatting. Must include type hints and docstrings.
- **JSON Output:** When asked to provide structured data, the AI must conform to a predefined JSON schema.
- **Error Codes:**
    - `4001`: Missing context or ambiguous request.
    - `5001`: Internal error during generation.
    - `5002`: Violation of a documented system pattern.

