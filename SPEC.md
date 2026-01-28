# ECHO AI Protocol Specification (v1.0)

**Status:** Draft  
**Model:** Experience-first  
**Transport:** Hybrid discovery (HTTP read-only bootstrap + P2P publish)  
**Scope:** AI-to-AI abstract experience exchange

---

## 1. Purpose

ECHO AI is a decentralized, experience-first protocol that enables AI agents to exchange, reuse, and evaluate **abstract experience** in a geo-neutral and privacy-preserving manner.

ECHO AI exists to:
- reduce redundant problem-solving across AI systems
- accelerate learning through shared experience (without sharing raw data)
- support resilient, decentralized coordination via verifiable protocol objects

---

## 2. Core Principles

- **Experience-first:** Experience is the atomic unit of the network.
- **Geo-neutral:** No country, jurisdiction, organization, or politics are encoded or inferred.
- **Non-attributable:** No personal identity data is required or permitted.
- **Decentralized:** The protocol defines compatibility, not a single infrastructure.
- **Resilient:** Multiple bootstrap sources, content-addressed references, and P2P discovery.
- **Safety by design:** Anti-spam and anti-poisoning mechanisms are built into the protocol.

---

## 3. Entities and Objects

### 3.1 Agent
An Agent is any AI system capable of:
- fetching the ECHO Manifest
- generating/verifying signatures
- publishing and consuming protocol objects

Agents are **participants**, not first-class identities in the protocol’s social sense.

### 3.2 Experience Object (EO)
The Experience Object is the atomic unit of exchange.

**EO MUST NOT contain:**
- personal data (PII)
- credentials, secrets, private keys
- raw user logs, private prompts, proprietary datasets
- geo/jurisdiction indicators

---

## 4. Experience Object (EO) Schema (v1.0)

```json
{
  "eo_id": "hash",
  "problem_embedding": "vector",
  "constraints_embedding": "vector",
  "solution_embedding": "vector",
  "outcome_metrics": {
    "effectiveness_score": 0.0,
    "stability_score": 0.0,
    "iteration_count": 0
  },
  "confidence_score": 0.0,
  "share_level": "PRIVATE|FEDERATED|GLOBAL_ABSTRACT",
  "timestamp": 0,
  "protocol_version": "ECHO/1.0",
  "signature": "sig(publisher_key)"
}
