# Summer Core Documentation

This directory contains the documentation for the Summer Core framework.

## Documentation Structure

The documentation is organized into the following sections:

- **Overview**: Introduction to the framework, getting started guide, and architecture overview
- **Core Container**: Documentation for the IoC container, beans, and application context
- **AOP**: Documentation for aspect-oriented programming
- **Event System**: Documentation for the event system
- **Data Access**: Documentation for data access abstractions
- **Integration**: Documentation for integration with other technologies
- **Testing**: Documentation for testing support
- **API Reference**: Automatically generated API documentation

## Building the Documentation

To build the documentation:

```bash
make docs-test
```

To serve the documentation locally:

```bash
make docs
```

To publish the documentation to GitHub Pages:

```bash
make docs-publish
```

## Creating New Documentation

To create documentation for a new module:

```bash
make docs-new-module
```

To create a new documentation file:

```bash
make docs-new-file
```

## Documentation Standards

Please follow the documentation standards outlined in the [Documentation Workflow](.kiro/steering/documentation-workflow.md) steering document.

## Contributing

Contributions to the documentation are welcome! Please follow the documentation standards and submit a pull request with your changes.