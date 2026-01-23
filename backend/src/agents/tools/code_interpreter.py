"""
Code Interpreter Tool
"""
from typing import Any, Optional, Dict
import logging
import asyncio

from .base import AgentTool, AgentToolConfig
from .registry import tool_registry
from src.sandbox.service import get_sandbox_service
from src.files.storage import storage_service

logger = logging.getLogger(__name__)


@tool_registry.register
class CodeInterpreterTool(AgentTool):
    """Tool for running Python code in a safe sandbox"""
    
    def __init__(self, config: Optional[AgentToolConfig] = None, conversation_id: Optional[str] = None):
        super().__init__(config)
        self.conversation_id = conversation_id
        self.sandbox = get_sandbox_service()
    
    @property
    def name(self) -> str:
        return "python_code_interpreter"
    
    @property
    def description(self) -> str:
        return (
            "A Python code interpreter. Use this to execute Python code for calculations, "
            "data analysis, file processing, or any task requiring code execution. "
            "Input should be a valid Python script. "
            "The environment has internet access disabled. "
            "You can assume standard libraries and pandas/numpy are available. "
            "The tool returns stdout, stderr, and exit code. "
            "CRITICAL: You MUST use print() to output any values or results. "
            "Expressions that are not printed will NOT be visible."
        )
    
    async def execute(self, code: str) -> Dict[str, Any]:
        """Execute python code"""
        if not self.conversation_id:
            return {
                "error": "No conversation ID provided. Cannot create sandbox session."
            }
            
        try:
            logger.info(f"Executing code for conversation {self.conversation_id}")
            
            # Simple diff: check files before (optional, optimization)
            # For now, just execute and then look for known patterns or all new files?
            # To be efficient, we can fetch file list before and after.
            existing_files = set(await self.sandbox.list_files(self.conversation_id))
            
            result = await self.sandbox.execute_code(
                conversation_id=str(self.conversation_id),
                code=code
            )
            
            # Check for new files
            current_files_list = await self.sandbox.list_files(self.conversation_id)
            current_files = set(current_files_list)
            new_files = current_files - existing_files
            
            logger.debug(f"DEBUG: Existing Files: {existing_files}")
            logger.debug(f"DEBUG: Current Files List: {current_files_list}")
            logger.debug(f"File diff for {self.conversation_id}: Existing={len(existing_files)}, Current={len(current_files)}, New={new_files}")
            
            # Filter out execution artifacts (uuid.py, .out, .err)
            artifacts = []
            generated_files_output = ""
            
            import uuid
            import io
            
            for filename in new_files:
                # Skip the script itself and logs
                if filename.startswith("exec_") and (filename.endswith(".py") or filename.endswith(".out") or filename.endswith(".err")):
                    continue
                
                # Check for common image/data formats
                # or just download everything that isn't system file
                
                content = await self.sandbox.read_file_bytes(self.conversation_id, filename)
                if content:
                    # Upload to RiceBall Storage
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(filename)
                    if not content_type:
                        content_type = "application/octet-stream"
                    
                    file_id = uuid.uuid4()
                    
                    # Store as session artifact
                    key = await storage_service.upload_file(
                        file_data=io.BytesIO(content),
                        file_type="agent-artifact",
                        file_id=file_id,
                        filename=filename,
                        content_type=content_type,
                        file_size=len(content)
                    )
                    
                    url = await storage_service.get_public_url(key)
                    artifacts.append({
                        "filename": filename,
                        "url": url,
                        "key": key
                    })
                    
                    # If it's an image, embed it
                    if content_type.startswith("image/"):
                        generated_files_output += f"\n![{filename}]({url})\n"
                    else:
                        generated_files_output += f"\n[{filename}]({url})\n"
            
            # Format output for the LLM
            output = ""
            if result.get("stdout"):
                output += f"STDOUT:\n{result['stdout']}\n"
            if result.get("stderr"):
                output += f"STDERR:\n{result['stderr']}\n"
            if result.get("exit_code") != 0:
                output += f"Exit Code: {result['exit_code']}\n"
            
            if generated_files_output:
                 output += "\nGenerated Files:" + generated_files_output
            
            if not output:
                output = "Code executed successfully but with NO OUTPUT. Remember to use print() to see results."
                
            return output
            
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return f"Error executing code: {str(e)}"
