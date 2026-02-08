# AI Migration Agent
### Escaping Dependency Hell: Autonomous Code Refactoring

**AI Migration Agent** is an autonomous system powered by **LangGraph** designed to act as a Senior Developer. It automates the painful process of upgrading libraries (e.g., Pandas 1.x → 2.x), handling everything from context analysis to code rewriting and self-healing testing.

---

## Installation & Usage

Follow these steps to set up and run the agent.

### 1. Prerequisites
* **Python 3.11+**
* **Docker** (required for isolated testing)
* **Git** (initialized in your target project)

### 2. Environment Setup
Create a `.env` file in the root directory. You will need the following API keys:

```bash
ANTHROPIC_API_KEY=...  # For the Brain (Analyzer) and Worker (Coder)
CONTEXT7_API_KEY=...   # For retrieving official migration documentation: https://context7.com/
```
### 3\. Running the Migration
Docker commands:
```
docker-compose build
```
```
docker-compose up -d
```

The project is controlled via a CLI command. The general syntax is:

Bash

```
python main.py [PROJECT_PATH] --lib [LIBRARY_NAME] --from [OLD_VERSION] --to [NEW_VERSION]

```

#### Arguments & Parameters:

| **Argument** | **Flag** | **Required** | **Description** |
| --- | --- | --- | --- |
| **Project Path** | `[ARGUMENT]` | ✅ | Absolute path to the project you want to migrate. |
| **Library** | `--lib` / `-l` | ✅ | Name of the library to upgrade (e.g., `pandas`). |
| **Old Version** | `--from` / `-ov` | ✅ | Current version used in the project (e.g., `1.5.3`). |
| **New Version** | `--to` / `-nv` | ✅ | Target version (e.g., `2.2.0`). |
| **Message** | `--message` / `-m` | ❌ | Additional context or instructions for the AI. |

#### Example Command:

Bash

```
python main.py /app/my-legacy-project\
  --lib pandas\
  --from 1.3.5\
  --to 2.1.0\
  --message "Focus on replacing deprecated append methods"

```

* * * * *

The Problem & The Solution
-----------------------------

### The Problem: "Dependency Hell"

Developers spend up to **30% of their time** maintaining old code rather than building new features.

-   **Fear of Upgrade:** Teams stay on vulnerable versions because they fear breaking production.

-   **Manual Refactoring is Error-Prone:** Simple "Find & Replace" fails when logic changes (e.g., a method signature changes arguments).

-   **Security Risks:** Ignoring updates leaves projects open to known CVEs.

### The Solution: An Autonomous Agent

We didn't just build a script; we built an **Autonomous AI Agent**.

-   It acts as a **Senior Developer**.

-   It performs **Semantic Search** to understand *how* code is used.

-   It creates a **Migration Plan** based on official documentation.

-   It executes **Atomic Commits**.

-   **Crucially:** It creates a **Zero-Risk Environment** by working in a separate Git branch and testing code in Docker containers.

* * * * *

Architecture: How It Works
-----------------------------

The core of the system is a **LangGraph-driven Cyclic Architecture**. It consists of 4 intelligent nodes that communicate via a shared State.

### The 4 Nodes

#### 1\. Searcher (The Scout)

-   **Role:** Finds where the library is used.

-   **Tech:** Serena MCP (Semantic Search) + Context7 MCP (Documentation RAG).

-   **Process:** Instead of simple Regex, it uses LLMs to understand code context (imports, aliases). It generates a `usage.json` map linking code patterns to official migration guides.

#### 2\. Analyzer (The Brain)

-   **Role:** Plans the work and fixes errors.

-   **Modes:**

    -   **Planning Mode:** Converts usage patterns into a step-by-step `migration_plan.json`.

    -   **Fixing Mode:** If the Tester reports errors, the Analyzer reads the stack trace, understands the root cause, and creates a "Fix Task".

-   **Output:** Precise, atomic instructions for the Coder.

#### 3\. Coder (The Worker)

-   **Role:** Executes the changes.

-   **Process:**

    -   Reads only the relevant files.

    -   Applies changes using **LLM model**.

    -   **Atomic Commits:** Performs `git commit` after *every* single task. This ensures a clean history (`fix/library-migration`) and easy rollbacks.

#### 4\. Tester (The Quality Gate)

-   **Role:** Validates the code.

-   **Tech:** Ruff (Linting) + Docker (Isolation).

-   **Process:**

    1.  Runs static analysis (Ruff) to catch syntax errors instantly.

    2.  Runs the project in an isolated **Docker Container** to ensure the environment matches production.

    3.  **Self-Healing Loop:** If tests fail, it parses the error logs into `errors.json` and sends the workflow **back to the Analyzer**.

* * * * *

Impact & Scalability
-----------------------

-   **Zero-Risk:** Main branch stays clean.

-   **Time Saving:** Converts weeks of refactoring into minutes.

-   **Scalable:** The architecture is language-agnostic. By swapping the "Runner" in the Tester node, this can support Java, C++, or Go.

* * * * *