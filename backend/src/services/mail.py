from jinja2 import Environment, FileSystemLoader
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from starlette_babel.contrib.jinja import configure_jinja_env

from src.config import settings, TEMPLATE_DIR

class BabelConnectionConfig(ConnectionConfig):
    def template_engine(self) -> Environment:
        """
        Return template environment
        """
        folder = self.TEMPLATE_FOLDER
        if not folder:
            raise ValueError(
                "Class initialization did not include a ``TEMPLATE_FOLDER`` ``PathLike`` object."
            )
        template_env = Environment(loader=FileSystemLoader(folder))
        configure_jinja_env(template_env)
        return template_env
    
conf = BabelConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    MAIL_FROM=settings.MAIL_FROM,
    TEMPLATE_FOLDER=TEMPLATE_DIR,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

sender = FastMail(conf)