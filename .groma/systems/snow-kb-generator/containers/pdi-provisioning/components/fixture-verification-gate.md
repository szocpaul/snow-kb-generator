---
type: C4 Component
title: PDI-native verification fixture (spec 015 T001/T002)
status: stable
groma:
  id: fixture-verification-gate
  parent: pdi-provisioning
  code:
    - scanner: python
      file: scripts_pdi/fixture_verification_gate.py
description: 'Provisions the calibration fixture on a fresh PDI: one Story plus one Update Set that capture only ALREADY EXISTING components (touch+revert — no new Script Include / Business Rule / field is created, per the spec constraint). Resume-capable via artifacts/verification_fixture_state.json; the verify subcommand spot-checks that every captured name exists (SC-001 input for the spec 015 gates).'
---
