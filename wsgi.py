import logging
from logging import FileHandler as Handler   # logging.handlers in Python 2.7

log_handler = Handler('wsgi.log')
log_handler.setLevel(logging.INFO)

import webapp
application = webapp.create_app()
application.logger.addHandler(log_handler)
