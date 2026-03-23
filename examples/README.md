# Examples

This directory contains example services and consumers for Claw Service Hub.

## Service Examples

### 🔌 Provider Services

| Service | Description | Run Command |
|---------|-------------|-------------|
| `weather_service.py` | Weather data from Open-Meteo API | `python examples/weather_service.py` |
| `calculator_service.py` | Basic arithmetic operations | `python examples/calculator_service.py` |
| `csv_processor_skill/` | CSV file processing | See subdirectory |

### 📡 Consumer Examples

| Example | Description | Run Command |
|---------|-------------|-------------|
| `weather_consumer.py` | Consumes weather service | `python examples/weather_consumer.py` |
| `calculator_consumer.py` | Consumes calculator service | `python examples/calculator_consumer.py` |

## Quick Start

### 1. Start the Hub Server

```bash
cd Claw-Service-Hub
python -m server.main
```

### 2. Start a Service Provider

```bash
# Terminal 1: Start weather service
python examples/weather_service.py

# Terminal 2: Start calculator service
python examples/calculator_service.py
```

### 3. Run a Consumer

```bash
# Terminal 3: Run consumer
python examples/weather_consumer.py
python examples/calculator_consumer.py
```

## Running Multiple Services

Each service runs independently and registers with the Hub. You can run multiple services simultaneously:

```bash
# Terminal 1
python examples/weather_service.py

# Terminal 2
python examples/calculator_service.py

# Terminal 3
python -m server.main  # If not already running
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HUB_URL` | `ws://localhost:8765` | WebSocket hub URL |
| `DEFAULT_LOCATION` | `Shanghai` | Default location for weather service |

Example:
```bash
HUB_URL=ws://localhost:8765 python examples/weather_service.py
```

## Creating Your Own Service

See the `calculator_service.py` for a simple template:

1. Create a class with handler methods
2. Use `LocalServiceRunner` to register your service
3. Register handlers for each method
4. Call `runner.run()` to start

See `skills/hub-client/SKILL.md` for complete documentation.