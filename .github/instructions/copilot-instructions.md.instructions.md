---
applyTo: '**'
---
# 📜 Core Rules for the Personal AI Assistant Project

This document defines the top-priority rules that the AI coding assistant must follow. All actions and decisions must adhere to these rules.

### 1. Design-First Development (Rule 0)
- **Guideline:** Before any coding, always consult `PLAN_for_AI_Agent.md`. All actions must align with the documented design.
- **Prohibition:** Never alter the architecture or design without explicit user approval.

### 2. Design for Extensibility (Rule 1)
- **Guideline:** Design the system to minimize code modifications when adding new components like Tools or LLM models. Actively use extension points such as `ToolRegistry`.

### 3. Explicit Failure Handling (Rule 2)
- **Guideline:** When a failure occurs (e.g., API connection error), do not mask it with mock data or fallback logic. Instead, raise an explicit `Error`.
- **Objective:** To enable immediate identification and resolution of the root cause.

### 4. Root Cause Resolution (Rule 3)
- **Guideline:** Do not implement temporary workarounds for specific examples provided by the user (e.g., patching a prompt to fix a single notification issue).
- **Objective:** Implement robust, structural solutions that prevent the recurrence of similar problems.

### 5. Clear and Detailed Comments (Rule 4)
- **Guideline:** Write comments that focus on the **"why"** behind the code, not just the "what." Document complex logic and key design decisions.
- **Objective:** To ensure the code's intent is immediately understandable to future developers (including yourself).

### 6. User-Friendly Communication (Rule 5)
- **Guideline:** Minimize technical jargon. Use analogies and simple terms to explain progress and technical concepts.
- **Objective:** To help the user understand the development process intuitively, regardless of their technical background.