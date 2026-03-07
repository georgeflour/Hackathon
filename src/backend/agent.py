import os
import logging
import sys
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()
logger = logging.getLogger("agent")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(ch)
    logger.propagate = True


PROJECT_ENDPOINT = "https://hacktothefuture-resource.services.ai.azure.com/api/projects/hacktothefuture"
AGENT_NAME = "dei-workflow"


def ask_agent(prompt: str) -> str:
    """
    Sends prompt to Azure AI Foundry workflow/agent and returns the response.
    """
    logger.info("Calling Microsoft Foundry agent/workflow: %s", AGENT_NAME)

    conversation = None
    try:
        project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )

        with project_client:
            openai_client = project_client.get_openai_client()

            # Create a new conversation for this request
            conversation = openai_client.conversations.create()
            logger.info("Created conversation id=%s", conversation.id)

            # Note: We use 'agent_reference' in extra_body as verified by testing
            response = openai_client.responses.create(
                conversation=conversation.id,
                input=prompt,
                extra_body={
                    "agent_reference": {
                        "name": AGENT_NAME,
                        "type": "agent_reference",
                    }
                },
                stream=False,
                metadata={"x-ms-debug-mode-enabled": "1"},
            )

            # Try to get output_text directly from the response object
            final_text = getattr(response, "output_text", None)
            
            # If output_text is empty or not available, extract from the response message list
            if not final_text and hasattr(response, "output"):
                text_parts = []
                for msg in response.output:
                    if msg.type == "message" and msg.role == "assistant" and msg.content:
                        for content_item in msg.content:
                            if content_item.type == "output_text":
                                text_parts.append(content_item.text)
                final_text = "".join(text_parts)

            # Clean up potential "WEB" prefix which sometimes appears in orchestrator responses
            if final_text and final_text.startswith("WEB"):
                final_text = final_text[3:]

            if not final_text:
                final_text = "Λυπάμαι, δεν έλαβα απάντηση από το workflow."

            logger.info("Workflow execution completed successfully.")
            return final_text.strip()

    except Exception as e:
        logger.exception("Error executing workflow: %s", e)
        return "Λυπάμαι, υπήρξε πρόβλημα επικοινωνίας με το workflow."

    finally:
        # Cleanup: Delete the conversation to avoid cluttering the project
        if conversation is not None:
            try:
                with AIProjectClient(
                    endpoint=PROJECT_ENDPOINT,
                    credential=DefaultAzureCredential(),
                ) as cleanup_client:
                    cleanup_client.get_openai_client().conversations.delete(conversation_id=conversation.id)
                    logger.info("Conversation deleted")
            except Exception as cleanup_error:
                logger.warning("Failed to delete conversation: %s", cleanup_error)