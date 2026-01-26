import json
import uuid
import time
import logging
from typing import Optional, Dict, Any
from fastapi import Request, Response

from src.channels.adapters.base import BaseChannelAdapter, IncomingMessage
from src.channels.models import ChannelConfig
from src.channels.adapters.wecom_crypto import WeComCrypto
from src.channels.services.wecom_smart_bot import get_stream_state, create_stream_state

logger = logging.getLogger(__name__)

class WecomSmartBotChannelAdapter(BaseChannelAdapter):
    def __init__(self, channel: ChannelConfig):
        super().__init__(channel)
        # WeCom Smart Bot uses Token and EncodingAESKey. 
        # CorpID is tricky, sometimes it is used, sometimes not (receiveid='')
        # We assume credentials have them.
        self.token = self.credentials.get("token")
        self.encoding_aes_key = self.credentials.get("encoding_aes_key")
        self.corp_id = self.credentials.get("corp_id", "") # Might be empty for Smart Bot
        
        if not self.token or not self.encoding_aes_key:
            logger.error("WeCom Bot missing token or encoding_aes_key")
            raise ValueError("WeCom Bot configuration error")
            
        self.crypto = WeComCrypto(self.token, self.encoding_aes_key, self.corp_id)

    async def verify_request(self, request: Request) -> bool:
        # Signature verification is done during decryption usually or explicit check
        # We can implement basic check here
        msg_signature = request.query_params.get("msg_signature")
        timestamp = request.query_params.get("timestamp")
        nonce = request.query_params.get("nonce")
        
        if not all([msg_signature, timestamp, nonce]):
            return False
            
        # WeComCrypto.get_signature can be used, but we need the 'admin' echo str or body?
        # For POST, we verify body signature. 
        # But here we just return True and let parse_webhook_body fail if decryption fails.
        return True

    async def handle_handshake(self, request: Request) -> Optional[Response]:
        # EchoStr challenge
        msg_signature = request.query_params.get("msg_signature")
        timestamp = request.query_params.get("timestamp")
        nonce = request.query_params.get("nonce")
        echostr = request.query_params.get("echostr")
        
        if echostr:
            try:
                # Decrypt EchoStr
                # Note: WeComCrypto.decrypt usually expects the full XML/JSON payload structure?
                # No, decrypt takes "text".
                # For VerifyURL, 'echostr' IS the text to decrypt.
                signature = self.crypto.get_signature(timestamp, nonce, echostr)
                if signature != msg_signature:
                    logger.warning("Handshake signature mismatch")
                    return None
                    
                decrypted_echo = self.crypto.decrypt(echostr, receive_id=None).decode('utf-8')
                return Response(content=decrypted_echo, media_type="text/plain")
            except Exception as e:
                logger.error(f"Handshake failed: {e}")
                return None
        return None

    def _encrypt_pack(self, plain_text: str) -> Dict[str, str]:
        """Encrypt content and pack into WeCom JSON format"""
        encrypted = self.crypto.encrypt(plain_text, receive_id=self.corp_id or None) # Base64
        # WeComCrypto.encrypt returns base64 str.
        
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex[:10]
        
        signature = self.crypto.get_signature(timestamp, nonce, encrypted)
        
        return {
            "encrypt": encrypted,
            "msgsignature": signature,
            "timestamp": timestamp,
            "nonce": nonce
        }

    async def parse_webhook_body(self, request: Request) -> Optional[IncomingMessage]:
        try:
            body = await request.body()
            data = json.loads(body)
            
            # 1. Validation
            msg_signature = request.query_params.get("msg_signature")
            timestamp = request.query_params.get("timestamp")
            nonce = request.query_params.get("nonce")
            encrypt = data.get("encrypt")
            
            if not encrypt:
                logger.error("No encrypt field in WeCom Bot body")
                return None
                
            sig = self.crypto.get_signature(timestamp, nonce, encrypt)
            if sig != msg_signature:
                 logger.error("Signature mismatch in verification")
                 return None
                 
            # 2. Decrypt
            decrypted_bytes = self.crypto.decrypt(encrypt, receive_id=None)
            msg_data = json.loads(decrypted_bytes.decode('utf-8'))
            logger.debug(f"WeCom Bot decrypted: {msg_data}")
            
            msg_type = msg_data.get("msgtype")
            
            if msg_type == "text":
                return self._handle_text_message(msg_data)
            elif msg_type == "stream":
                return self._handle_stream_poll(msg_data)
            else:
                logger.warning(f"Unsupported message type {msg_type}")
                return None
                
        except Exception as e:
            logger.error(f"WeCom Bot Parse Error: {e}", exc_info=True)
            return None

    def _handle_text_message(self, msg_data: Dict[str, Any]) -> IncomingMessage:
        """Process incoming user text message and prepare for stream response"""
        content = msg_data.get("text", {}).get("content", "")
        
        # Handle Quote (Reply context)
        quote_info = msg_data.get("quote", {})
        if quote_info and quote_info.get("msgtype") == "text":
             quote_text = quote_info.get("text", {}).get("content", "")
             if quote_text:
                 content = f"{content}\n\n[引用内容:\n{quote_text}]"
        
        # Extract User Identity
        real_user_id = msg_data.get("from", {}).get("userid")
        if not real_user_id:
             logger.warning("No userid in from field, using random ID")
             real_user_id = uuid.uuid4().hex
        
        # Initialize Stream Session
        stream_id = uuid.uuid4().hex
        create_stream_state(stream_id)
        logger.info(f"Created stream session {stream_id} for user {real_user_id}")
        
        # Prepare Direct Response (Handshake packet for client to start polling)
        resp_payload = {
            "msgtype": "stream",
            "stream": {
                "id": stream_id,
                "finish": False,
                "content": "" 
            }
        }
        self._set_direct_response(resp_payload)
        
        # Return Task for Executor
        return IncomingMessage(
            user_id=real_user_id,
            content=content,
            message_id=msg_data.get("msgid", stream_id),
            channel_id=str(self.channel.id),
            stream_id=stream_id,
            is_stream_poll=False
        )

    def _handle_stream_poll(self, msg_data: Dict[str, Any]) -> IncomingMessage:
        """Process polling request for an existing stream"""
        stream_id = msg_data.get("stream", {}).get("id")
        state = get_stream_state(stream_id)
        
        if not state:
            logger.warning(f"Stream {stream_id} not found or expired")
            resp_payload = {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                     "finish": True,
                     "content": "Session Expired."
                }
            }
        else:
            # Return current accumulated content
            resp_payload = {
                 "msgtype": "stream",
                 "stream": {
                     "id": stream_id,
                     "finish": state["finish"],
                     "content": state["content"]
                 }
            }
        
        self._set_direct_response(resp_payload)
        
        # Return poll signal (no background task needed)
        return IncomingMessage(
            user_id=stream_id or "poll",
            content="",
            message_id=str(uuid.uuid4()),
            channel_id=str(self.channel.id),
            stream_id=stream_id,
            is_stream_poll=True
        )

    def _set_direct_response(self, payload: Dict[str, Any]):
        """Helper to encrypt and set the direct response"""
        encrypted_resp = self._encrypt_pack(json.dumps(payload, ensure_ascii=False))
        self.direct_response = Response(content=json.dumps(encrypted_resp), media_type="application/json")

    async def send_text(self, user_id: str, text: str):
        # Outbound disabled: WeCom Smart Bot uses polling (Passive Response)
        pass

