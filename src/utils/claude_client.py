"""
claude_client.py

Shared wrapper around the Anthropic API client for the MTS system.
All agents must use this module — never instantiate the Anthropic client directly.

Provides:
- Text completion
- Vision-based analysis (PDF pages rendered as images)
"""

import base64
from pathlib import Path

import anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL


class ClaudeClient:
    """
    Thin, reusable wrapper around the Anthropic API client.

    Responsibilities:
    - Maintain a single shared client instance
    - Provide text and vision completion methods
    - Abstract model selection from calling code

    Does NOT handle retry logic, artifact writing, or prompt construction.
    """

    def __init__(self) -> None:
        """Initialize the Anthropic client with the configured API key."""
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def complete_text(self, prompt: str, max_tokens: int = 4096) -> str:
        """
        Send a text-only prompt to Claude and return the response.

        Args:
            prompt: The instruction or question for Claude.
            max_tokens: Maximum tokens allowed in the response.

        Returns:
            The text content of Claude's response.

        Raises:
            anthropic.APIError: If the API call fails.
        """
        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def complete_with_image(self, prompt: str, image_path: Path, max_tokens: int = 2048) -> str:
        """
        Send a prompt with a PNG image to Claude and return the response.

        Used for analyzing PDF pages that have complex layouts, diagrams,
        or tables where text extraction alone is insufficient.

        Args:
            prompt: The instruction or question about the image.
            image_path: Path to a PNG image file to include in the request.
            max_tokens: Maximum tokens allowed in the response.

        Returns:
            The text content of Claude's response.

        Raises:
            FileNotFoundError: If the image file does not exist at image_path.
            anthropic.APIError: If the API call fails.
        """
        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: '{image_path}'. "
                "Render the PDF page before calling complete_with_image."
            )

        # Read and base64-encode the image for the API request
        image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")

        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return response.content[0].text
