import datetime
import socket


class ServerNA2(object):
    IP = '144.217.72.80'
    PORT = 6385
    SERVER_STATUS = "OFFLINE"
    SERVER_NAME = "USA (Server logowania)"
    FLAG = ':flag_us:'


class ServerNA(object):
    IP = '144.217.72.80'
    PORT = 6387
    SERVER_STATUS = "OFFLINE"
    SERVER_NAME = "USA"
    FLAG = ':flag_us:'


class ServerBR(object):
    IP = '177.54.152.16'
    PORT = 6387
    SERVER_STATUS = "OFFLINE"
    SERVER_NAME = "BR"
    FLAG = ':flag_br:'


class ServersStatus:
    def __init__(self):
        self.server_NA = ServerNA()
        self.server_BR = ServerBR()

        self.servers = ['BR', 'NA']

        self.last_status_check = datetime.datetime.now()
        self.status_check_time_limit = 10
        self.update_status_na()
        self.update_status_br()

    def simple_status_check(self):
        # Uproszczoen sprawdznie statusu
        # jezeli udaje sie socket.connect() to zakladamy, ze jest ONLINE

        msg = 'Nastepujące serwery BloodStone zmieniły swój status:\n\n'

        status_has_changed = False
        for server in self.servers:
            server_obj = getattr(self, 'server_{}'.format(server))

            current_status = server_obj.SERVER_STATUS
            with socket.socket() as s:
                try:
                    s.connect((server_obj.IP, server_obj.PORT))
                    if current_status != 'ONLINE':
                        status_has_changed = True
                        server_obj.SERVER_STATUS = 'ONLINE'
                        msg += '{} {}:\n```CSS\nOFFLINE -> ONLINE\n```\n'.format(
                            server_obj.FLAG,
                            server_obj.SERVER_NAME
                        )
                except Exception as e:
                    if current_status != 'OFFLINE':
                        status_has_changed = True
                        server_obj.SERVER_STATUS = 'OFFLINE'
                        msg += '{} {}:\n```\nONLINE -> OFFLINE\n```\n'.format(
                            server_obj.FLAG,
                            server_obj.SERVER_NAME
                        )
        if not status_has_changed:
            return False

        return msg

    def try_to_login(self, IP, PORT):
        # Proba zalogowania na postac do gry
        packets = [
            # Login server
            {
                'ip': '144.217.72.80',
                'port': 6385,
                'packet': '2D 00 00 00 00 00 00 00 00 00 00 00 02 12 00 00 00 09 00 41 72 61 6E 61 6B 74 75 33 0F 00 37 4E 59 6A 39 66 30 61 67 54 26 47 34 52 23',
                'valid_packet': {4: 0x97, 5: 0x7F},
                'limit': None,
                'close': True
            },
            {
                'ip': IP,
                'port': PORT,
                'packet': '29 00 00 00 00 00 00 00 00 00 00 00 03 09 00 41 72 61 6E 61 6B 74 75 33 0F 00 37 4E 59 6A 39 66 30 61 67 54 26 47 34 52 23',
                'valid_packet': {4: 0xBD, 5: 0x7F},
                'limit': None,
                'close': True
            },
            {
                'ip': IP,
                'port': PORT,
                'packet': '43 00 00 00 00 00 00 00 00 00 00 00 06 01 12 00 00 00 01 09 00 41 72 61 6E 61 6B 74 75 33 0F 00 37 4E 59 6A 39 66 30 61 67 54 26 47 34 52 23 7D 21 00 00 94 45 00 00 6F 0F 00 00 94 6D 00 00 B4 14 00 00',
                'valid_packet': None,
                'limit': 8,
                'close': False
            },
        ]

        for p in packets:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((p['ip'], p['port']))
            except ConnectionRefusedError:
                return False
            except Exception as e:
                print(e)
                return False

            if not self.send_and_recv(
                    s, p['packet'],
                    valid_packet=p['valid_packet'],
                    packet_limit=p['limit'],
            ):
                # Server Offline
                return False

            if 'close' in p and p['close']:
                s.close()

        # LOGOUT PACKET
        self.send_and_recv(
            s, '0D 00 00 00 00 00 00 00 00 00 00 00 07',
            packet_limit=1,
        )
        s.close()

        return True

    def send_and_recv(self, s, to_send, valid_packet=None, packet_limit=None):
        s.send(bytes.fromhex(to_send))
        s.settimeout(10.0)

        recv_packets = 0
        while True:
            try:
                data = s.recv(4096)
            except Exception:
                return False

            if data:
                recv_packets += 1

                if packet_limit and (recv_packets >= packet_limit):
                    return True

                if valid_packet:
                    for packet_offset, valid_byte in valid_packet.items():
                        if data[packet_offset] != valid_byte:
                            continue

                    return True

    def _check_time_limit(self):
        if (datetime.datetime.now() - self.last_status_check).seconds <= self.status_check_time_limit:
            return False

        self.last_status_check = datetime.datetime.now()

        return True
    ####################
    # Status servera NA
    ####################

    def update_status_na(self):
        if not self._check_time_limit():
            return False

        if self.try_to_login(
            self.server_NA.IP,
            self.server_NA.PORT,
        ):
            self.server_NA.SERVER_STATUS = "ONLINE"
        else:
            self.server_NA.SERVER_STATUS = "OFFLINE"

    ####################
    # Status servera BR
    ####################

    def update_status_br(self):
        if not self._check_time_limit():
            return False

        if self.try_to_login(
            self.server_BR.IP,
            self.server_BR.PORT,
        ):
            self.server_BR.SERVER_STATUS = "ONLINE"
        else:
            self.server_BR.SERVER_STATUS = "OFFLINE"

    def get_status_msg(self):
        msg = "Status serwerów gry BloodStone:\n\n"

        for server in self.servers:
            s_obj = getattr(self, 'server_{}'.format(server))
            server_status_msg = "{} {} \n{}\n\n"
            if s_obj.SERVER_STATUS == 'ONLINE':
                status = "```CSS\n-ONLINE\n```"
            else:
                status = "```diff\n-OFFLINE\n```"

            msg += server_status_msg.format(
                s_obj.FLAG,
                s_obj.SERVER_NAME,
                status,
            )

        return msg
