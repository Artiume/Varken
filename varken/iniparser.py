import configparser
import logging
from sys import exit
from os.path import join, exists

from varken.helpers import clean_sid_check
from varken.varkenlogger import BlacklistFilter
from varken.structures import SonarrServer, RadarrServer, OmbiServer, TautulliServer, InfluxServer, CiscoASAFirewall


class INIParser(object):
    def __init__(self, data_folder):
        self.config = configparser.ConfigParser(interpolation=None)
        self.data_folder = data_folder

        self.logger = logging.getLogger()

        self.influx_server = InfluxServer()

        self.sonarr_enabled = False
        self.sonarr_servers = []

        self.radarr_enabled = False
        self.radarr_servers = []

        self.ombi_enabled = False
        self.ombi_servers = []

        self.tautulli_enabled = False
        self.tautulli_servers = []

        self.ciscoasa_enabled = False
        self.ciscoasa_firewalls = []

        self.parse_opts()

        self.filtered_strings = None

    def config_blacklist(self):
        filtered_strings = [section.get(k) for key, section in self.config.items()
                                 for k in section if k in BlacklistFilter.blacklisted_strings]
        self.filtered_strings = list(filter(None, filtered_strings))
        
        for handler in self.logger.handlers:
            handler.addFilter(BlacklistFilter(set(self.filtered_strings)))

    def enable_check(self, server_type=None):
        t = server_type
        try:
            global_server_ids = self.config.get('global', t)
            if global_server_ids.lower() in ['false', 'no', '0']:
                self.logger.info('%s disabled.', t.upper())
            else:
                sids = clean_sid_check(global_server_ids, t)
                return sids
        except configparser.NoOptionError as e:
            self.logger.error(e)

    def read_file(self):
        file_path = join(self.data_folder, 'varken.ini')
        if exists(file_path):
            with open(file_path) as config_ini:
                self.config.read_file(config_ini)
            self.config_blacklist()
        else:
            exit('Config file missing (varken.ini) in %s', self.data_folder)

    def parse_opts(self):
        self.read_file()
        # Parse InfluxDB options
        url = self.config.get('influxdb', 'url')
        port = self.config.getint('influxdb', 'port')
        username = self.config.get('influxdb', 'username')
        password = self.config.get('influxdb', 'password')

        self.influx_server = InfluxServer(url, port, username, password)

        # Parse Sonarr options
        self.sonarr_enabled = self.enable_check('sonarr_server_ids')

        if self.sonarr_enabled:
            for server_id in self.sonarr_enabled:
                sonarr_section = 'sonarr-' + str(server_id)
                try:
                    url = self.config.get(sonarr_section, 'url')
                    apikey = self.config.get(sonarr_section, 'apikey')
                    scheme = 'https://' if self.config.getboolean(
                        sonarr_section, 'ssl') else 'http://'
                    verify_ssl = self.config.getboolean(
                        sonarr_section, 'verify_ssl')
                    if scheme != 'https://':
                        verify_ssl = False
                    queue = self.config.getboolean(sonarr_section, 'queue')
                    missing_days = self.config.getint(
                        sonarr_section, 'missing_days')
                    future_days = self.config.getint(
                        sonarr_section, 'future_days')
                    missing_days_run_seconds = self.config.getint(
                        sonarr_section, 'missing_days_run_seconds')
                    future_days_run_seconds = self.config.getint(
                        sonarr_section, 'future_days_run_seconds')
                    queue_run_seconds = self.config.getint(
                        sonarr_section, 'queue_run_seconds')

                    server = SonarrServer(server_id, scheme + url, apikey, verify_ssl, missing_days,
                                          missing_days_run_seconds, future_days, future_days_run_seconds,
                                          queue, queue_run_seconds)
                    self.sonarr_servers.append(server)
                except configparser.NoOptionError as e:
                    self.radarr_enabled = False
                    self.logger.error(
                        '%s disabled. Error: %s', sonarr_section, e)

        # Parse Radarr options
        self.radarr_enabled = self.enable_check('radarr_server_ids')

        if self.radarr_enabled:
            for server_id in self.radarr_enabled:
                radarr_section = 'radarr-' + str(server_id)
                try:
                    url = self.config.get(radarr_section, 'url')
                    apikey = self.config.get(radarr_section, 'apikey')
                    scheme = 'https://' if self.config.getboolean(
                        radarr_section, 'ssl') else 'http://'
                    verify_ssl = self.config.getboolean(
                        radarr_section, 'verify_ssl')
                    if scheme != 'https://':
                        verify_ssl = False
                    queue = self.config.getboolean(radarr_section, 'queue')
                    queue_run_seconds = self.config.getint(
                        radarr_section, 'queue_run_seconds')
                    get_missing = self.config.getboolean(
                        radarr_section, 'get_missing')
                    get_missing_run_seconds = self.config.getint(
                        radarr_section, 'get_missing_run_seconds')

                    server = RadarrServer(server_id, scheme + url, apikey, verify_ssl, queue, queue_run_seconds,
                                          get_missing, get_missing_run_seconds)
                    self.radarr_servers.append(server)
                except configparser.NoOptionError as e:
                    self.radarr_enabled = False
                    self.logger.error(
                        '%s disabled. Error: %s', radarr_section, e)

        # Parse Tautulli options
        self.tautulli_enabled = self.enable_check('tautulli_server_ids')

        if self.tautulli_enabled:
            for server_id in self.tautulli_enabled:
                tautulli_section = 'tautulli-' + str(server_id)
                try:
                    url = self.config.get(tautulli_section, 'url')
                    fallback_ip = self.config.get(
                        tautulli_section, 'fallback_ip')
                    apikey = self.config.get(tautulli_section, 'apikey')
                    scheme = 'https://' if self.config.getboolean(
                        tautulli_section, 'ssl') else 'http://'
                    verify_ssl = self.config.getboolean(
                        tautulli_section, 'verify_ssl')
                    if scheme != 'https://':
                        verify_ssl = False
                    get_activity = self.config.getboolean(
                        tautulli_section, 'get_activity')
                    get_activity_run_seconds = self.config.getint(
                        tautulli_section, 'get_activity_run_seconds')

                    server = TautulliServer(server_id, scheme + url, fallback_ip, apikey, verify_ssl, get_activity,
                                            get_activity_run_seconds)
                    self.tautulli_servers.append(server)
                except configparser.NoOptionError as e:
                    self.tautulli_enabled = False
                    self.logger.error(
                        '%s disabled. Error: %s', tautulli_section, e)

        # Parse Ombi options
        self.ombi_enabled = self.enable_check('ombi_server_ids')

        if self.ombi_enabled:
            for server_id in self.ombi_enabled:
                ombi_section = 'ombi-' + str(server_id)
                try:
                    url = self.config.get(ombi_section, 'url')
                    apikey = self.config.get(ombi_section, 'apikey')
                    scheme = 'https://' if self.config.getboolean(
                        ombi_section, 'ssl') else 'http://'
                    verify_ssl = self.config.getboolean(
                        ombi_section, 'verify_ssl')
                    if scheme != 'https://':
                        verify_ssl = False
                    request_type_counts = self.config.getboolean(
                        ombi_section, 'get_request_type_counts')
                    request_type_run_seconds = self.config.getint(
                        ombi_section, 'request_type_run_seconds')
                    request_total_counts = self.config.getboolean(
                        ombi_section, 'get_request_total_counts')
                    request_total_run_seconds = self.config.getint(
                        ombi_section, 'request_total_run_seconds')

                    server = OmbiServer(server_id, scheme + url, apikey, verify_ssl, request_type_counts,
                                        request_type_run_seconds, request_total_counts, request_total_run_seconds)
                    self.ombi_servers.append(server)
                except configparser.NoOptionError as e:
                    self.ombi_enabled = False
                    self.logger.error(
                        '%s disabled. Error: %s', ombi_section, e)

        # Parse ASA opts
        self.ciscoasa_enabled = self.enable_check('ciscoasa_firewall_ids')

        if self.ciscoasa_enabled:
            for firewall_id in self.ciscoasa_enabled:
                ciscoasa_section = 'ciscoasa-' + str(firewall_id)
                try:
                    url = self.config.get(ciscoasa_section, 'url')
                    username = self.config.get(ciscoasa_section, 'username')
                    password = self.config.get(ciscoasa_section, 'password')
                    scheme = 'https://' if self.config.getboolean(
                        ciscoasa_section, 'ssl') else 'http://'
                    verify_ssl = self.config.getboolean(
                        ciscoasa_section, 'verify_ssl')
                    if scheme != 'https://':
                        verify_ssl = False
                    outside_interface = self.config.get(
                        ciscoasa_section, 'outside_interface')
                    get_bandwidth_run_seconds = self.config.getint(
                        ciscoasa_section, 'get_bandwidth_run_seconds')

                    firewall = CiscoASAFirewall(firewall_id, scheme + url, username, password, outside_interface,
                                                verify_ssl, get_bandwidth_run_seconds)
                    self.ciscoasa_firewalls.append(firewall)
                except configparser.NoOptionError as e:
                    self.ciscoasa_enabled = False
                    self.logger.error(
                        '%s disabled. Error: %s', ciscoasa_section, e)
