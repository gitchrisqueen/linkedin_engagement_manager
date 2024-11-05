import logging
import sys
from logging.handlers import RotatingFileHandler
import datetime as DT

# Setup logger
logger = logging.getLogger('cqc_lem')
INFO_FORMAT = "%(message)s"
#DEBUG_FORMAT = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s]%(levelname)s: %(message)s"
#ERROR_FORMAT = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s]%(levelname)s: %(message)s"
logging.basicConfig(format=INFO_FORMAT, level=logging.INFO)
#logging.basicConfig(format=DEBUG_FORMAT, level=logging.DEBUG)
#logging.basicConfig(format=ERROR_FORMAT, level=logging.ERROR)

today = DT.date.today()
# Log to file
LOGGING_FILENAME = 'logs/cqc_lem_'+today.strftime("%Y_%m_%d")+'.log'


class MyFormatter(logging.Formatter):
    err_fmt = "ERROR: %(msg)s"
    dbg_fmt = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s]%(levelname)s: %(msg)s"
    info_fmt = "%(msg)s"

    def __init__(self):
        super().__init__(fmt="%(levelno)d: %(msg)s", datefmt=None, style='%')

    def format(self, record):

        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt

        # Replace the original format with one customized by logging level
        if record.levelno == logging.DEBUG:
            self._style._fmt = MyFormatter.dbg_fmt

        elif record.levelno == logging.INFO:
            self._style._fmt = MyFormatter.info_fmt

        elif record.levelno == logging.ERROR:
            self._style._fmt = MyFormatter.err_fmt

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._style._fmt = format_orig

        return result


fmt = MyFormatter()
#stream_handler = logging.StreamHandler(sys.stdout)
#stream_handler.setFormatter(fmt)
#logger.root.addHandler(stream_handler)
#logging.root.setLevel(logging.INFO)

file_handler = RotatingFileHandler(LOGGING_FILENAME, maxBytes=250000000, backupCount=10)  # 10 files of 250MB each
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)


def myprint(message, debug=False):
    if debug:
        logger.info(message)
    else:
        sys.stdout.flush()
        sys.stdout.write('\r' + message + '\n')
        sys.stdout.flush()
