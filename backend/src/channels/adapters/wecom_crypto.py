import base64
import struct
import socket
import hashlib
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

class WeComCrypto:
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.token = token
        self.encoding_aes_key = encoding_aes_key
        self.corp_id = corp_id
        
        # Key derivation
        try:
            self.key = base64.b64decode(encoding_aes_key + "=")
            assert len(self.key) == 32
        except Exception:
            raise ValueError("Invalid EncodingAESKey")
    
    def get_signature(self, timestamp: str, nonce: str, encrypt_msg: str) -> str:
        """Generate signature"""
        sort_list = [self.token, timestamp, nonce, encrypt_msg]
        sort_list.sort()
        sha = hashlib.sha1()
        sha.update("".join(sort_list).encode("utf-8"))
        return sha.hexdigest()

    def decrypt(self, text: str, receive_id: Optional[str] = None) -> bytes:
        """Decrypt content"""
        # Base64 decode
        try:
            crypt_data = base64.b64decode(text)
        except Exception:
            raise ValueError("Base64 decode error")

        # AES Decrypt
        iv = self.key[:16]
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        try:
            original = decryptor.update(crypt_data) + decryptor.finalize()
        except Exception:
             raise ValueError("AES decrypt error")

        # Unpad (TKIP/PKCS#7)
        pad = original[-1]
        if pad < 1 or pad > 32:
            pad = 0
        decrypted = original[:-pad]

        # Splitting payload
        # 16 bytes random | 4 bytes length | content | receive_id
        try:
            content_len = socket.ntohl(struct.unpack("I", decrypted[16:20])[0])
            content = decrypted[20 : 20 + content_len]
            from_receive_id = decrypted[20 + content_len:].decode("utf-8")
        except Exception:
            raise ValueError("Invalid buffer")
            
        # Verify corp_id
        if receive_id and from_receive_id and from_receive_id != receive_id:
            logger.warning(f"CorpID validation failed. Configured: '{receive_id}', Received: '{from_receive_id}'")
            raise ValueError("CorpID validation failed")
            
        return content

    def encrypt(self, text: str, receive_id: Optional[str] = None) -> str:
        """Encrypt content"""
        # 1. Random 16 bytes (Use ASCII characters to match official SDK)
        import random
        import string
        letters = string.ascii_letters + string.digits
        random_header = "".join(random.choice(letters) for _ in range(16)).encode("utf-8")
        
        # 2. Content length 4 bytes (network order)
        text_bytes = text.encode("utf-8")
        msg_len = struct.pack("I", socket.htonl(len(text_bytes)))
        
        # 3. CorpID
        # Use provided receive_id if available, otherwise use self.corp_id
        current_id = receive_id if receive_id is not None else self.corp_id
        corp_id_bytes = current_id.encode("utf-8")
        
        # Join
        to_encrypt = random_header + msg_len + text_bytes + corp_id_bytes
        
        # Pad (PKCS#7)
        block_size = 32
        amount_to_pad = block_size - (len(to_encrypt) % block_size)
        if amount_to_pad == 0:
            amount_to_pad = block_size
        pad = chr(amount_to_pad).encode("utf-8")
        to_encrypt = to_encrypt + pad * amount_to_pad

        # Encrypt
        iv = self.key[:16]
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(to_encrypt) + encryptor.finalize()
        
        # Base64
        return base64.b64encode(encrypted).decode("utf-8")
