# Documentation Index

Complete documentation for WinGet Package Updater.

## Getting Started

**New here? Start with these:**

1. **[quick-start.md](quick-start.md)** - 5-minute setup guide
   - Fork repositories
   - Configure secrets
   - Add your first package
   - Run the workflow

2. **[contributing.md](contributing.md)** - Adding packages
   - Step-by-step guide
   - Common patterns
   - Best practices

## Reference Documentation

### Configuration

- **[checkver-guide.md](checkver-guide.md)** - Complete checkver configuration reference
  - File naming conventions
  - GitHub-based checkver
  - Script-based checkver
  - Multi-architecture support
  - Troubleshooting

### System Design

- **[architecture.md](architecture.md)** - System architecture
  - 3-stage pipeline
  - Module structure
  - Design patterns
  - Workflow orchestration

### Development

- **[development.md](development.md)** - Developer guide
  - Local setup
  - Testing
  - Debugging
  - Code style

## Additional Resources

### Quick References

- **[../manifests/README.md](../manifests/README.md)** - Checkver quick reference
- **[../.github/workflows/README.md](../.github/workflows/README.md)** - Workflow documentation

### External Links

- [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) - Upstream repository
- [PowerShell Documentation](https://docs.microsoft.com/en-us/powershell/)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Documentation Map

```
docs/
├── README.md              # This file - Documentation index
├── quick-start.md         # 5-minute setup guide
├── contributing.md        # How to add packages
├── checkver-guide.md      # Complete checkver reference
├── architecture.md        # System architecture
└── development.md         # Developer guide

Other locations:
├── manifests/README.md    # Checkver quick reference
└── .github/workflows/README.md  # Workflow documentation
```

## Need Help?

- **Questions?** Open a [discussion](https://github.com/zeldrisho/winget-pkgs-updater/discussions)
- **Bug reports?** Open an [issue](https://github.com/zeldrisho/winget-pkgs-updater/issues)
- **Want to contribute?** See [contributing.md](contributing.md)
