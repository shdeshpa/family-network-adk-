"""Async HTTP client for FastMCP Input Server."""

import httpx
import json
from typing import Optional, Dict, Any


class InputMCPClient:
    """Async HTTP client for calling Input MCP server tools."""

    def __init__(self, base_url: str = "http://localhost:8003"):
        """
        Initialize the MCP client.

        Args:
            base_url: Base URL of the MCP server (default: http://localhost:8003)
        """
        self.base_url = base_url
        self.client = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(timeout=120.0)  # 2 minute timeout
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def process_text_input(
        self,
        text: str,
        context_person_id: Optional[int] = None,
        context_person_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process text input to create or edit family members.

        Args:
            text: Natural language text
            context_person_id: Optional person ID for editing context
            context_person_name: Optional person name for editing context

        Returns:
            dict with processing results
        """
        # For FastMCP, we call the Python function directly via HTTP
        # The endpoint format is /tools/{tool_name}
        payload = {
            "text": text,
            "context_person_id": context_person_id,
            "context_person_name": context_person_name
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/tools/process_text_input",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            return result
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"MCP HTTP error: {e.response.status_code} - {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"MCP call failed: {str(e)}"
            }

    async def process_audio_input(
        self,
        audio_file_path: str,
        context_person_id: Optional[int] = None,
        context_person_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process audio input to create or edit family members.

        Args:
            audio_file_path: Path to audio file
            context_person_id: Optional person ID for editing context
            context_person_name: Optional person name for editing context

        Returns:
            dict with processing results
        """
        payload = {
            "audio_file_path": audio_file_path,
            "context_person_id": context_person_id,
            "context_person_name": context_person_name
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/tools/process_audio_input",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            return result
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"MCP HTTP error: {e.response.status_code} - {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"MCP call failed: {str(e)}"
            }

    async def get_input_help(self) -> Dict[str, Any]:
        """
        Get help and examples for using input tools.

        Returns:
            dict with help information
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/get_input_help",
                json={},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            return result
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"MCP HTTP error: {e.response.status_code} - {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"MCP call failed: {str(e)}"
            }

    async def health_check(self) -> bool:
        """
        Check if MCP server is running and responsive.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            return False


# Convenience function for one-off calls
async def call_text_input(
    text: str,
    context_person_id: Optional[int] = None,
    context_person_name: Optional[str] = None,
    server_url: str = "http://localhost:8003"
) -> Dict[str, Any]:
    """
    Convenience function to process text input.

    Args:
        text: Natural language text
        context_person_id: Optional person ID for editing context
        context_person_name: Optional person name for editing context
        server_url: MCP server URL

    Returns:
        dict with processing results
    """
    async with InputMCPClient(server_url) as client:
        return await client.process_text_input(text, context_person_id, context_person_name)


async def call_audio_input(
    audio_file_path: str,
    context_person_id: Optional[int] = None,
    context_person_name: Optional[str] = None,
    server_url: str = "http://localhost:8003"
) -> Dict[str, Any]:
    """
    Convenience function to process audio input.

    Args:
        audio_file_path: Path to audio file
        context_person_id: Optional person ID for editing context
        context_person_name: Optional person name for editing context
        server_url: MCP server URL

    Returns:
        dict with processing results
    """
    async with InputMCPClient(server_url) as client:
        return await client.process_audio_input(audio_file_path, context_person_id, context_person_name)
