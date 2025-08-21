# Local MCP Processing Setup Guide

## Overview
The Telegram bot now supports local pre-processing of Dynamic Tool requests using Ollama with the deepseek-r1:7b model. This provides immediate, high-quality responses without depending on external webhooks.

## Setup Instructions

### 1. Install Ollama
```bash
# macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Or via brew
brew install ollama
```

### 2. Start Ollama Server
```bash
ollama serve
```

### 3. Install deepseek-r1:7b Model
```bash
ollama pull deepseek-r1:7b
```

### 4. Verify Installation
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test the model
ollama run deepseek-r1:7b "Hello, can you help me write a Python script to show Hello World?"
```

## How It Works

### 1. Intent Detection
- User sends: "create a Python to calculate cylinder volume and surface area"
- MCP processor detects: `DYNAMIC_TOOL` intent with `python` tool type

### 2. Local Processing Attempt
- System checks if Ollama is available at `localhost:11434`
- If available, sends enhanced prompt to deepseek-r1:7b model
- Model generates code using MCP instructions
- System attempts safe execution for mathematical calculations

### 3. Response Flow
```
User Query → Intent Detection → Local Ollama Processing → Immediate Response
                              ↓
                         Also sent to N8N webhook for additional processing
```

### 4. Safety Features
- Code execution is sandboxed in temporary directory
- Only mathematical/calculation scripts are auto-executed
- Dangerous operations (file I/O, system commands) are blocked
- 10-second execution timeout

## Example Responses

### Successful Local Processing
```
🛠️ Dynamic Tool Creation - Local Processing

🤖 AI Response (deepseek-r1:7b):
I'll create a Python script to calculate the surface area and volume of a cylinder...

✅ Execution Result:
Volume: 452.389 cubic units
Surface Area: 377.0 square units

🚀 Also sent to external MCP system for additional processing!
```

### Fallback to Webhook
```
🛠️ Dynamic Tool Creation

📝 Request: create a Python script...
🔧 Tool Type: python

⚡ Local processing: Ollama not available
🚀 Sending to external MCP system for processing...
```

## Benefits

1. **Immediate Response**: No waiting for external webhook processing
2. **Offline Capability**: Works even when N8N/external systems are down
3. **Cost Effective**: Uses local model instead of API calls
4. **Privacy**: Sensitive requests processed locally
5. **Dual Processing**: Still sends to webhook for comprehensive handling

## Testing

Run the test script to verify local processing:
```bash
python test_local_mcp.py
```

## Troubleshooting

### Ollama Not Available
```
❌ LOCAL PROCESSING FAILED
🔍 Error: Ollama not available
```
**Solution**: Start Ollama server with `ollama serve`

### Model Not Found
```
Model deepseek-r1:7b not found
```
**Solution**: Install model with `ollama pull deepseek-r1:7b`

### Connection Refused
```
Failed to check Ollama availability: Connection refused
```
**Solution**: Ensure Ollama is running on localhost:11434

## Configuration

The local processor can be configured in `src/ai/local_mcp_processor.py`:
- Model name: Change `model_name` parameter
- Base URL: Modify `base_url` for different Ollama instance
- Safety checks: Adjust `dangerous_keywords` list
- Execution timeout: Modify timeout value in `_try_execute_safe_code`
