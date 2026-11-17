# Code Standards & Engineering Hygiene

## 📐 General Rules
1. **Keep it Simple:** Do not over-engineer. Write clean, readable code that works reliably under live demo conditions.
2. **Separation of Concerns:** Keep core math/algorithms strictly separated from UI components and data loading layers[span_26](start_span)[span_26](end_span).
3. **Robust Error Handling:** Always wrap API calls, file reads, and algorithm executions in `try/catch` blocks with meaningful fallbacks[span_27](start_span)[span_27](end_span).
4. **Input Validation:** Validate all user inputs and edge cases before passing them into optimization or routing functions[span_28](start_span)[span_28](end_span)[span_29](start_span)[span_29](end_span).
5. **Security:** No hardcoded API keys, passwords, or secrets. Use environment variables and maintain a clean `.gitignore`[span_30](start_span)[span_30](end_span)[span_31](start_span)[span_31](end_span)[span_32](start_span)[span_32](end_span).
