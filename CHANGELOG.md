# Changelog

## [2.0.0] (2025-08-22)

## Major Features
- Added Redis caching and Qdrant vector database integration to handle conversation history for the Telegram bot.
- Automatically sends relevant conversation history as context if related to the user query.
- Applied Retrieval-Augmented Generation (RAG) to search and retrieve relevant conversation history for improved long-term memory and semantic context.

### Enhancements
- Improved context handling and relevance scoring for user queries.
- Optimized Redis caching strategy for faster message retrieval.
- Enhanced Qdrant integration for better semantic search capabilities.

### Architecture & Code Quality
- Improved modularity and separation of concerns in the codebase.
- Enhanced testing coverage and introduced new unit tests for critical components.
- Refactored code for better readability and maintainability.

## [1.5.0] - 2025-08-20

### Major Features
- Complete project restructuring for modularity and scalability
- Added MCP-enhanced bot mode with AI-powered natural language understanding and intent detection
- Integrated Model Context Protocol (MCP) for intelligent responses and workflow automation
- Centralized AI instructions and intent guidance for multiple MCP server types
- N8N webhook integration for external workflow automation

### Enhancements
- Improved system monitoring commands and output formatting
- Enhanced photo and document handling with caption and Qdrant support
- Added support for direct natural language commands (e.g., "weather in London", "info", "uptime")
- Improved error handling and logging throughout the codebase
- Updated configuration management and environment variable handling

### Architecture & Code Quality
- Separated code into core, handlers, services, ai, database, utils, middleware, and config modules
- Created migration script for automated import path updates
- Added comprehensive documentation and project structure overview
- Future-ready for additional AI providers, database integrations, authentication, rate limiting, and microservices

### Other
- Added MIT license
- Updated README and project description

---
