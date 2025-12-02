import uuid
import secrets
import string
import logging
from typing import Optional, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users import exceptions
from fastapi import HTTPException

from src.config import settings
from src.users.models import User
from src.services.mail import sender, MessageSchema, MessageType
from src.utils.language import detect_language
from .dependencies import get_user_db
from .oauth_models import OAuthProvider
from .django_password import verify_django_password, is_django_password, is_unusable_password

if TYPE_CHECKING:
    from .api.v1.schemas import UserCreate

logger = logging.getLogger(__name__)

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY
    
    # Email sending rate limit (seconds)
    EMAIL_RATE_LIMIT_SECONDS = 60
    
    async def create(
        self,
        user_create: "UserCreate",
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> User:
        """
        Override create to handle user creation
        """
        # 1. Validate password
        await self.validate_password(user_create.password, user_create)

        # 2. Check existing user
        if user_create.email:
            existing_user = await self.user_db.get_by_email(user_create.email)
            if existing_user is not None:
                raise exceptions.UserAlreadyExists()

        # 3. Prepare user dict
        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        
        # 4. Handle password
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        
        # 5. Create user
        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user

    def _check_email_rate_limit(
        self, 
        last_sent_at: Optional[datetime], 
        email_type: str
    ) -> None:
        """
        Check email sending rate limit
        
        Args:
            last_sent_at: Last sent time
            email_type: Email type (for logging)
            
        Raises:
            HTTPException: If within rate limit time
        """
        if last_sent_at is None:
            return
            
        now = datetime.now(timezone.utc)
        time_since_last_sent = now - last_sent_at
        
        if time_since_last_sent < timedelta(seconds=self.EMAIL_RATE_LIMIT_SECONDS):
            remaining_seconds = self.EMAIL_RATE_LIMIT_SECONDS - int(time_since_last_sent.total_seconds())
            logger.warning(
                f"Rate limit hit for {email_type} email. "
                f"Last sent: {last_sent_at}, remaining: {remaining_seconds} seconds"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {remaining_seconds} seconds before requesting another {email_type} email."
            )
    
    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        # Check rate limit
        self._check_email_rate_limit(
            user.last_verification_email_sent_at,
            "verification"
        )
        
        # Check if user has valid email
        if not user.email:
            logger.warning(f"Attempted to send verification email to user {user.id} but user has no email address")
            return
        
        # Detect user language preference
        user_lang = detect_language(user.language, request)
        
        verify_link = f"{str(settings.FRONTEND_URL).rstrip('/')}/verify-email?token={token}"
        context = {
            "request": request,
            "user": user,
            "verify_link": verify_link,
        }
        
        # Select email template based on language
        template_name = f"emails/verify_email.{user_lang}.html"
        
        message = MessageSchema(
            subtype=MessageType.html,
            recipients=[user.email],
            subject="Email Verification Request" if user_lang == 'en' else "Email Verification Request",
            template_body=context
        )
        await sender.send_message(message, template_name=template_name)
        
        # Update sent time
        await self.user_db.update(user, {"last_verification_email_sent_at": datetime.now(timezone.utc)})

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        # Check rate limit
        self._check_email_rate_limit(
            user.last_password_reset_email_sent_at,
            "password reset"
        )
        
        # Check if user has valid email
        if not user.email:
            logger.warning(f"Attempted to send password reset email to user {user.id} but user has no email address")
            return
        
        # Detect user language preference
        user_lang = detect_language(user.language, request)
            
        reset_password_link = f"{str(settings.FRONTEND_URL).rstrip('/')}/reset-password?token={token}"
        context = {
            "request": request,
            "user": user,
            "reset_password_link": reset_password_link,
        }
        
        # Select email template based on language
        template_name = f"emails/reset_password.{user_lang}.html"
        
        message = MessageSchema(
            subtype=MessageType.html,
            recipients=[user.email],
            subject="Password Reset Request" if user_lang == 'en' else "Password Reset Request",
            template_body=context
        )
        await sender.send_message(message, template_name=template_name)
        
        # Update sent time
        await self.user_db.update(user, {"last_password_reset_email_sent_at": datetime.now(timezone.utc)})

    async def oauth_login_or_create(
        self, 
        provider: OAuthProvider,
        provider_user_info: Dict[str, Any],
        oauth_token: Dict[str, Any]
    ) -> tuple[User, bool]:
        """
        OAuth Login or Create User
        
        Returns:
            tuple[User, bool]: (User object, Is new OAuth link)
        """
        try:
            # Import inside function to avoid circular import
            from .oauth_service import OAuthService
            
            provider_user_id = str(provider_user_info.get('id'))
            email = provider_user_info.get('email')
            username = provider_user_info.get('login') or provider_user_info.get('username') or provider_user_info.get('name')
            
            logger.info(f"OAuth login/create process started - provider: {provider.name}, user_id: {provider_user_id}, email: {email}, username: {username}")
            
            # Create OAuth service instance
            oauth_service = OAuthService(self.user_db.session)
            
            # 1. Check if already linked (Highest priority)
            logger.debug(f"Checking existing OAuth link for provider {provider.id} and user {provider_user_id}")
            oauth_link = await oauth_service.get_oauth_link(provider.id, provider_user_id)
            if oauth_link:
                logger.info(f"Found existing OAuth link - user_id: {oauth_link.user_id}")
                # Update token info
                await oauth_service.update_oauth_link_token(oauth_link, oauth_token)
                user = await self.get(oauth_link.user_id)
                logger.info(f"OAuth login successful for existing link - user: {user.id}")
                return user, False  # Not a new OAuth link
            
            # 2. Try multi-strategy matching to find existing user
            existing_user = await self._find_existing_user_for_oauth(email, username, provider_user_info)
            
            if existing_user:
                # Link to existing user
                user = existing_user
                logger.info(f"Linking OAuth account to existing user: {user.id}")
                is_new_oauth_link = True  # New OAuth link to existing user
            else:
                # Create new user
                user = await self._create_oauth_user(provider, provider_user_id, email, username, provider_user_info)
                is_new_oauth_link = True  # New user, new OAuth link
            
            # 3. Create OAuth link
            logger.debug(f"Creating OAuth link for user {user.id} and provider {provider.id}")
            await oauth_service.create_oauth_link(
                user_id=user.id,
                provider=provider,
                provider_user_info=provider_user_info,
                token_data=oauth_token
            )
            logger.info(f"OAuth link created successfully for user {user.id} and provider {provider.name}")
            
            return user, is_new_oauth_link
        except Exception as e:
            logger.error(
                f"OAuth login/create failed - provider: {provider.name}, "
                f"user_id: {provider_user_info.get('id')}, "
                f"email: {provider_user_info.get('email')}, "
                f"error: {str(e)}", 
                exc_info=True
            )
            raise

    async def _find_existing_user_for_oauth(
        self, 
        email: Optional[str], 
        username: Optional[str], 
        provider_user_info: Dict[str, Any]
    ) -> Optional[User]:
        """
        Find existing user using multi-strategy
        
        Args:
            email: Email returned by OAuth provider
            username: Username returned by OAuth provider
            provider_user_info: Complete OAuth user info
            
        Returns:
            Found user object or None
        """
        
        # Strategy 1: Match by email (Most reliable)
        if email:
            try:
                logger.debug(f"Checking if user exists with email: {email}")
                existing_user = await self.get_by_email(email)
                logger.info(f"Found existing user with email {email} - user_id: {existing_user.id}")
                return existing_user
            except exceptions.UserNotExists:
                logger.debug(f"No existing user found with email: {email}")
        else:
            logger.debug("No email provided by OAuth provider")
        
        # Strategy 2: Match by username (Current User model does not support username field)
        # Note: Use with caution as usernames may not be unique or prone to conflicts
        # if username and hasattr(User, 'username'):
        #     # If User model has username field and supports query
        #     # Add username matching logic here
        #     pass
        
        # Strategy 3: Match by other unique identifiers (if OAuth provider provides phone etc.)
        # phone = provider_user_info.get('phone')
        # if phone and hasattr(User, 'phone'):
        #     # If User model has phone field and supports query
        #     # Add phone matching logic here
        #     pass
        
        # TODO: Add more matching strategies in the future
        # - Match by real-name verification info
        # - Match by device fingerprint
        # - Match by user active linking
        
        logger.debug("No existing user found through any matching strategy")
        return None
    
    async def _create_oauth_user(
        self,
        provider: OAuthProvider, 
        provider_user_id: str,
        email: Optional[str], 
        username: Optional[str],
        provider_user_info: Dict[str, Any]
    ) -> User:
        """
        Create new user for OAuth
        
        Args:
            provider: OAuth provider
            provider_user_id: Provider user ID
            email: Email
            username: Username
            provider_user_info: Complete OAuth user info
            
        Returns:
            Created user object
        """
        
        # Handle email address - Best practice: Use real email or None
        if email:
            user_email = email
            logger.info(f"Creating OAuth user with email: {email}")
        else:
            # Check if creating user without email is allowed
            if not settings.OAUTH_CREATE_USER_WITHOUT_EMAIL:
                logger.error(f"OAuth provider {provider.name} did not provide email and OAUTH_CREATE_USER_WITHOUT_EMAIL is disabled")
                raise ValueError("Email is required for user creation but not provided by OAuth provider")
            
            # Best practice: Do not generate fake email, set to None directly
            # Pros:
            # 1. Data integrity - No fake info stored
            # 2. Clear user status - System knows user has no email
            # 3. Compliance - No fake personal info stored
            # 4. Better UX - User can add real email later
            user_email = None
            logger.info(f"Creating OAuth user without email - provider: {provider.name}, user_id: {provider_user_id}")
        
        # Get name and avatar from mapped OAuth user info
        # Note: These fields should be mapped via provider.user_mapping configuration
        name = provider_user_info.get('name') or username
        avatar_url = provider_user_info.get('avatar')
        
        logger.info(f"Creating OAuth user with name: '{name}', avatar_url: '{avatar_url}'")
        
        # Create user data object
        from .api.v1.schemas import UserCreate
        
        user_create_data = UserCreate(
            email=user_email,
            password=self._generate_random_password(),
            name=name,
            avatar_url=avatar_url,
            is_verified=not settings.OAUTH_REQUIRE_EMAIL_VERIFICATION,  # Determined by config and whether real email exists
            is_active=True
        )
        
        # Current User model does not support username field, uncomment if needed in future
        # if username and hasattr(User, 'username'):
        #     # Ensure username uniqueness
        #     unique_username = await self._generate_unique_username(username, provider.name)
        #     # Note: If username is enabled, need to add username field to UserCreate model
        #     # user_create_data.username = unique_username
        
        logger.info(f"Creating new user for OAuth - email: {user_email}")
        
        # Create user
        user = await self.create(user_create_data)
        logger.info(f"New user created successfully - user_id: {user.id}")
        
        return user
    
    async def _generate_unique_username(self, base_username: str, provider_name: str) -> str:
        """
        Generate unique username (Current User model does not support username field, this method is reserved)
        
        Args:
            base_username: Base username
            provider_name: Provider name
            
        Returns:
            Unique username
        """
        # Clean username, remove special characters
        import re
        clean_username = re.sub(r'[^\w\-_.]', '', base_username.lower())
        
        # If empty after cleaning, use provider name
        if not clean_username:
            clean_username = provider_name.lower()
        
        # If User model supports username field in future, implement this logic
        # Currently return cleaned username directly
        return clean_username or f"{provider_name}_user"
    
    def _generate_random_password(self) -> str:
        """Generate random password"""
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(32))
    
    async def authenticate(self, credentials) -> Optional[User]:
        """
        Override authenticate method to support Django password format
        
        Need to check password format before password_helper.verify_and_update,
        because Django format will cause UnknownHashError
        """
        try:
            user = await self.get_by_email(credentials.username)
        except exceptions.UserNotExists:
            # Run password hash to prevent timing attacks
            self.password_helper.hash(credentials.password)
            return None

        # Call validate_password first to handle different formats
        try:
            await self.validate_password(credentials.password, user)
        except exceptions.InvalidPasswordException:
            return None
        
        return user if user.is_active else None

    async def validate_password(self, password: str, user: Union["UserCreate", User]) -> None:
        """
        Validate password
        
        Supports three password formats:
        1. Django pbkdf2_sha256 format (users migrated from old system)
        2. Django unusable password (OAuth users, cannot login with password)
        3. Bcrypt format (new users or upgraded users)
        
        If user logs in successfully with Django format password, it will be automatically upgraded to bcrypt
        
        Args:
            password: Password to validate
            user: User object (login) or UserCreate object (create user)
        """
        # If it is UserCreate object (create user), only need to call parent class password validation
        # No need to check hashed_password, because it does not exist yet
        if not isinstance(user, User):
            # This is create user scenario, call parent class password strength validation
            await super().validate_password(password, user)
            return
        
        # The following is User object validation logic (login scenario)
        # Check if it is Django unusable password (OAuth user)
        if is_unusable_password(user.hashed_password):
            logger.warning(
                f"Login attempt with password for OAuth-only user {user.id}. "
                "This account was created via OAuth and has no password set."
            )
            raise exceptions.InvalidPasswordException(
                reason="This account uses OAuth login. Please use 'Continue with GitHub/Google' or reset your password."
            )
        
        # Check if it is Django format password
        if is_django_password(user.hashed_password):
            # Use Django password validation
            is_valid = verify_django_password(password, user.hashed_password)
            
            if is_valid:
                # Validation successful, automatically upgrade to bcrypt format
                logger.info(f"Upgrading Django password to bcrypt for user {user.id}")
                new_hash = self.password_helper.hash(password)
                await self.user_db.update(user, {"hashed_password": new_hash})
                return
            else:
                # Password incorrect
                raise exceptions.InvalidPasswordException()
        else:
            # Use standard bcrypt validation
            verified, updated_password_hash = self.password_helper.verify_and_update(
                password, user.hashed_password
            )
            if not verified:
                raise exceptions.InvalidPasswordException(
                    reason="Password validation failed"
                )
            
            # If password hash needs update (e.g. parameters changed)
            if updated_password_hash is not None:
                await self.user_db.update(user, {"hashed_password": updated_password_hash})

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)