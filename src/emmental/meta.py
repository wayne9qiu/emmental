import logging
import os
import tempfile
from builtins import object
from datetime import datetime

import yaml

from emmental.utils.utils import merge, set_random_seed

MAX_CONFIG_SEARCH_DEPTH = 25  # Max num of parent directories to look for config

logger = logging.getLogger(__name__)


def init(
    log_dir=tempfile.gettempdir(),
    log_name="emmental.log",
    format="[%(asctime)s][%(levelname)s] %(name)s:%(lineno)s - %(message)s",
    level=logging.INFO,
    config={},
    config_dir=None,
    config_name="emmental-config.yaml",
):
    """Initialize the logging and configuration.
    :param log_dir: The directory to store logs in.
    :type log_dir: str
    :param format: The logging format string to use.
    :type format: str
    :param level: The logging level to use, e.g., logging.INFO.
    :param config: The new configuration, defaults to {}
    :type config: dict, optional
    :param config_dir: the path to the config file, defaults to None
    :type config_dir: str, optional
    :param config_name: the config file name, defaults to "emmental-config.yaml"
    :type config_name: str, optional
    """

    init_logging(log_dir, log_name, format, level)
    init_config()
    if config_dir is not None:
        Meta.update_config(config, config_dir, config_name)

    set_random_seed(Meta.config["meta_config"]["seed"])


def init_config():
    """Load the default configuration."""

    # Load the default setting
    default_config_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "emmental-default-config.yaml"
    )
    with open(default_config_path, "r") as f:
        config = yaml.load(f)
    logger.info(f"Loading Emmental default config from {default_config_path}.")

    Meta.config = config


def init_logging(
    log_dir=tempfile.gettempdir(),
    log_name="emmental.log",
    format="[%(asctime)s][%(levelname)s] %(name)s:%(lineno)s - %(message)s",
    level=logging.INFO,
):
    """Configures logging to output to the provided log_dir.
    Will use a nested directory whose name is the current timestamp.
    :param log_dir: The directory to store logs in.
    :type log_dir: str
    :param format: The logging format string to use.
    :type format: str
    :param level: The logging level to use, e.g., logging.INFO.
    """

    if not Meta.log_path:
        # Generate a new directory using the log_dir, if it doesn't exist
        date = datetime.now().strftime("%Y_%m_%d")
        time = datetime.now().strftime("%H_%M_%S")
        log_path = os.path.join(log_dir, date, time)
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        # Configure the logger using the provided path
        logging.basicConfig(
            format=format,
            level=level,
            handlers=[
                logging.FileHandler(os.path.join(log_path, log_name)),
                logging.StreamHandler(),
            ],
        )

        # Notify user of log location
        logger.info(f"Setting logging directory to: {log_path}")
        Meta.log_path = log_path
    else:
        logger.info(
            f"Logging was already initialized to use {Meta.log_path}.  "
            "To configure logging manually, call emmental.init_logging before "
            "initialiting Meta."
        )


class Meta(object):
    """Singleton-like metadata class for all global variables.
    Adapted from the Unique Design Pattern:
    https://stackoverflow.com/questions/1318406/why-is-the-borg-pattern-better-than-the-singleton-pattern-in-python
    """

    log_path = None
    config = None

    @classmethod
    def init(cls):
        """Return the unique Meta class."""
        if not Meta.log_path:
            init_logging()

        if not Meta.config:
            init_config()

        return cls

    def update_config(config={}, path=None, filename="emmental-config.yaml"):
        """Update the configuration with the configs in root of project and
        its parents.

        Note: There are two ways to update the config:
            (1) uses a config dict to update to config
            (2) uses path and filename to load yaml file to update config

        :param config: The new configuration, defaults to {}
        :type config: dict, optional
        :param path: the path to the config file, defaults to os.getcwd()
        :param path: str, optional
        :param filename: the config file name, defaults to "emmental-config.yaml"
        :param filename: str, optional
        """

        if config != {}:
            Meta.config = merge(Meta.config, config)
            logger.info("Updating Emmental config from user provided config.")

        if path is not None:
            tries = 0
            current_dir = path
            while current_dir and tries < MAX_CONFIG_SEARCH_DEPTH:
                potential_path = os.path.join(current_dir, filename)
                if os.path.exists(potential_path):
                    with open(potential_path, "r") as f:
                        Meta.config = merge(Meta.config, yaml.safe_load(f))
                    logger.info(f"Updating Emmental config from {potential_path}.")
                    break

                new_dir = os.path.split(current_dir)[0]
                if current_dir == new_dir:
                    logger.info("Unable to find config file. Using defaults.")
                    break
                current_dir = new_dir
                tries += 1
