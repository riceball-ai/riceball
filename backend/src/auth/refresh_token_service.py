"""
Refresh Token Service
"""
import secrets
import hashlib
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.auth.refresh_token_models import RefreshToken

logger = logging.getLogger(__name__)


class RefreshTokenService:
    """Refresh Token Business Logic"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash the token"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def _generate_token() -> str:
        """Generate random token"""
        return secrets.token_urlsafe(64)
    
    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        device_info: Optional[str] = None
    ) -> tuple[str, RefreshToken]:
        """
        Create Refresh Token
        
        Args:
            user_id: User ID
            device_info: Device info (User-Agent)
        
        Returns:
            tuple[str, RefreshToken]: (raw token, RefreshToken object)
        """
        # Generate random token
        raw_token = self._generate_token()
        hashed_token = self._hash_token(raw_token)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(
            seconds=settings.REFRESH_TOKEN_LIFETIME_SECONDS
        )
        
        # Create database record
        refresh_token = RefreshToken(
            token=hashed_token,
            user_id=user_id,
            expires_at=expires_at,
            device_info=device_info,
            revoked=False
        )
        
        self.session.add(refresh_token)
        
        # Limit max tokens per user
        await self._cleanup_old_tokens(user_id)
        
        await self.session.commit()
        await self.session.refresh(refresh_token)
        
        logger.info(f"Created refresh token for user {user_id}, expires at {expires_at}")
        
        return raw_token, refresh_token
    
    async def verify_refresh_token(
        self,
        raw_token: str
    ) -> Optional[RefreshToken]:
        """
        Verify Refresh Token
        
        Args:
            raw_token: Raw token
        
        Returns:
            RefreshToken object or None (if invalid)
        """
        hashed_token = self._hash_token(raw_token)
        
        # Query token
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.token == hashed_token,
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.expires_at > datetime.utcnow()
            )
        )
        
        result = await self.session.execute(stmt)
        refresh_token = result.scalar_one_or_none()
        
        if refresh_token:
            logger.debug(f"Refresh token verified for user {refresh_token.user_id}")
        else:
            logger.warning("Invalid or expired refresh token")
        
        return refresh_token
    
    async def revoke_token(self, token_id: uuid.UUID) -> bool:
        """
        Revoke specified Refresh Token
        
        Args:
            token_id: Token ID
        
        Returns:
            Whether revocation was successful
        """
        stmt = select(RefreshToken).where(RefreshToken.id == token_id)
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        
        if token:
            token.revoked = True
            await self.session.commit()
            logger.info(f"Revoked refresh token {token_id}")
            return True
        
        return False
    
    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """
        Revoke all Refresh Tokens for a user (for "Logout all devices")
        
        Args:
            user_id: User ID
        
        Returns:
            Number of revoked tokens
        """
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False  # noqa: E712
            )
        )
        
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()
        
        count = 0
        for token in tokens:
            token.revoked = True
            count += 1
        
        await self.session.commit()
        logger.info(f"Revoked {count} refresh tokens for user {user_id}")
        
        return count
    
    async def rotate_token(
        self,
        old_token: RefreshToken,
        device_info: Optional[str] = None
    ) -> tuple[str, RefreshToken]:
        """
        Rotate Refresh Token (revoke old, create new)
        
        Args:
            old_token: Old RefreshToken object
            device_info: Device info
        
        Returns:
            tuple[str, RefreshToken]: (new raw token, new RefreshToken object)
        """
        # Revoke old token
        old_token.revoked = True
        
        # Create new token
        raw_token, new_token = await self.create_refresh_token(
            user_id=old_token.user_id,
            device_info=device_info or old_token.device_info
        )
        
        logger.info(f"Rotated refresh token for user {old_token.user_id}")
        
        return raw_token, new_token
    
    async def _cleanup_old_tokens(self, user_id: uuid.UUID) -> None:
        """
        Cleanup excessive Refresh Tokens for user
        
        Keep the latest N valid tokens, delete the rest
        """
        # Get all unrevoked tokens for user, ordered by creation time descending
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False  # noqa: E712
            )
        ).order_by(RefreshToken.created_at.desc())
        
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()
        
        # If limit exceeded, revoke old tokens
        if len(tokens) >= settings.REFRESH_TOKEN_MAX_PER_USER:
            tokens_to_revoke = tokens[settings.REFRESH_TOKEN_MAX_PER_USER - 1:]
            for token in tokens_to_revoke:
                token.revoked = True
            
            logger.info(f"Cleaned up {len(tokens_to_revoke)} old refresh tokens for user {user_id}")
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Cleanup all expired Refresh Tokens (can be called by scheduled task)
        
        Returns:
            Number of deleted tokens
        """
        stmt = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.utcnow()
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} expired refresh tokens")
        
        return deleted_count
    
    async def get_user_active_tokens(self, user_id: uuid.UUID) -> list[RefreshToken]:
        """
        Get all active Refresh Tokens for user
        
        Args:
            user_id: User ID
        
        Returns:
            List of RefreshToken
        """
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.expires_at > datetime.utcnow()
            )
        ).order_by(RefreshToken.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


def get_refresh_token_service(session: AsyncSession) -> RefreshTokenService:
    """Dependency Injection: Get RefreshTokenService instance"""
    return RefreshTokenService(session)
