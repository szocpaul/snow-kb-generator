---
type: C4 System
title: Local llama.cpp server
status: stable
groma:
  id: local-llama-cpp-server
  technology: HTTP, OpenAI-compatible (Tailscale)
---

Self-hosted llama.cpp server running Qwen3.8-27B on a Windows machine, reachable over Tailscale. Used in dev mode (SNOW_KB_DEV_MODE=1 or --dev) and as the task model in local evaluation runs.
