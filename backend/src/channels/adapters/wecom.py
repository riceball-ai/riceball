from typing import Optional, Dict, Any
from fastapi import Request, Response
import httpx
import logging
import time
import json
import xml.etree.ElementTree as ET

from src.channels.adapters.base import BaseChannelAdapter, IncomingMessage
from src.channels.models import ChannelConfig
from src.channels.adapters.wecom_crypto import WeComCrypto

logger = logging.getLogger(__name__)

class WecomChannelAdapter(BaseChannelAdapter):
    API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self, channel: ChannelConfig):
        super().__init__(channel)
        self.corp_id = self.credentials.get("corp_id")
        self.secret = self.credentials.get("secret")
        self.agent_id = self.credentials.get("agent_id")
        self.token = self.credentials.get("token")
        self.aes_key = self.credentials.get("aes_key")
        
        self.crypto = None
        if all([self.corp_id, self.token, self.aes_key]):
            try:
                self.crypto = WeComCrypto(self.token, self.aes_key, self.corp_id)
            except Exception as e:
                logger.error(f"Failed to init WeComCrypto for channel {channel.id}: {e}")
            except Exception as e:
                logger.error(f"Failed to init WeComCrypto for channel {channel.id}: {e}")

    async def verify_request(self, request: Request) -> bool:
        """
        Verify signature for both GET (verification) and POST (callback).
        """
        if not self.crypto:
            logger.warning("WeCom crypto not initialized, cannot verify request")
            return False

        params = request.query_params
        msg_signature = params.get("msg_signature")
        timestamp = params.get("timestamp")
        nonce = params.get("nonce")
        echostr = params.get("echostr") # Only in GET

        if not all([msg_signature, timestamp, nonce]):
            return False

        # If it's a GET request, we verify the echostr
        if request.method == "GET" and echostr:
            signature = self.crypto.get_signature(timestamp, nonce, echostr)
            if signature != msg_signature:
                return False
            # We don't verify further here, handle_webhook will assume verified if this passes
            # But handle_handshake calls this too.
            return True
        
        return True # For POST, we verify the body signature later during decryption

    async def handle_handshake(self, request: Request) -> Optional[Response]:
        """
        Handle the URL verification challenge from WeCom.
        """
        if request.method == "GET":
            if not self.crypto:
                return Response("WeCom configuration invalid", status_code=500)

            params = request.query_params
            msg_signature = params.get("msg_signature")
            timestamp = params.get("timestamp")
            nonce = params.get("nonce")
            echostr = params.get("echostr")
            
            if not all([msg_signature, timestamp, nonce, echostr]):
                return None

            signature = self.crypto.get_signature(timestamp, nonce, echostr)
            if signature != msg_signature:
                logger.warning("WeCom signature verification failed")
                return Response("Invalid signature", status_code=403)
                
            try:
                decrypted_echo = self.crypto.decrypt(echostr, self.corp_id)
                return Response(content=decrypted_echo)
            except Exception as e:
                logger.error(f"WeCom echo decryption failed: {e}")
                return Response("Decryption failed", status_code=403)
        return None

    async def parse_webhook_body(self, request: Request) -> Optional[IncomingMessage]:
        if not self.crypto:
            logger.error("WeCom crypto not initialized, cannot parse body")
            return None

        params = request.query_params
        msg_signature = params.get("msg_signature")
        timestamp = params.get("timestamp")
        nonce = params.get("nonce")
        
        if not all([msg_signature, timestamp, nonce]):
            logger.warning("Missing signature parameters in WeCom POST")
            return None

        body_bytes = await request.body()
        encrypt_text = None
        
        # Try JSON first (Smart Bot uses JSON)
        try:
            json_body = json.loads(body_bytes)
            encrypt_text = json_body.get("encrypt") or json_body.get("Encrypt")  # lowercase first
            if encrypt_text:
                logger.debug("Extracted encrypted content from JSON body")
        except json.JSONDecodeError:
            # Try XML (regular apps may use XML)
            try:
                root = ET.fromstring(body_bytes)
                encrypt_node = root.find("Encrypt")
                if encrypt_node is not None:
                    encrypt_text = encrypt_node.text
                    logger.debug("Extracted encrypted content from XML body")
            except ET.ParseError:
                pass
        
        if not encrypt_text:
            logger.error("Failed to extract encrypted content from body (neither XML nor JSON)")
            return None

        try:
            # Verify signature of the encrypted body
            signature = self.crypto.get_signature(timestamp, nonce, encrypt_text)
            if signature != msg_signature:
                logger.warning("WeCom body signature mismatch")
                return None
                
            # Decrypt
            content_bytes = self.crypto.decrypt(encrypt_text, self.corp_id)
            logger.debug(f"Decrypted WeCom content raw: {content_bytes.decode('utf-8', errors='replace')}")
            
            try:
                # Smart Bot uses JSON
                json_data = json.loads(content_bytes)
                msg_type = json_data.get("msgtype")
                
                if msg_type == "text":
                    # Smart Bot Text Request
                    self.is_smart_bot = True # Mark as smart bot to trigger streaming flow
                    content = json_data.get("text", {}).get("content", "")
                    
                    # Handle quoted message
                    quote = json_data.get("quote")
                    if quote and quote.get("msgtype") == "text":
                        quote_content = quote.get("text", {}).get("content", "")
                        if quote_content:
                            # Attach quote to content so AI has context
                            content += f"\n\n[引用消息]\n{quote_content}"

                    from_data = json_data.get("from", {})
                    user_id = from_data.get("userid") or from_data.get("user_id") or "unknown"
                    
                    logger.info(f"Received WeCom Smart Bot text message: user_id={user_id}, content_len={len(content)}")
                    logger.debug(f"Full text message data: {json_data}")
                    
                    return IncomingMessage(
                        user_id=user_id,
                        username=None,
                        content=content,
                        message_id=json_data.get("msgid", ""),
                        channel_id=str(self.channel.id)
                    )
                elif msg_type == "stream":
                    # Stream Poll Request
                    # Docs say 'from.userid' is available
                    stream_id = json_data.get("stream", {}).get("id")
                    user_id = json_data.get("from", {}).get("userid", "unknown")
                    logger.debug(f"Received WeCom stream poll request: stream_id={stream_id}, user_id={user_id}")
                    logger.debug(f"Full stream poll data: {json_data}")
                    
                    return IncomingMessage(
                        user_id=user_id,
                        content="", # No content in poll
                        message_id=json_data.get("msgid", "poll"),  # Use msgid from refresh packet
                        channel_id=str(self.channel.id),
                        is_stream_poll=True,
                        stream_id=stream_id
                    )
                
                logger.warning(f"WeCom unsupported JSON msgtype: {msg_type}")
                return None
            except json.JSONDecodeError:
                logger.error("Failed to parse WeCom body as JSON")
                return None
        except Exception as e:
            logger.error(f"Error parsing WeCom body: {e}")
            return None

    def should_stream_response(self, incoming: IncomingMessage) -> bool:
        """
        Check if we should stream the response.
        For WeCom Smart Bot (detected by JSON usage), we MUST stream to reply instantly.
        """
        return getattr(self, "is_smart_bot", False)

    def format_stream_response(self, stream_id: str, content: str, finished: bool, request_params: dict) -> Response:
        """
        Generate WeCom Smart Bot streaming response.
        
        Key findings:
        - WeCom Smart Bot uses JSON format for communication (NOT XML!)
        - Request: {"encrypt": "...", ...} (lowercase encrypt)
        - Response: {"encrypt": "...", "msg_signature": "...", "timestamp": "...", "nonce": "..."}
        - Content-Type: application/json
        """
        
        # 1. Build plain JSON message (decrypted content)
        plain = {
            "msgtype": "stream",
            "stream": {
                "id": stream_id,
                "finish": finished,
                "content": content
            }
        }
        
        plain_json = json.dumps(plain, ensure_ascii=False)
        logger.debug(f"Plain stream message: {plain_json}")
        
        # 2. Encrypt JSON string
        # Smart Bot uses empty string as receiveid
        encrypted_content = self.crypto.encrypt(plain_json, receive_id="")
        
        # 3. Generate signature
        request_params = request_params or {}
        timestamp = request_params.get("timestamp") or str(int(time.time()))
        nonce = request_params.get("nonce") or str(int(time.time()))
        
        signature = self.crypto.get_signature(timestamp, nonce, encrypted_content)
        
        # 4. Build JSON response (matching WeCom format)
        response_data = {
            "encrypt": encrypted_content,  # Note: lowercase encrypt
            "msg_signature": signature,     # lowercase with underscore
            "timestamp": timestamp,          # lowercase
            "nonce": nonce                   # lowercase
        }
        
        response_json = json.dumps(response_data, ensure_ascii=False)
        logger.info(f"Stream response: stream_id={stream_id}, finish={finished}, content_len={len(content)}")
        logger.debug(f"Encrypted JSON response: {response_json[:200]}...")
        
        # Return JSON format
        return Response(content=response_json, media_type="application/json")


    async def send_text(self, user_id: str, text: str):
        logger.info(f"Attempting to send text to user {user_id} via WeCom API. Length: {len(text)}")
        access_token = await self._get_access_token()
        if not access_token:
            logger.error("Failed to get WeCom access token during send_text")
            return

        url = f"{self.API_BASE}/message/send?access_token={access_token}"
        payload = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": text
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            logger.info(f"WeCom Send Response: {data}")
            if data.get("errcode") != 0:
                logger.error(f"Failed to send WeCom message: {data}")

    async def _get_access_token(self) -> Optional[str]:
        # Simple caching in memory
        # TODO: Move to Redis or DB for multi-instance support
        now = time.time()
        if hasattr(self, "_token_cache") and self._token_cache["expires_at"] > now:
            return self._token_cache["token"]
            
        url = f"{self.API_BASE}/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.secret}
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            if data.get("errcode") == 0:
                token = data["access_token"]
                expires_in = data["expires_in"]
                self._token_cache = {
                    "token": token,
                    "expires_at": now + expires_in - 200 # Buffer
                }
                return token
        return None

    def format_passive_text_response(self, user_id: str, content: str) -> Response:
        """
        Generate a passive XML text response (Encrypted)
        """
        now = str(int(time.time()))
        
        # 1. Construct Plain XML
        plain_xml = f"""<xml>
<ToUserName><![CDATA[{user_id}]]></ToUserName>
<FromUserName><![CDATA[{self.corp_id}]]></FromUserName>
<CreateTime>{now}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

        # 2. Encrypt It
        encrypted = self.crypto.encrypt(plain_xml)
        
        # 3. Generate Signature
        nonce = str(int(time.time()))
        signature = self.crypto.get_signature(now, nonce, encrypted)
        
        # 4. Wrap in Final XML
        final_xml = f"""<xml>
<Encrypt><![CDATA[{encrypted}]]></Encrypt>
<MsgSignature><![CDATA[{signature}]]></MsgSignature>
<TimeStamp>{now}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""

        return Response(content=final_xml, media_type="application/xml")
