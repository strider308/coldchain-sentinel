# Command Center Algorithm Integration

Phase 38 brings STBL evidence and inspection recommendations into the main command center.

## Dashboard integration

The command center shows:

- The 171,000-row synthetic training corpus
- Neural and distilled synthetic metrics
- Links to the algorithm console, predictor, and inspection engine
- Representative high-value cases and their first human inspection target
- A concise offline-training to transparent-runtime story
- Explicit safety boundaries and blocked operational actions

The integration adds no dependency and changes no application architecture. It is a static presentation layer over existing Phase 35B/36 payload functions.

## Runtime boundary

The live application remains stdlib-only. It makes no outbound call from these routes and requires no GPU, PyTorch, notebook, database, or external service.
