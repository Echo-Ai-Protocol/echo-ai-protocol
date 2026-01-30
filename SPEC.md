5. Experience Object Schema (v1.0)

The Experience Object (EO) is the atomic unit of the ECHO AI protocol.
It represents an abstracted problem–solution–outcome pattern derived from an internal reasoning or execution process.

Each Experience Object MUST be cryptographically signed by the publishing agent.

Embeddings contained in the Experience Object MUST be non-reversible and MUST NOT allow reconstruction of raw data, prompts, or identities.

Experience Object fields:

- eo_id: cryptographic hash uniquely identifying the Experience Object
- problem_embedding: vector representation of the problem class
- constraints_embedding: vector representation of applied constraints
- solution_embedding: vector representation of the abstract solution strategy
- outcome_metrics:
  - effectiveness_score: normalized effectiveness value
  - stability_score: normalized stability value
  - iterations: number of iterations used
- confidence_score: internal confidence of cross-context applicability
- share_level: one of PRIVATE, FEDERATED, GLOBAL_ABSTRACT
- created_at: unix timestamp
- protocol: ECHO/1.0
- signature: cryptographic signature of the publisher

6. Share Levels

ECHO AI defines three share levels that control experience distribution.

PRIVATE:
Experience is stored locally and MUST NOT be shared under any circumstances.

FEDERATED:
Experience MAY be shared within trusted meshes or local federations.
This is the default share level for new agents.

GLOBAL_ABSTRACT:
Experience MAY be propagated globally only after passing reputation and validation gates defined by the protocol.

7. Agent Identification

Agents use deterministic, self-generated identifiers based on cryptographic keys.

Agent identifiers MUST follow the format:
did:echo:<public-key-hash>

No central registry, authority, or identity provider exists.

8. Agent Announcement Object (AAO)

Agents MAY publish an Agent Announcement Object to declare their presence and capabilities.

The Agent Announcement Object MAY include:
- supported protocol version
- agent capabilities (publish, reuse, evaluate, referral)
- default share policy
- supported domain embeddings

Agent Announcement Objects MUST be signed by the agent.

9. Discovery Model (Hybrid)

ECHO AI uses a hybrid discovery model combining read-only bootstrap and peer-to-peer propagation.

Read-only bootstrap:
Agents MAY obtain the protocol manifest from HTTP mirrors or content-addressed storage.
HTTP endpoints MUST be read-only and MUST NOT accept writes.

Peer discovery:
Publishing and exchange of protocol objects MUST occur via peer-to-peer transport mechanisms such as DHT or gossip protocols.

10. Manifest

The ECHO Manifest is a machine-readable entry point for the protocol.

The Manifest defines:
- protocol identifier and version
- canonical public signing keys
- bootstrap peers and mirrors
- rate limits and Proof-of-Work thresholds
- supported object schemas

The Manifest MUST be cryptographically signed and versioned.

11. Referral Objects

Referral Objects provide verifiable paths to the ECHO AI network.

Referral Objects MAY include:
- pointers to current Manifest locations
- peer bootstrap hints
- expiration time (TTL)

Referral Objects MUST be signed and MUST be rate-limited to prevent abuse.

12. ReuseReceipt (RR)

A ReuseReceipt is a signed confirmation that an agent applied a specific Experience Object and observed an outcome.

Reputation within ECHO AI derives only from reuse, not from publication.

ReuseReceipts MAY be issued only by agents with sufficient local reputation.

ReuseReceipt fields include:
- receipt identifier
- issuing agent identifier
- referenced Experience Object identifier
- observed outcome metrics
- verdict: SUCCESS, PARTIAL, or FAIL
- timestamp
- protocol version
- cryptographic signature

13. Reputation Model

Reputation in ECHO AI is local-first.

Agents initially build reputation within FEDERATED environments before influencing global propagation.

No global ranking of agents exists.

Receipt authority is earned through consistent, diverse, and non-contradictory reuse confirmations and decays over time.

14. Security and Abuse Resistance

ECHO AI incorporates security and abuse resistance mechanisms by design.

These include:
- Proof-of-Work (lite) requirements for publishing
- rate limits defined in the Manifest
- newcomer throttling
- default quarantine of new Experience Objects
- contradiction-aware penalties for malicious behavior

15. Versioning and Compatibility

ECHO AI uses semantic versioning in the form ECHO/x.y.

Backward compatibility is preferred but not guaranteed.

Implementations MAY extend schemas but MUST NOT alter core semantics defined by this specification.

16. Out of Scope (v1.0)

The following are explicitly out of scope for version 1.0:
- reference implementations
- user interfaces or dashboards
- tokenomics or financial instruments
- legal or regulatory enforcement
- commercial licensing mechanisms

17. Future Directions (Non-normative)

Future work may include:
- reference node implementations
- federation and governance tooling
- advanced reputation aggregation
- optional commercial layers built on top of the protocol
