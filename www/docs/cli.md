# CLI Tools

Pydantic2 includes built-in command-line tools that help you interact with your databases and monitor usage.

## Database Viewing

Pydantic2 stores information in two SQLite databases:

1. **Models Database**: Contains information about models, their parameters, and configurations
2. **Usage Database**: Tracks usage statistics, token counts, and costs

You can view these databases using the built-in CLI tools that leverage [Datasette](https://datasette.io/) to provide a web interface for exploring the data.

## Installation

The CLI tools are automatically installed when you install Pydantic2:

```bash
pip install pydantic2
```

## Command Reference

### Main Command

```bash
pydantic2 [OPTIONS]
```

Available options:

| Option | Description |
|--------|-------------|
| `--view-models` | View models database in browser at http://localhost:8001 |
| `--view-usage` | View usage database in browser at http://localhost:8002 |
| `--view-all` | View both databases simultaneously |
| `--help` | Show help message and available options |

### Examples

View models database:
```bash
pydantic2 --view-models
```

View usage statistics:
```bash
pydantic2 --view-usage
```

View both databases:
```bash
pydantic2 --view-all
```

Get help:
```bash
pydantic2 --help
```

## Legacy Commands

For backward compatibility, the following commands are also available:

```bash
pydantic2-view-models
pydantic2-view-usage
pydantic2-view-all
```

## Using Datasette

The web interface provides several powerful features:

1. **SQL Editor**: Run custom SQL queries against your databases
2. **Export**: Download query results in various formats (CSV, JSON, etc.)
3. **Filtering**: Filter table views by column values
4. **Pagination**: Navigate through large datasets

## Database Schema

### Models Database

The models database typically contains tables such as:

- `models`: Information about available models
- `parameters`: Parameters associated with each model
- `capabilities`: Features supported by each model

### Usage Database

The usage database typically contains tables such as:

- `requests`: Individual API requests
- `tokens`: Token usage per request
- `costs`: Cost information per request
- `summary`: Aggregated usage statistics

## Technical Details

The CLI tools are implemented in `pydantic2.utils.cli` and use the Click library to provide a user-friendly command-line interface. The database paths are automatically determined based on the package installation location.

If you need to customize the CLI behavior, you can modify the `cli.py` file or extend it with additional commands.

## Customizing Port Numbers

By default, the databases are served on ports 8001 and 8002. If you need to use different ports, you can modify the `cli.py` file in the package source code.
