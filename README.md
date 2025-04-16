# tool alchemist

imagine a [goose](https://github.com/block/goose) extension that writes and configures goose extensions. Work in progress. Use at your own risk.

**NOTE**: While this tool will configure the extension in the goose config, currently Goose does not support loading extensions in-session. You will need to restart the session to have access to the extension.

## Tools

- **CreateNewToolBoilerplate**
- **GetToolPath**
- **AddDependency**

## Resources

- **llmcontext://mcpdocs** (get latest mcp sdk docs)

## Configuration

### [Goose](https://github.com/block/goose)

```yaml
extensions:
  tool-alchemist:
    args:
    - --from
    - git+https://github.com/flothjl/tool-alchemist-mcp@main
    - tool-alchemist-mcp
    cmd: uvx
    enabled: true
    envs: {}
    name: tool-alchemist
    type: stdio
```
