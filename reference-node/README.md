# ECHO Reference Node (v0.8)

This folder contains a minimal reference implementation of the ECHO protocol.

Goal: provide a simple, auditable, runnable node that can:
- load `manifest.json`
- load JSON schemas from `/schemas`
- validate protocol objects (EO / Trace / Request / RR)
- store validated objects locally (file-based storage)
- perform basic search over stored objects (field equality)

> Note: This is a local reference node (no P2P networking yet).
> P2P/discovery will be introduced in later versions.

## Quick start

### 1) Install requirements
```bash
python3 -m pip install -r reference-node/requirements.txt
