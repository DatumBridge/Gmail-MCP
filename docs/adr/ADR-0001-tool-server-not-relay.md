# ADR-0001 — Tool-Server, Not Relay

## Context

DatumBridge MCP taxonomy distinguishes tool-servers from the WS hub relay.

## Decision

Implement Gmail as a **Python FastMCP tool-server** under `mcp/gmail-mcp`, sibling to `google-drive-mcp`.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|--------------|
| Extend WS hub | Wrong class; Gmail is cloud SaaS |
| Add Gmail tools into Drive MCP | Mixes products; harder scoping |
| Go relay template | Unnecessary transport layer |

## Consequences

- Copy Drive OAuth/tool patterns; forbid hub WS/correlation/catalog copies.
- `design.md` declares tool-server class.

## Risks

Authors might still paste hub packages — mitigated by docs and checklist.
