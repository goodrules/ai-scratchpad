from google.adk import Agent

# 1. Define the tool
def convert_temperature(value: float, from_scale: str, to_scale: str) -> float:
    """Converts temperatures between 'C', 'F', and 'K'."""
    # Validate inputs
    if not from_scale or not to_scale:
        raise ValueError("Scale parameters cannot be empty")

    # Normalize inputs to first letter uppercase (e.g. 'fahrenheit' -> 'F')
    from_scale = from_scale[0].upper()
    to_scale = to_scale[0].upper()

    # Validate scale types
    if from_scale not in ['C', 'F', 'K'] or to_scale not in ['C', 'F', 'K']:
        raise ValueError("Scales must be 'C', 'F', or 'K'")

    if from_scale == to_scale:
        return value

    # Normalize to Celsius
    celsius = value
    if from_scale == 'F':
        celsius = (value - 32) * 5 / 9
    elif from_scale == 'K':
        celsius = value - 273.15

    # Convert to target
    if to_scale == 'F':
        return (celsius * 9 / 5) + 32
    elif to_scale == 'K':
        return celsius + 273.15
    return celsius

# 2. Register it
root_agent = Agent(
    name="utility_agent",
    model="gemini-3.7-flash",
    instruction="You are a utility assistant. Use 'convert_temperature' to answer queries. Understand that 'F' and 'Fahrenheit', 'C' and 'Celsius', 'K' and 'Kelvin' are interchangeable.",
    tools=[convert_temperature]
    # Note: 'description' parameter is primarily used for multi-agent routing
)
