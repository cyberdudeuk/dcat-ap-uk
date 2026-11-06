# DCAT-UK AP MCP server

A small [Model Context Protocol](https://modelcontextprotocol.io/) server so an AI assistant can read DCAT-UK AP and check, score,
convert and export records. It runs on your machine, reads only the generated profile, makes no network requests and writes no files.

It uses the portal's own validator (`site_src/validator.js`) and the generated `profile.json`, so its verdicts are the ones the
SHACL shapes and the JSON Schema give. The repository's tests start it and call every tool.

## Run it

```sh
python3 -I tools/build.py            # writes site/downloads/profile.json
node integrations/mcp/server.js      # or: --profile path/to/profile.json
```

Add it to an MCP client as a stdio server with the command `node` and the argument `integrations/mcp/server.js` (use the full path).

## Tools

| Tool | What it does |
|---|---|
| `profile_summary` | Version, status, classes and sector extensions |
| `describe_class` | Every property of a class with its obligation, optionally with extensions |
| `describe_property` | Definition, guidance, kind, codelist, example and where it is used |
| `list_codelist` | The values of a codelist |
| `search` | Find properties, classes and codelists |
| `validate_record` | Errors, warnings, conformance level and quality score |
| `convert_mem` | xGov MEM record to DCAT-UK AP |
| `convert_openapi` | OpenAPI description to a data service record (never copies an email address) |
| `export_record` | Turtle, schema.org or Croissant 1.1 (dataset level) |

DCAT-UK AP is a proposal and is not endorsed. This is not an official service. Licence: MIT.
