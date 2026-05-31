# AI Code Review Assistant: Comprehensive Technical & Algorithmic Report

This document details the underlying algorithms, architectural pipeline, state management, and strict data contracts driving the AI Code Review Assistant. 

---

## 1. System Architecture & Orchestration Pipeline

The system is designed as an asynchronous, pipeline-driven architecture. The core logic operates within `app/services.py` (`CodeAnalysisService`), which acts as an orchestrator for a sequence of independent analytical modules. 

The pipeline strictly guarantees that lightweight, deterministic operations run first, providing context that enriches the heavier, non-deterministic Generative AI layer.

**Pipeline Flow:**
1. **Validation (`CodeValidationService`)**: Ensures code length is within token limits (`MAX_CODE_LENGTH`) and discards placeholder text (e.g., `// Write your code here...`).
2. **Structural Parsing (`CodeParser`)**: Converts raw string input into an Abstract Syntax Tree (AST). If parsing fails (syntax error), the pipeline short-circuits, returning a 400 error immediately without invoking AI compute.
3. **Deterministic Rule Engine (`RuleEngine`)**: Traverses the AST to identify hard-coded antipatterns.
4. **Algorithmic Profiling (`ComplexityAnalyzer`)**: Analyzes looping constructs to derive mathematical Big-O estimations.
5. **Semantic AI Layer (`AIAnalyzer`)**: Receives the raw code, AST rule violations, and Big-O metrics as a consolidated prompt for the Google Gemini API to identify deep logical bugs.

---

## 2. Deterministic AST Rules Engine (`app/analyzer/rules.py`)

The deterministic engine utilizes Python's built-in `ast` module. It acts as an extremely fast, zero-latency linter designed to catch structural flaws that AI models might overlook.

### Algorithm
The engine implements an `ast.NodeVisitor` design pattern. It walks the syntax tree and overrides specific node-visit methods to trigger validation logic:
*   **Variable Shadowing (`visit_FunctionDef`)**: Compares function argument identifiers against Python's built-in namespace (`dir(builtins)`). If a parameter is named `list` or `dict`, it flags a shadowing issue.
*   **Exception Safety (`visit_ExceptHandler`)**: Checks if an `except:` block defines an exception type (`node.type is None`). If missing, it flags a "bare except" which is a known anti-pattern that swallows `KeyboardInterrupt`.
*   **Resource Leaks (`visit_With` & `visit_Assign`)**: Traverses `open()` calls. If `open()` is assigned directly to a variable (`f = open('...')`) outside of a `with` context manager, it flags a potential unclosed file descriptor.

All violations are strictly mapped to an internal schema containing a `uuid`, line number, and a severity mapping.

---

## 3. Algorithmic Complexity Calculation Engine (`app/analyzer/complexity.py`)

Instead of relying solely on the AI to guess the Time and Space complexity, the system employs a custom mathematical engine utilizing AST traversal to guarantee programmatic accuracy.

### Big-O Time Complexity Algorithm
The `ComplexityVisitor` recursively analyzes function definitions to track depth loops:
1.  **Linear & Polynomial Detection (`visit_For`, `visit_While`)**: The visitor maintains a `loop_depth` counter. Every time it enters a loop node, it increments the depth; on exit, it decrements. The `max_loop_depth` is tracked. A max depth of `1` yields `O(N)`, `2` yields `O(N²)`, etc.
2.  **Logarithmic Detection**: The algorithm looks for division assignments (`visit_Assign` and `visit_AugAssign`). If a variable inside a loop is modified using `// 2` or bitwise right-shift `>> 1`, the system flags the loop as logarithmic (`O(log N)`).
3.  **Recursive Detection (`visit_Call`)**: The visitor checks if a function call identifier matches the parent function identifier. If it does, and no specific memoization or halving is detected, it flags exponential `O(2^N)` potential.

### Big-O Space Complexity Algorithm
The visitor tracks memory allocation nodes. Whenever it encounters a list comprehension (`visit_ListComp`), dictionary creation, or calls to `.append()`, `.insert()`, it increments a tracked space multiplier against the current `loop_depth`.

---

## 4. Generative AI Semantic Layer (`app/analyzer/ai_layer.py`)

The system utilizes `google.generativeai` (Gemini-1.5-Flash) to catch logical, architectural, and security flaws that ASTs cannot detect.

### Context Windowing & Hallucination Mitigation
The prompt injected into the Gemini model is heavily structured:
*   **Context Priming**: The model is fed the AST findings and the calculated Big-O metrics. This prevents the model from wasting tokens redefining issues the system already knows about.
*   **Strict Output Enforcement**: The system demands the output strictly conform to a JSON array. 
*   **Regex JSON Extraction**: Because LLMs notoriously wrap JSON in markdown (e.g., ```json ... ```), the `_process_ai_response` method uses a robust regex block (`re.search(r'\[.*\]', response, re.DOTALL)`) to extract purely the JSON payload, gracefully falling back to legacy processing if parsing fails.

### Data Normalization
AI responses are mapped to a strict contract required by the UI:
`{"id": UUID, "type": "security", "problem": str, "solution": str, "example": str, "line": int, "severity": "high", "scope": "local", "source": "ai"}`

---

## 5. Frontend State & UI Virtualization

The React frontend operates as a heavy, interactive single-page application built with Vite.

### Global State (Zustand)
Instead of deep prop-drilling or dealing with the boilerplate of Redux, the app uses **Zustand**. A centralized `useStore.js` file holds the user's current code, language selection, API response (`analysisResult`), and loading states. This allows the Monaco editor and the Analysis side-panel to exist entirely uncoupled while reacting to the exact same data source in real-time.

### Monaco Editor Synchronization & Debouncing
The synchronization between the user's keystrokes and the backend analysis requires tight performance guards (`Dashboard.jsx`):
*   **Network Debouncing**: Typing triggers a `setTimeout`. If the user types again within `700ms`, the timer is cleared. This guarantees the backend is only hit when the user actually pauses.
*   **Request Cancellation**: If an analysis is running and the user types again, an `AbortController` triggers an `abort()` signal, killing the pending Axios HTTP request to save client-side memory.
*   **Marker Injection**: The system parses the normalized `analysisResult` and injects `monaco.editor.setModelMarkers` (squiggly lines). To prevent visual tearing or editor lag:
    *   Issues are clamped via `MAX_MARKERS = 50`.
    *   Issues sharing the exact same line are mathematically grouped using `groupByLine()` to prevent Monaco from randomly overwriting markers.
    *   Background heatmaps are injected into Monaco's `createDecorationsCollection` based on severity (`bg-rose-500/20` for High, `bg-sky-500/10` for Low).

---

## 6. Database Schema & Persistence (`app/models.py`)

The Flask application uses SQLite paired with SQLAlchemy.

*   `User`: Handles authentication logic using `flask_login` (hashed passwords).
*   `CodeSubmission`: Stores the raw code payload, language, analysis duration, and stringified JSON blobs for the issues, complexity, and AI suggestions.
*   `ReviewHistory`: Maps `CodeSubmission` records to users for historical rendering.

This persistence layer ensures that any optimizations generated by the AI can be retrieved by the user at a later date, providing a persistent "Code Health" history.

