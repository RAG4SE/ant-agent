# Ant Agent

**Ant Agent** is a LangChain-based LLM agent for general purpose software engineering tasks. It provides a powerful CLI interface that can understand natural language instructions and execute complex software engineering workflows using various tools and LLM providers.

This is a rewrite of [Trae Agent](https://github.com/bytedance/trae-agent) using LangChain for better extensibility and integration with the LangChain ecosystem.

## ✨ Features

- 🧠 **LangChain-based**: Built on LangChain for better extensibility
- 🤖 **Multi-LLM Support**: Works with OpenAI, Anthropic, DeepSeek, Google Gemini, Ollama, and more
- 🛠️ **Rich Tool Ecosystem**: File editing, bash execution, sequential thinking, and more
- 🎯 **Interactive Mode**: Conversational interface for iterative development
- 📊 **Trajectory Recording**: Detailed logging of all agent actions for debugging and analysis
- ⚙️ **Flexible Configuration**: YAML-based configuration with environment variable support
- 🚀 **Easy Installation**: Simple pip-based installation

## 🚀 Installation

### Requirements
- Python 3.11+
- API key for your chosen provider (OpenAI, Anthropic, Google, etc.)

### Setup

```bash
git clone <ant-agent-repo>
cd ant-agent
pip install -e .
```

## ⚙️ Configuration

1. Copy the example configuration file:
   ```bash
   cp ant_config.yaml.example ant_config.yaml
   ```

2. Edit `ant_config.yaml` with your API credentials and preferences:

```yaml
agents:
  ant_agent:
    enable_lakeview: true
    model: ant_agent_model
    max_steps: 200
    tools:
      - bash
      - edit_tool
      - create_file
      - sequential_thinking
      - task_done

models:
  ant_agent_model:
    model_provider: openai
    model: gpt-4
    max_tokens: 4096
    temperature: 0.5

model_providers:
  openai:
    api_key: your_openai_api_key
  anthropic:
    api_key: your_anthropic_api_key
```

## 📖 Usage

### Basic Commands

```bash
# Simple task execution
ant-cli run "Create a hello world Python script"

# Check configuration
ant-cli show-config

# Interactive mode
ant-cli interactive
```

### Provider-Specific Examples

```bash
# OpenAI
ant-cli run "Fix the bug in main.py" --provider openai --model gpt-4

# Anthropic
ant-cli run "Add unit tests" --provider anthropic --model claude-3-sonnet

# DeepSeek
ant-cli run "Debug this issue" --provider deepseek --model deepseek-chat
```

### Advanced Options

```bash
# Custom working directory
ant-cli run "Add tests for utils module" --working-dir /path/to/project

# Save execution trajectory
ant-cli run "Debug authentication" --trajectory-file debug_session.json

# Interactive mode with custom settings
ant-cli interactive --provider openai --model gpt-4 --max-steps 30
```

## 🛠️ Available Tools

Ant Agent provides a comprehensive toolkit for software engineering tasks:

- **bash**: Execute bash commands and scripts
- **edit_tool**: Edit files using precise string replacement
- **create_file**: Create new files with specified content
- **sequential_thinking**: Think step-by-step to solve complex problems
- **task_done**: Mark tasks as completed with summaries

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

This project is inspired by and based on [Trae Agent](https://github.com/bytedance/trae-agent) from ByteDance, rewritten using LangChain for better extensibility.