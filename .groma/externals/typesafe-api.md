---
type: C4 System
title: TypeSafe API
status: stable
groma:
  id: typesafe-api
  technology: typesafe-sdk 0.7.x over HTTPS
---

Hosted decision API behind the typesafe-sdk (System One typed Choice and Noul calls). Used with the pinned jev-1.13.0 model: the audience decision (spec 013) and the component-name verification calibrated layer (spec 014) call it, and the eval capture/reanchor runners record from it. Authenticated with the TYPESAFE_API_KEY environment variable.
