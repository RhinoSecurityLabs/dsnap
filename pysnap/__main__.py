from botocore.exceptions import NoCredentialsError, NoRegionError

from .main import app
import logging

logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.WARNING)

try:
    app()
except (NoCredentialsError, NoRegionError) as e:
    logging.error(e.args[0])