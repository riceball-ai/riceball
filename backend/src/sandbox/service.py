"""
Sandbox Service - Manages Docker containers for code execution.
This is the default 'Managed' implementation using aiodocker.
"""
import logging
import io
import tarfile
import uuid
from typing import Dict, Any, Optional
import aiodocker
from aiodocker.exceptions import DockerError

from src.config import settings

logger = logging.getLogger(__name__)

class SandboxService:
    """
    Manages lightweight Docker containers for Python code execution.
    Maintains a mapping of conversation_id -> container_id.
    """
    
    # In-memory mapping removed, relying on Docker container names
    
    def __init__(self):
        self._docker: Optional[aiodocker.Docker] = None
    
    @property
    def docker(self) -> aiodocker.Docker:
        """Lazy load docker client"""
        # ... (keep existing implementation)
        if self._docker is None:
             logger.debug("Initializing aiodocker client...")
             try:
                 self._docker = aiodocker.Docker()
                 logger.debug("aiodocker client initialized successfully")
             except Exception as e:
                 logger.error(f"Failed to initialize aiodocker client: {e}")
                 raise
        return self._docker
        
    async def close(self):
        if self._docker:
            await self._docker.close()
            self._docker = None

    async def get_or_create_session(self, conversation_id: str) -> str:
        """Get existing container ID or create a new one"""

        container_name = f"riceball-sandbox-{conversation_id}"
        
        try:
            # Try to find by name
            container = await self.docker.containers.get(container_name)
            info = await container.show()
            
            if info['State']['Running']:
                return container.id
            else:
                # Exists but stopped/exited, cleanup
                await self._remove_container(container.id)
        except DockerError as e:
            if e.status != 404:
                # Real error?
                logger.warning(f"Error checking container {container_name}: {e}")
            # If 404, it means not found, proceed to create
            pass
        
        return await self._create_container(conversation_id, container_name)
    
    async def _create_container(self, conversation_id: str, container_name: str) -> str:
        """Start a new sandbox container"""
        try:
            # Parse memory limit
            mem_limit = 512 * 1024 * 1024
            if isinstance(settings.SANDBOX_MEMORY_LIMIT, str):
                s = settings.SANDBOX_MEMORY_LIMIT.lower()
                if s.endswith('g'):
                    mem_limit = int(float(s[:-1]) * 1024 * 1024 * 1024)
                elif s.endswith('m'):
                    mem_limit = int(float(s[:-1]) * 1024 * 1024)

            config = {
                "Image": settings.SANDBOX_IMAGE_NAME,
                "Cmd": ["sleep", "infinity"],
                "HostConfig": {
                    "Memory": mem_limit,
                    "NanoCpus": int(settings.SANDBOX_CPU_LIMIT * 1e9),
                    "NetworkMode": "none" if not settings.SANDBOX_ENABLE_NETWORK else "bridge",
                },
                "WorkingDir": settings.SANDBOX_WORK_DIR,
                "User": "sandbox",
                "Tty": False,
                "OpenStdin": False
            }
            
            # Use fixed name
            container = await self.docker.containers.create(config=config, name=container_name)
            await container.start()
            
            logger.info(f"Started sandbox {container.id[:8]} (name={container_name}) for {conversation_id}")
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to create sandbox container: {e}")
            raise

    async def _remove_container(self, container_id: str):
        try:
            container = await self.docker.containers.get(container_id)
            await container.delete(force=True)
        except Exception:
            pass

    async def execute_code(self, conversation_id: str, code: str) -> Dict[str, Any]:
        """
        Execute Python code in the sandbox.
        """
        container_id = await self.get_or_create_session(conversation_id)
        container = await self.docker.containers.get(container_id)
        
        filename = f"exec_{uuid.uuid4().hex[:8]}.py"
        
        # 1. Upload code
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            data = code.encode('utf-8')
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            info.mtime = 0 
            tar.addfile(info, io.BytesIO(data))
        tar_stream.seek(0)
        
        await container.put_archive(path=settings.SANDBOX_WORK_DIR, data=tar_stream)
        
        # 2. Execute via file redirection
        run_cmd = f"python {filename} > {filename}.out 2> {filename}.err"
        
        exec_instance = await container.exec(
            cmd=["/bin/sh", "-c", run_cmd],
            workdir=settings.SANDBOX_WORK_DIR,
            user="sandbox"
        )
        
        # Start and wait
        try:
            async with exec_instance.start(detach=False) as stream:
                # Need to read stream with aiodocker < 0.21 or > 0.14
                if hasattr(stream, 'read_out'):
                    await stream.read_out()
                elif hasattr(stream, 'read'):
                    # Some versions return Stream which we iterate or read
                    await stream.read()
                elif hasattr(stream, '__aiter__'):
                     async for _ in stream: pass
        except Exception:
            pass
        
        # Inspect for exit code
        exec_info = await exec_instance.inspect()
        exit_code = exec_info.get("ExitCode")
        
        # 3. Read output files
        stdout = await self._read_file(container, f"{filename}.out")
        stderr = await self._read_file(container, f"{filename}.err")

        # 4. Cleanup execution artifacts (script and logs), keep user files
        try:
            await container.exec(
                cmd=["rm", filename, f"{filename}.out", f"{filename}.err"],
                workdir=settings.SANDBOX_WORK_DIR,
                user="sandbox"
            )
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox artifacts: {e}")
        
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code
        }

    async def upload_file(self, conversation_id: str, filename: str, data: bytes):
        """Upload a file to the sandbox working directory"""
        container_id = await self.get_or_create_session(conversation_id)
        container = await self.docker.containers.get(container_id)
        
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            info.mtime = 0 
            tar.addfile(info, io.BytesIO(data))
        tar_stream.seek(0)
        
        await container.put_archive(path=settings.SANDBOX_WORK_DIR, data=tar_stream)

    async def list_files(self, conversation_id: str) -> list[str]:
        """List files in the working directory"""
        container_id = await self.get_or_create_session(conversation_id)
        container = await self.docker.containers.get(container_id)
        
        # simple ls with Tty=True to avoid raw stream headers and ensure clean text
        exec_instance = await container.exec(
            cmd=["ls", "-1", settings.SANDBOX_WORK_DIR],
            user="sandbox",
            tty=True
        )
        
        output = b""
        try:
             async with exec_instance.start(detach=False) as stream:
                if hasattr(stream, 'read_out'):
                    msg = await stream.read_out()
                    if msg is not None:
                        if hasattr(msg, 'data'):
                            output = msg.data
                        else:
                            output = msg
                elif hasattr(stream, 'read'):
                    output = await stream.read()
                elif hasattr(stream, '__aiter__'):
                     async for chunk in stream: 
                         if isinstance(chunk, bytes):
                             output += chunk
                         else:
                             output += chunk.data
        except Exception as e:
            logger.warning(f"Error listing files: {e}")
            pass
            
        # Parse output (files separated by newline)
        if isinstance(output, bytes):
            # Remove potential control characters if TTY adds them
            decoded = output.decode('utf-8', errors='ignore')
            logger.debug(f"DEBUG: ls output (raw): {output!r}")
            logger.debug(f"DEBUG: ls output (decoded): {decoded!r}")
            files = decoded.splitlines()
        else:
            files = str(output).splitlines()
            
        return [f.strip() for f in files if f.strip()]

    async def read_file_bytes(self, conversation_id: str, filename: str) -> Optional[bytes]:
        """Read binary file content from container"""
        container_id = await self.get_or_create_session(conversation_id)
        container = await self.docker.containers.get(container_id)
        
        try:
            tar_obj = await container.get_archive(f"{settings.SANDBOX_WORK_DIR}/{filename}")
            
            content = io.BytesIO()
            if isinstance(tar_obj, bytes):
                content.write(tar_obj)
            elif hasattr(tar_obj, '__aiter__'):
                async for chunk in tar_obj:
                    content.write(chunk)
            else:
                 # Fallback for other types
                 try:
                     import tarfile
                     if hasattr(tar_obj, 'extractfile'):
                         for member in tar_obj:
                             if member.isfile():
                                 f = tar_obj.extractfile(member)
                                 if f: return f.read()
                 except: pass

                 try:
                     for chunk in tar_obj: content.write(chunk)
                 except: pass

            content.seek(0)
            
            with tarfile.open(fileobj=content, mode='r') as tar:
                member = tar.next()
                if member:
                    f = tar.extractfile(member)
                    if f:
                        return f.read()
        except Exception as e:
            logger.warning(f"Failed to read binary file {filename}: {e}")
        return None

    async def _read_file(self, container, filename: str) -> str:
        """Read text file from container"""
        try:
            tar_obj = await container.get_archive(f"{settings.SANDBOX_WORK_DIR}/{filename}")
            
            content = io.BytesIO()
            
            # Handle different return types from aiodocker versions
            if isinstance(tar_obj, bytes):
                content.write(tar_obj)
            elif hasattr(tar_obj, '__aiter__'):
                async for chunk in tar_obj:
                    content.write(chunk)
            elif hasattr(tar_obj, 'read') or hasattr(tar_obj, 'extractfile'): # Sync stream or TarFile?
                # If it's a TarFile object, we can't write it to BytesIO directly as bytes
                import tarfile
                if hasattr(tar_obj, 'extractfile'):
                    # It behaves like a TarFile object
                    try:
                        # Iterate to find the first member (file)
                        for member in tar_obj:
                            if member.isfile():
                                f = tar_obj.extractfile(member)
                                if f: return f.read().decode('utf-8', errors='replace')
                        return ""
                    except Exception as e:
                        logger.warning(f"Error extracting from TarFile object: {e}")
                        return ""
                else:
                    # Sync read
                    content.write(tar_obj.read())
            else:
                 # Attempt to iterate synchronously
                 try:
                     for chunk in tar_obj:
                         content.write(chunk)
                 except:
                     logger.error(f"Unknown type returned from get_archive: {type(tar_obj)}")
                     return ""

            content.seek(0)
            
            try:
                with tarfile.open(fileobj=content, mode='r') as tar:
                    member = tar.next()
                    if member:
                        f = tar.extractfile(member)
                        if f:
                            return f.read().decode('utf-8', errors='replace')
            except tarfile.ReadError:
                 return ""
            return ""
        except Exception as e:
            logger.warning(f"Failed to read file {filename}: {e} (Type: {type(tar_obj) if 'tar_obj' in locals() else 'unknown'})")
            return ""

# Global Singleton
_sandbox_service_instance: Optional[SandboxService] = None

def get_sandbox_service() -> SandboxService:
    global _sandbox_service_instance
    if _sandbox_service_instance is None:
        _sandbox_service_instance = SandboxService()
    return _sandbox_service_instance

async def close_sandbox_service():
    global _sandbox_service_instance
    if _sandbox_service_instance:
        await _sandbox_service_instance.close()
        _sandbox_service_instance = None

