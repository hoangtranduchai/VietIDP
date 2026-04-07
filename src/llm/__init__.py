# -*- coding: utf-8 -*-
"""LLM module: Ollama client + prompt templates."""

from src.llm.ollama_client import OllamaClient, summarize_with_ollama
from src.llm.prompts import PROMPTS

__all__ = ["OllamaClient", "summarize_with_ollama", "PROMPTS"]
