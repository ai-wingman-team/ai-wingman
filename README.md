# AI Wingman

Personal AI assistant with context memory using RAG (Retrieval-Augmented Generation).

## Overview

AI Wingman stores Slack conversations in a local PostgreSQL database with vector embeddings, enabling intelligent context-aware responses using local LLM inference.

## Project Structure

- **src/ai_wingman/** - Main Python package
  - **database/** - Database models and connections
  - **storage/** - Context storage with embeddings
  - **retrieval/** - Query generation and search
  - **generation/** - LLM response generation
  - **integrations/** - Slack API integration
- **config/** - Application configuration
- **data/** - Local data storage
  - **raw/** - Raw Slack data
  - **processed/** - Processed embeddings
- **tests/** - Test suite

## Tech Stack (Planned)

- **Database:** PostgreSQL with pgvector extension
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **LLM:** Ollama (local inference)
- **Integration:** Slack SDK for Python

## Setup (Coming Soon)

Setup instructions will be added as development progresses.

