import os
import logging
from dotenv import load_dotenv
 
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.ai.projects import AIProjectClient
 
load_dotenv()
 
logger = logging.getLogger("agent")
 
# ----------------------------
# ENV CONFIG
# ----------------------------
# Azure configuration
AZURE_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
 
# Use the correct agent name and version
AGENT_NAME = os.getenv("AZURE_AGENT_NAME", "deiAgent")
AGENT_VERSION = os.getenv("AZURE_AGENT_VERSION", "1")
 
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
 
_openai_client = None
 
 
def _get_credential():
    """
    Use DefaultAzureCredential for local development (picks up `az login`).
    """
    logger.info("Using DefaultAzureCredential authentication")
    return DefaultAzureCredential()
 
 
def get_azure_openai_client():
    """
    Lazily initializes Azure OpenAI client.
    """
 
    global _openai_client
 
    if _openai_client is None:
        try:
            if not AZURE_ENDPOINT:
                raise ValueError("AZURE_AI_PROJECT_ENDPOINT not defined in .env")
 
            logger.info(f"Initializing AIProjectClient → {AZURE_ENDPOINT}")
 
            credential = _get_credential()
 
            project_client = AIProjectClient(
                endpoint=AZURE_ENDPOINT,
                credential=credential,
            )
 
            _openai_client = project_client.get_openai_client()
 
            logger.info("Connected to Azure AI Project successfully")
 
        except Exception as e:
            logger.error(f"Azure AI initialization failed: {e}")
            raise RuntimeError("Azure AI Configuration Error") from e
 
    return _openai_client
 
 
def ask_agent(prompt: str) -> str:
    """
    Sends prompt to Azure deiAgent and returns the response.
    """
 
    client = get_azure_openai_client()
 
    try:
        response = client.responses.create(
            input=[{"role": "user", "content": prompt}],
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME,
                    "version": AGENT_VERSION,
                    "type": "agent_reference",
                }
            },
        )
 
        return response.output_text
 
    except Exception as e:
        logger.error(f"Error querying deiAgent: {e}")
 
        return (
            "Λυπάμαι, υπήρξε πρόβλημα επικοινωνίας με τον Assistant αυτή τη στιγμή. "
            "Παρακαλώ δοκιμάστε ξανά αργότερα."
        )
 
 
# if __name__ == "__main__":
    # Test script locally
    # print(ask_agent("Hello, how can I help you today?"))