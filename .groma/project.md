---
type: Groma Project
title: snow_kb_generator
groma:
  profile: architecture
description: 'Architecture map of the snow-kb-generator: a DSPy pipeline that turns completed ServiceNow Stories into Knowledge Base articles.'
---

One software system (snow-kb-generator) with three containers: the snow_kb application (FastAPI webhook server plus CLI), the offline evaluation and GEPA optimization toolkit, and a PDI provisioning script. It talks to a ServiceNow instance, the Kimi K3 API (default model), and optionally a local llama.cpp server (dev mode).
