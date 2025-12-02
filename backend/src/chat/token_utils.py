"""
Token calculation utilities for chat messages
"""
import tiktoken
from typing import List
from .models import ChatMessage


class TokenCounter:
    """Token counter for chat messages using tiktoken"""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize token counter with specified encoding
        
        Args:
            encoding_name: Encoding name for tiktoken (default: cl100k_base for GPT-3.5/GPT-4)
        """
        self.encoding_name = encoding_name
        # Pre-initialize encoding to avoid repeated creation
        self._encoding = tiktoken.get_encoding(encoding_name)
    
    def count_text_tokens(self, text: str) -> int:
        """
        Count tokens in a text string
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if text is None:
            return 0
        if not isinstance(text, str):
            if isinstance(text, list):
                text = " ".join(str(part) for part in text)
            else:
                text = str(text)
        if not text:
            return 0
        return len(self._encoding.encode(text))
    
    def count_message_tokens(self, message: ChatMessage) -> int:
        """
        Count tokens for a single chat message
        
        This includes both the role identifier and content tokens.
        The exact token count may vary by model, but this provides
        a reasonable approximation.
        
        Args:
            message: ChatMessage to count tokens for
            
        Returns:
            Approximate token count for the message
        """
        # Role tokens (e.g., "user:", "assistant:", "system:")
        role_tokens = self.count_text_tokens(f"{message.role.value}:")
        
        # Content tokens
        content_tokens = self.count_text_tokens(message.content)
        
        # Add a small overhead for message formatting
        # This accounts for any additional tokens used in message structure
        formatting_overhead = 3
        
        return role_tokens + content_tokens + formatting_overhead
    
    def count_messages_tokens(self, messages: List[ChatMessage]) -> int:
        """
        Count total tokens for a list of chat messages
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            Total token count for all messages
        """
        if not messages:
            return 0
        
        total_tokens = sum(self.count_message_tokens(msg) for msg in messages)
        
        # Add additional overhead for conversation structure
        # This accounts for any tokens used in conversation-level formatting
        conversation_overhead = 5
        
        return total_tokens + conversation_overhead
    
    def estimate_max_history_messages(
        self,
        fixed_messages: List[ChatMessage],
        max_context_tokens: int,
        max_output_tokens: int,
        safety_ratio: float = 0.9
    ) -> int:
        """
        Estimate maximum number of tokens available for history messages
        
        Args:
            fixed_messages: Fixed messages (system prompt, current input)
            max_context_tokens: Maximum context tokens for the model
            max_output_tokens: Maximum output tokens reserved for response
            safety_ratio: Safety ratio to avoid hitting token limits (default: 0.9)
            
        Returns:
            Maximum tokens available for history messages
        """
        # Calculate available input tokens
        available_input_tokens = max_context_tokens - max_output_tokens
        
        # Apply safety ratio
        safe_input_tokens = int(available_input_tokens * safety_ratio)
        
        # Subtract fixed messages tokens
        fixed_tokens = self.count_messages_tokens(fixed_messages)
        
        # Return available tokens for history
        return max(0, safe_input_tokens - fixed_tokens)


def get_default_token_counter() -> TokenCounter:
    """Get a default token counter instance"""
    return TokenCounter()