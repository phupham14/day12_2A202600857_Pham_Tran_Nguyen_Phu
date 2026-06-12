"""Mock LLM for local dev — replace with OpenAI/Anthropic when API key is available."""
import time
import random

_RESPONSES = [
    "That's a great question! In production systems, {topic} is handled through proper configuration management and environment variables.",
    "When deploying AI agents, {topic} requires careful consideration of scalability, reliability, and security.",
    "The 12-factor app methodology recommends handling {topic} by separating configuration from code.",
    "In containerized environments, {topic} is typically managed through orchestration tools like Docker Compose or Kubernetes.",
    "Production-ready AI systems address {topic} using structured logging, health checks, and graceful shutdown mechanisms.",
]


def ask(question: str) -> str:
    time.sleep(0.05)  # simulate latency
    topic = question.split()[-1].rstrip("?.!") if question else "this"
    template = random.choice(_RESPONSES)
    return template.format(topic=topic)
