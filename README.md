🔍 TEA Research & Verification Agent
====================================

_A Tool–Environment–Agent (TEA) Protocol Implementation for Trustworthy AI Research_

Motivation
----------

After reading the paper**“The Tool–Environment–Agent Protocol”**[https://arxiv.org/abs/2506.12508](https://arxiv.org/abs/2506.12508)

I was fascinated by the idea that LLM systems should not just _call tools_, but should be structured as:

*   **Tools** → Capabilities
    
*   **Environment** → State & Observations
    
*   **Agents** → Reasoning & Control
    

Most existing “AI agents” are just LLM + tools.This project is my attempt to build a **true TEA-compliant system** where:

*   The **Environment** is explicit and stateful
    
*   The **Agent** reasons, plans, verifies, retries, and stops
    
*   The **Tools** are clean, auditable, and replaceable
    

The goal:

> Build a research system that is _verifiable, explainable, and controllable_, not just fluent.

What This System Does
---------------------

This project is an **AI Research & Verification Agent** that:

1.  Accepts a user query
    
2.  Searches the web
    
3.  Extracts factual claims
    
4.  Verifies them across sources
    
5.  Scores confidence
    
6.  Plans retries if evidence is weak or conflicting
    
7.  Synthesizes a final answer
    
8.  Stores everything for audit and reproducibility
    

All of this is orchestrated using a **TEA-style architecture**.

TEA Architecture Mapping
------------------------

### 🛠 Tools

*   Web search APIs
    
*   LLM (Gemini 2.5)
    
*   PostgreSQL
    
*   Cache
    
*   Verification models
    

Tools are _stateless and dumb_. They only execute.

### 🌍 Environment

*   WebEnvironment (documents, sources, retrieval state)
    
*   Database (sessions, evidence, planner traces, cache)
    
*   Budgets (search limits, retry limits, TTL)
    
*   Query cache
    
*   System state for each session
    

The environment is what the agent _observes and acts upon_.

### 🧠 Agents

#### 1\. Planner Agent (Meta-Controller)

*   State machine: INIT → RESEARCH → VERIFY → SYNTHESIZE → DONE / FAILED
    
*   Controls:
    
    *   Retry logic
        
    *   Strategy switching
        
    *   Budget enforcement
        
    *   Loop prevention
        
    *   Cache reuse
        
*   Decides when to stop and when to trust results
    

#### 2\. Verification Agent

*   Decides:
    
    *   ACCEPT
        
    *   RETRY
        
    *   STOP
        
*   Based on:
    
    *   Confidence level
        
    *   Conflict detection
        
    *   Source diversity
        
    *   Evidence sufficiency
        

#### 3\. Confidence Scorer

*   Rule-based, explainable:
    
    *   HIGH → multiple independent reputable sources
        
    *   MEDIUM → partial agreement
        
    *   LOW → single source or conflicts
        
*   Always returns:
    
    *   confidence\_level
        
    *   confidence\_reason
        

#### 4\. Answer Synthesizer

*   Strict claim-grounded generation
    
*   No hallucination
    
*   No inference beyond verified claims
    
*   TEA-safe phrasing
    

Why This Is Better Than Typical RAG
-----------------------------------

Typical RAGThis SystemOne-shot retrievalMulti-attempt planningNo stateStateful environmentNo verificationCross-source verificationNo confidence logicExplicit confidence reasoningNo audit trailFull planner + evidence traceNo stopping logicBudget-aware terminationLLM decides everythingLLM only phrases, agents decide

This is not “LLM with tools”.This is **LLM inside an Agent, operating over an Environment, using Tools** — exactly what TEA proposes.

Storage & Explainability
------------------------

All runs are stored in PostgreSQL:

### Domains

1.  **Query Sessions** – user questions, final status
    
2.  **Answer Snapshots** – final responses
    
3.  **Evidence & Claims** – every verified claim + source
    
4.  **Planner Traces** – attempts, strategies, decisions
    
5.  **Search Logs** – cost, queries, failures
    
6.  **Cache** – TTL-based reuse
    

This enables:

*   Reproducibility
    
*   Auditing
    
*   Debugging
    
*   Trust
    

Tech Stack
----------

### Core

*   Python 3.11
    
*   FastAPI
    
*   PostgreSQL
    
*   SQLAlchemy
    
*   Alembic (migrations)
    

### AI

*   **Gemini 2.5 API**
    
*   Custom LLM client wrapper
    

### Architecture

*   TEA Protocol
    
*   State Machine Planner
    
*   Deterministic Verification
    
*   Rule-based Confidence
    
*   Cache + Budget Control
    

Why I’m Proud of This
---------------------

This project is not just another “AI app”.It is a **control-theoretic, research-grade agent system** that:

*   Separates reasoning from execution
    
*   Makes verification explicit
    
*   Makes confidence explainable
    
*   Makes failure safe
    
*   Makes decisions auditable
    

It follows the same design philosophy used in:

*   Autonomous robotics
    
*   Formal agent systems
    
*   Scientific workflow engines
    

But applied to **LLM-based research**.

Status
------

*   Backend: Complete
    
*   TEA layers: Implemented
    
*   Planner + Verification: Working
    
*   Storage + Cache: Integrated
    
*   API: Ready
    
*   Frontend: Connected
    
*   Next: Scaling, multi-modal environments, tool learning
    

Reference
---------

This project is inspired by:

**The Tool–Environment–Agent Protocol**[https://arxiv.org/abs/2506.12508](https://arxiv.org/abs/2506.12508)
