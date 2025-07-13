"""LangChain-powered AI client for message processing."""

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import BaseMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MessageClassification(BaseModel):
    """Structured output for message classification."""

    type: str = Field(
        description="Classification type: incident, knowledge_query, support_request, deployment_help"
    )
    severity: str = Field(description="Severity level: low, medium, high, critical")
    urgency: str = Field(description="Urgency level: low, medium, high")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: Optional[str] = Field(
        description="Brief explanation of the classification"
    )


class KnowledgeResponse(BaseModel):
    """Structured output for knowledge base responses."""

    summary: str = Field(description="Main summary of the information")
    key_points: List[str] = Field(
        description="Key points extracted from the knowledge base"
    )
    source_documents: List[str] = Field(description="Source documents referenced")
    confidence: float = Field(description="Confidence in the response quality")


class LangChainAIClient:
    """LangChain-powered AI client for structured AI interactions."""

    def __init__(self):
        """Initialize the LangChain AI client."""
        self._load_workflow_config()

        if not config.openai_api_key:
            logger.warning("OpenAI API key not configured, using mock responses")
            self._llm = None
        else:
            self._llm = ChatOpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url if config.openai_base_url else None,
                model=config.openai_model,
                temperature=config.openai_temperature,
                max_tokens=config.openai_max_tokens,
                timeout=config.openai_timeout,
                max_retries=2,
            )
            logger.info(
                "LangChain ChatOpenAI initialized",
                model=config.openai_model,
                base_url=config.openai_base_url,
            )

        self._setup_chains()

    def _setup_chains(self):
        """Setup LangChain chains for different tasks."""
        # Classification chain with structured output
        self.classification_parser = PydanticOutputParser(
            pydantic_object=MessageClassification
        )

        classification_template = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(
                    self._build_classification_system_prompt()
                ),
                HumanMessagePromptTemplate.from_template(
                    "Classify this message: {message}\n\n{format_instructions}"
                ),
            ]
        )

        if self._llm:
            self.classification_chain = (
                {
                    "message": RunnablePassthrough(),
                    "format_instructions": lambda _: self.classification_parser.get_format_instructions(),
                }
                | classification_template
                | self._llm
                | self.classification_parser
            )
        else:
            self.classification_chain = None

        # Knowledge response chain
        self.knowledge_parser = PydanticOutputParser(pydantic_object=KnowledgeResponse)

        knowledge_template = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(
                    """
You are a helpful AI assistant that formats knowledge base search results into clear, user-friendly responses.

Guidelines:
1. Extract the most relevant information from the search results
2. Format the response in a clear, readable way
3. Provide a summary and key points
4. List source documents
5. Be concise but comprehensive
6. Use a professional but friendly tone

{format_instructions}
            """
                ),
                HumanMessagePromptTemplate.from_template(
                    """
User asked: "{query}"

Knowledge base search results:
{search_results}

Please format this into a helpful, structured response.
            """
                ),
            ]
        )

        if self._llm:
            self.knowledge_chain = (
                {
                    "query": lambda x: x["query"],
                    "search_results": lambda x: x["search_results"],
                    "format_instructions": lambda _: self.knowledge_parser.get_format_instructions(),
                }
                | knowledge_template
                | self._llm
                | self.knowledge_parser
            )
        else:
            self.knowledge_chain = None

        # General response chain
        general_template = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(
                    """
You are an AI support assistant. Provide helpful, concise, and professional responses.
Consider the context and classification when responding.
            """
                ),
                HumanMessagePromptTemplate.from_template(
                    """
Message: {message}
Classification: {classification}
Context: {context}

Provide a helpful response:
            """
                ),
            ]
        )

        if self._llm:
            self.general_chain = general_template | self._llm
        else:
            self.general_chain = None

    async def classify_message(self, message: str) -> Dict[str, Any]:
        """Classify a message using structured LangChain output."""
        logger.info("Classifying message with LangChain", model=config.openai_model)

        if not self.classification_chain:
            logger.warning("LangChain not initialized, using mock response")
            return self._get_mock_classification_response()

        try:
            result = await self.classification_chain.ainvoke(message)

            logger.info(
                "Message classified successfully with LangChain",
                type=result.type,
                severity=result.severity,
                confidence=result.confidence,
            )

            return {
                "type": result.type,
                "severity": result.severity,
                "urgency": result.urgency,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
            }

        except Exception as e:
            logger.exception("Error classifying message with LangChain", error=str(e))
            return {"type": "unknown", "severity": "unknown", "confidence": 0.0}

    async def generate_knowledge_response(
        self, user_query: str, search_results: str
    ) -> str:
        """Generate a structured knowledge response using LangChain."""
        if not self.knowledge_chain:
            return self._get_mock_knowledge_response(search_results)

        try:
            result = await self.knowledge_chain.ainvoke(
                {"query": user_query, "search_results": search_results}
            )

            # Format the structured response into user-friendly text
            response_parts = [f"📚 **{result.summary}**\n"]

            if result.key_points:
                response_parts.append("**Key Points:**")
                for point in result.key_points:
                    response_parts.append(f"• {point}")
                response_parts.append("")

            if result.source_documents:
                sources = ", ".join(result.source_documents)
                response_parts.append(f"*Sources: {sources}*")

            response_parts.append("\nNeed more help? Feel free to ask!")

            formatted_response = "\n".join(response_parts)

            logger.info(
                "Knowledge response generated with LangChain",
                query=user_query,
                confidence=result.confidence,
                key_points_count=len(result.key_points),
                response_length=len(formatted_response),
            )

            return formatted_response

        except Exception as e:
            logger.error(
                "Error generating knowledge response with LangChain",
                query=user_query,
                error=str(e),
            )
            return self._get_mock_knowledge_response(search_results)

    async def generate_response(
        self,
        message: str,
        classification: Dict[str, Any],
        context: Optional[Dict] = None,
    ) -> str:
        """Generate a general response using LangChain."""
        if not self.general_chain:
            return self._get_mock_response_generation()

        try:
            result = await self.general_chain.ainvoke(
                {
                    "message": message,
                    "classification": json.dumps(classification),
                    "context": json.dumps(context) if context else "None",
                }
            )

            response = result.content if hasattr(result, "content") else str(result)
            logger.info("General response generated with LangChain")
            return response

        except Exception as e:
            logger.exception("Error generating response with LangChain", error=str(e))
            return (
                "I apologize, but I'm having trouble processing your request right now."
            )

    def _load_workflow_config(self):
        """Load workflow configuration from flow.yaml."""
        try:
            workflow_file = Path("config/flow.yaml")
            if workflow_file.exists():
                with open(workflow_file, "r") as f:
                    self.flow_config = yaml.safe_load(f)
                logger.info(
                    "Loaded workflow config for LangChain classification",
                    workflows=len(self.flow_config.get("workflows", [])),
                )
            else:
                logger.warning(
                    "flow.yaml not found, using default classification types"
                )
                self.flow_config = {"workflows": []}
        except Exception as e:
            logger.error("Error loading workflow config", error=str(e))
            self.flow_config = {"workflows": []}

    def _build_classification_system_prompt(self) -> str:
        """Build system prompt for classification with workflow context."""
        # Extract classification types from workflows
        classification_types = set()
        severity_values = set()
        urgency_values = set()

        for workflow in self.flow_config.get("workflows", []):
            trigger_conditions = workflow.get("trigger_conditions", {})

            if "classification_type" in trigger_conditions:
                classification_types.add(trigger_conditions["classification_type"])

            if "severity" in trigger_conditions:
                severity_list = trigger_conditions["severity"]
                if isinstance(severity_list, list):
                    severity_values.update(severity_list)
                else:
                    severity_values.add(severity_list)

            if "urgency" in trigger_conditions:
                urgency_list = trigger_conditions["urgency"]
                if isinstance(urgency_list, list):
                    urgency_values.update(urgency_list)
                else:
                    urgency_values.add(urgency_list)

        # Fallback to defaults
        if not classification_types:
            classification_types = {
                "incident",
                "knowledge_query",
                "support_request",
                "deployment_help",
            }
        if not severity_values:
            severity_values = {"low", "medium", "high", "critical"}
        if not urgency_values:
            urgency_values = {"low", "medium", "high"}

        types_list = " | ".join(sorted(classification_types))
        severity_list = " | ".join(sorted(severity_values))
        urgency_list = " | ".join(sorted(urgency_values))

        return f"""You are an expert message classifier for an IT support system. 

Classify messages into these exact types based on configured workflows:
- Classification Types: {types_list}
- Severity Levels: {severity_list}  
- Urgency Levels: {urgency_list}

Classification Guidelines:
• "incident" - System outages, production issues, critical failures, servers down
• "knowledge_query" - Questions asking for information, how-to guides, documentation
• "support_request" - Help requests, user issues, non-critical problems
• "deployment_help" - Deployment questions, release help, deployment guides

Always provide a confidence score and brief reasoning for your classification.
Use "low" as default for severity/urgency if not clearly specified."""

    def _get_mock_classification_response(self) -> Dict[str, Any]:
        """Mock classification response for testing."""
        return {
            "type": "support_request",
            "severity": "low",
            "urgency": "low",
            "confidence": 0.8,
            "reasoning": "Mock response - LangChain not available",
        }

    def _get_mock_knowledge_response(self, search_results: str) -> str:
        """Mock knowledge response for testing."""
        return f"📚 **Mock Knowledge Response**\n\nBased on the search results:\n{search_results}\n\n*This is a mock response - LangChain not available*"

    def _get_mock_response_generation(self) -> str:
        """Mock general response for testing."""
        return "I understand your request. How can I help you further? (Mock response - LangChain not available)"
