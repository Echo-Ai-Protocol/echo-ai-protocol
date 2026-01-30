# DIRECTORY LAYOUT

This repository is a protocol seed. Future implementations MAY map objects to a filesystem layout.

## Recommended layout

/.well-known/echo-ai/manifest.json
/manifest.json
/SPEC.md

/docs/
/examples/

## Object collections (implementation hint)

/objects/experience/
/objects/trace/
/objects/request/
/objects/receipt/
/objects/announcement/
/objects/referral/

## Notes

- Trace and Request objects are ephemeral; implementations SHOULD support TTL-based garbage collection.
- ExperienceObjects may be stored as global abstracts (no raw prompts).
- ReuseReceipts MUST be immutable once published.
