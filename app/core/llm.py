import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.client = None
        self.model = settings.LLM_MODEL

        # Determine API key (primarily OpenRouter)
        api_key = settings.OPENROUTER_API_KEY

        if api_key:
            try:
                import httpx

                self.client = OpenAI(
                    base_url=settings.LLM_BASE_URL,
                    api_key=api_key,
                    default_headers={
                        "HTTP-Referer": "http://localhost:8501",  # Required by OpenRouter
                        "X-Title": "Property Guardian AI",  # Required by OpenRouter
                    },
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def extract_metadata(self, text: Optional[str]) -> Dict[str, Any]:
        if not self.client:
            return {}

        # Truncate to avoid context limit if not using full VL yet, though this model has 128k context.
        # For simple text extraction, 4k-8k is usually plenty for the header info.
        truncated_text = ""
        if text:
            # Iterative truncation to avoid slicing issues
            limit_val = 16000
            if len(text) > limit_val:
                trunc_chars: List[str] = []
                c_idx = 0
                for c in text:
                    if c_idx >= limit_val:
                        break
                    trunc_chars.append(str(c))
                    c_idx += 1
                truncated_text = "".join(trunc_chars)
            else:
                truncated_text = text
        prompt = f"""
        Analyze the following document text and extract property details.
        
        **Goal**: Extract structured metadata for a Property Fraud Detection System.
        
        **Instructions**:
        1. **Analyze the Structure**: Look for headers, tables, or key-value pairs (e.g., "Village: X", "Mouza - Y").
        2. **Identify Synonyms**:
           - "Village" might be called "Mouza", "Revenue Village", or "Town".
           - "Tehsil" might be "Taluka", "Mandal", "Sub-District".
           - "District" might be "Zilla".
           - "Buyer" might be "Transferee", "Purchaser", "Second Party".
           - "Seller" might be "Transferor", "Vendor", "First Party".
3. **Extract Keys**:
           - State, District, Tehsil, Village (Name), Plot No, House No.
           - Seller Name, Buyer Name.
           - Registration Date (YYYY-MM-DD).
        4. **Handling Missing Data**: If a specific field is not clearly present, set it to "Unknown".
        5. **Clean Names**: Extract ONLY the person's name. Remove PAN numbers, Aadhaar, or text like "(Seller)" or "(Buyer)".
        
        **Return Format**:
        Return ONLY a JSON object with these exact keys:
        {{
            "state": "...",
            "district": "...",
            "tehsil": "...",
            "village": "...",
            "plot_no": "...",
            "house_no": "...",
            "seller_name": "...",
            "buyer_name": "...",
            "seller_aadhaar": "...",
            "seller_pan": "...",
            "buyer_aadhaar": "...",
            "buyer_pan": "...",
            "registration_date": "..."
        }}

        **Document Text (Truncated)**:
        {truncated_text} 
        """

        client = self.client
        if not client:
            return {}

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=512,
                stream=False,
                timeout=120.0,
            )
            content = completion.choices[0].message.content
            if not content:
                content = "{}"
            # Clean up potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except Exception as e:
            logger.warning(f"LLM Extraction failed: {e}")
            return {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def nl_to_query_params(self, nl_query: str) -> dict:
        if not self.client:
            return {}

        prompt = f"""
        Analyze the following property search query and extract search parameters.
        Return ONLY a JSON object with keys:
        village, plot_no, district, seller_name, buyer_name.
        If a parameter is not mentioned, exclude it or set to null.
        NOTE: "plot_no" should include "Plot", "Survey", "Gat", "Gut", "Khewat", or "Khatauni" numbers.
        
        Query: "{nl_query}"
        """

        client = self.client
        if not client:
            return {}

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=512,
                timeout=10.0,
            )
            content = completion.choices[0].message.content
            if not content:
                content = "{}"
            # Clean up
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except Exception as e:
            logger.warning(f"LLM Query Parsing failed: {e}")
            return {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_response(
        self,
        context: str,
        question: str,
        history_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple:
        client = self.client
        if not client:
            return "AI model is not configured.", None

        from datetime import datetime

        current_date_str = datetime.now().strftime("%Y-%m-%d")

        messages = history_messages if history_messages else []

        system_prompt = f"""
        You are a helpful assistant for a Property Guardian (AI-powered Real Estate Security System).
        Today's Date: {current_date_str}
        
        1. AUTHORITATIVE CONTEXT: Use the "Context" section below as your primary source of truth for property facts.
        2. CONVERSATIONAL AWARENESS: You can use the "Conversation History" (if provided) to handle follow-up questions or meta-questions like "What did we just talk about?".
        3. FALLBACK: If the question asks for property data NOT in the context, say "I couldn't find relevant information in the documents."
        
        Context:
        {context}
        """

        # Ensure system prompt is at the start
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": question})

        client = self.client
        if not client:
            return "AI model is not configured.", None

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=250,
                stream=False,
                timeout=120.0,
                extra_body={"reasoning": {"enabled": True}},
            )
            message = completion.choices[0].message
            content = (
                message.content.strip()
                if message.content
                else "OpenRouter API limits reached or AI response was empty."
            )
            # Extract reasoning_details if present (OpenRouter specific)
            reasoning_details = getattr(message, "reasoning_details", None)

            return content, reasoning_details
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            logger.error(
                f"LLM Response Generation failed: {type(e).__name__}: {e}\n{error_trace}"
            )
            return f"Error: {str(e)}", None


llm_client = LLMClient()
