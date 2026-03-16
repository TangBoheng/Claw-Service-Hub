---
name: csv-processor
description: Process and analyze CSV files locally
emoji: 📊
version: 1.0.0
tags: [csv, data, processor]
requires:
  bins: [python]
  env: []
---

# CSV Processor

A tool service for processing CSV files with various operations.

## Usage

```python
from client import ToolServiceClient

client = ToolServiceClient(
    name="csv-processor",
    skill_dir="./examples/csv-processor-skill"
)
await client.connect("ws://localhost:8765")
```

## Supported Methods

### `analyze(file_path)`
Analyze a CSV file and return statistics.

**Parameters:**
- `file_path` (str): Path to the CSV file

**Returns:**
```json
{
  "row_count": 100,
  "column_count": 5,
  "columns": ["name", "age", "city"],
  "sample": [...]
}
```

### `convert(file_path, target_format)`
Convert CSV to other formats (JSON, Excel).

**Parameters:**
- `file_path` (str): Path to the CSV file
- `target_format` (str): Target format, one of: "json", "excel"

**Returns:**
```json
{
  "output_path": "/path/to/output.json",
  "status": "success"
}
```

## Examples

```bash
# Analyze a CSV file
python run.py analyze --file data.csv

# Convert to JSON
python run.py convert --file data.csv --format json
```

## Requirements

- Python 3.8+
- pandas library

## License

MIT
