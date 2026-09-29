# Security policy

## Supported versions

Security fixes go into the latest release on `main`.

## Reporting a vulnerability

Please do not open a public issue. Report privately through GitHub: **Security > Report a vulnerability** on
this repository. Include what an attacker could do, how to reproduce it and the versions involved (Resolve,
Python, the connector's `fu_version_info`). You should hear back within a week.

## What is in scope

The server runs locally, speaks MCP over stdio to your agent client and drives DaVinci Resolve through its
scripting API with your user's permissions. Issues that matter most:

- an operation writing outside its documented folders (`FUSION_MCP_OUT_DIR`, `FUSION_MCP_CACHE_DIR`, Resolve's
  Templates folder when `template.install` is enabled);
- a way around the guard rails: `FUSION_MCP_READONLY`, `FUSION_MCP_ALLOW_CATEGORIES`,
  `FUSION_MCP_PROJECT_ALLOWLIST` or the default-off `eval.*` operations;
- code execution through crafted comp, `.setting` or scene files.

## Safe use

- Set `FUSION_MCP_PROJECT_ALLOWLIST` to a scratch project while you evaluate the tools.
- Leave `FUSION_MCP_ENABLE_EVAL` unset unless you need it: it lets the agent run Python or Lua inside Resolve.
- Treat comps, `.setting` files and scene descriptions from others like code, and open them in a scratch
  project first.
