"""
Utilities class for converting cyborg observations and action objects into 
dictionaries and vice-versa. The only two methods that should be used from this class are
obverations_to_dict(), action_object_to_dict(), and action_dict_to_object()
"""

from CybORG.Shared.Enums import *
import json
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from copy import deepcopy
from CybORG.Shared.Actions import *


class CyborgObsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, IPv4Address):
            return {"IPv4Address": self._get_specifics_ipv4(obj=obj)}

        if isinstance(obj, IPv4Network):
            return {
                "IPv4Network": self._get_specifics_ipv4(obj=obj),
                "broadcast_address": self._get_specifics_ipv4(obj.broadcast_address),
                "hostmask": self._get_specifics_ipv4(obj.hostmask),
                "netmask": self._get_specifics_ipv4(obj.netmask),
                "network_address": self._get_specifics_ipv4(obj.network_address),
            }
        if isinstance(obj, Action):
            return {
                "Action": self._get_common_class_params_session_agent_hostname(obj),
            }
        return super().default(obj)

    def _get_specifics_ipv4(self, obj) -> dict:
        return obj.compressed
        # Below is a more full data represetation of the ipv4 object information
        # return {
        #     "compressed": obj.compressed,
        #     "exploded": obj.exploded,
        #     "is_global": obj.is_global,
        #     "is_link_local": obj.is_link_local,
        #     "is_loopback": obj.is_loopback,
        #     "is_multicast": obj.is_multicast,
        #     "is_private": obj.is_private,
        #     "is_reserved": obj.is_reserved,
        #     "is_unspecified": obj.is_unspecified,
        #     "max_prefixlen": obj.max_prefixlen,
        # }


class CyborgActionEncoder(json.JSONEncoder):

    def default(self, obj):
        COMMON_PARAMS_CLASS_SESSION_AGENT_HOSTNAME = [
            Analyse,
            Remove,
            Misinform,
            DecoyApache,
            DecoyFemitter,
            DecoyHarakaSMPT,
            DecoySmss,
            DecoySSHD,
            DecoySvchost,
            DecoyTomcat,
            DecoyVsftpd,
            Restore,
            PrivilegeEscalate,
            Impact,
        ]
        COMMON_PARAMS_CLASS_SESSION_AGENT_IP = [DiscoverNetworkServices]
        COMMON_PARAMS_CLASS_SESSION_AGENT_IP_TARGET = [
            SSHBruteForce,
            BlueKeep,
            EternalBlue,
            FTPDirectoryTraversal,
            HarakaRCE,
            HTTPRFI,
            HTTPSRFI,
            SQLInjection,
        ]

        if isinstance(obj, tuple(COMMON_PARAMS_CLASS_SESSION_AGENT_HOSTNAME)):
            return self._get_common_class_params_session_agent_hostname(obj)

        if isinstance(obj, tuple(COMMON_PARAMS_CLASS_SESSION_AGENT_IP)):
            return self._get_common_class_params_session_agent_ip(obj)
        if isinstance(obj, tuple(COMMON_PARAMS_CLASS_SESSION_AGENT_IP_TARGET)):
            return self._get_common_class_params_session_agent_ip_target(obj)

        if isinstance(obj, Enum):
            return obj.value

        if isinstance(obj, Sleep):
            return {"Action": obj.__class__.__name__}

        if isinstance(obj, ExploitRemoteService):
            return {
                "Action": obj.__class__.__name__,
                "session": obj.session,
                "agent": obj.agent,
                "ip_address": obj.ip_address.exploded,
                "priority": obj.priority,
            }

        if isinstance(obj, Monitor):
            return {
                "Action": obj.__class__.__name__,
                "session": obj.session,
                "agent": obj.agent,
            }
        if isinstance(obj, DiscoverRemoteSystems):
            return {
                "Action": obj.__class__.__name__,
                "session": obj.session,
                "agent": obj.agent,
                "subnet": obj.subnet.exploded,
            }
        return super().default(obj)

    def _get_common_class_params_session_agent_hostname(self, obj) -> dict:
        return {
            "Action": obj.__class__.__name__,
            "session": obj.session,
            "agent": obj.agent,
            "hostname": obj.hostname,
        }

    def _get_common_class_params_session_agent_ip(self, obj) -> dict:
        return {
            "Action": obj.__class__.__name__,
            "session": obj.session,
            "agent": obj.agent,
            "ip_address": obj.ip_address.exploded,
        }

    def _get_common_class_params_session_agent_ip_target(self, obj) -> dict:
        return {
            "Action": obj.__class__.__name__,
            "session": obj.session,
            "agent": obj.agent,
            "ip_address": obj.ip_address.exploded,
            "target_session": obj.target_session,
        }


class CyborgActionDecoder(json.JSONDecoder):
    COMMON_PARAMS_SESSION_AGENT_HOSTNAME = [
        "Analyse",
        "Remove",
        "Misinform",
        "DecoyApache",
        "DecoyFemitter",
        "DecoyHarakaSMPT",
        "DecoySmss",
        "DecoySSHD",
        "DecoySvchost",
        "DecoyTomcat",
        "DecoyVsftpd",
        "Restore",
        "PrivilegeEscalate",
        "Impact",
    ]

    COMMON_PARAMS_SESSION_AGENT_IP_TARGET = [
        "SSHBruteForce",
        "BlueKeep",
        "EternalBlue",
        "FTPDirectoryTraversal",
        "HarakaRCE",
        "HTTPRFI",
        "HTTPSRFI",
        "SQLInjection",
    ]

    def __init__(self, *args, **kwargs):
        # super.__init__(self, object_hook=self.object_hook, *args, **kwargs)
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct):
        # Verify that this is an expected cyborg action
        if "Action" in dct:
            # First check the edge cases, specifically the sleep action
            if dct["Action"] == "Sleep":
                return Sleep()
            # parsing common params among all actions
            session = dct["session"]
            agent = dct["agent"]
            if dct["Action"] == "Monitor":
                return Monitor(session=session, agent=agent)
            if dct["Action"] == "ExploitRemoteService":
                ip_address = dct["ip_address"]
                if "priority" in dct:
                    priority = dct["priority"]
                    return ExploitRemoteService(
                        session=session,
                        agent=agent,
                        ip_address=ip_address,
                        priority=priority,
                    )
                else:
                    return ExploitRemoteService(
                        session=session, agent=agent, ip_address=ip_address
                    )
            if dct["Action"] == "DiscoverNetworkServices":
                ip_address = dct["ip_address"]
                return DiscoverNetworkServices(
                    session=session, agent=agent, ip_address=ip_address
                )
            if dct["Action"] == "DiscoverRemoteSystems":
                subnet = dct["subnet"]
                return DiscoverRemoteSystems(
                    session=session, agent=agent, subnet=subnet
                )
            # --------------------
            if dct["Action"] in self.COMMON_PARAMS_SESSION_AGENT_HOSTNAME:
                hostname = dct["hostname"]
                if dct["Action"] == "Analyse":
                    return Analyse(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "Remove":
                    return Remove(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "Misinform":
                    return Misinform(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "DecoyApache":
                    return DecoyApache(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "DecoyFemitter":
                    return DecoyFemitter(
                        session=session, agent=agent, hostname=hostname
                    )
                if dct["Action"] == "DecoyHarakaSMPT":
                    return DecoyHarakaSMPT(
                        session=session, agent=agent, hostname=hostname
                    )
                if dct["Action"] == "DecoySmss":
                    return DecoySmss(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "DecoySSHD":
                    return DecoySSHD(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "DecoySvchost":
                    return DecoySvchost(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "DecoyTomcat":
                    return DecoyTomcat(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "DecoyVsftpd":
                    return DecoyVsftpd(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "Restore":
                    return Restore(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "Impact":
                    return Impact(session=session, agent=agent, hostname=hostname)
                if dct["Action"] == "PrivilegeEscalate":
                    return PrivilegeEscalate(
                        session=session, agent=agent, hostname=hostname
                    )
            if dct["Action"] in self.COMMON_PARAMS_SESSION_AGENT_IP_TARGET:
                ip_address = dct["ip_address"]
                target_session = dct["target_session"]
                if dct["Action"] == "SSHBruteForce":
                    return SSHBruteForce(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )
                if dct["Action"] == "BlueKeep":
                    return BlueKeep(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )
                if dct["Action"] == "EternalBlue":
                    return EternalBlue(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )
                if dct["Action"] == "FTPDirectoryTraversal":
                    return FTPDirectoryTraversal(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )
                if dct["Action"] == "HarakaRCE":
                    return HarakaRCE(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )
                if dct["Action"] == "HTTPRFI":
                    return HTTPRFI(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )
                if dct["Action"] == "HTTPSRFI":
                    return HTTPSRFI(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )
                if dct["Action"] == "SQLInjection":
                    return SQLInjection(
                        session=session,
                        agent=agent,
                        target_session=target_session,
                        ip_address=ip_address,
                    )

        return None
        # return dct


def observations_to_dict(obs, verbose=False) -> dict:
    serialized_json = json.dumps(obs, cls=CyborgObsEncoder, indent=3)
    if verbose:
        # Saving to verify output looks correct
        file_path = "output.json"
        with open(file_path, "w") as json_file:
            json_file.write(
                serialized_json,
            )
    return serialized_json


def action_object_to_dict(obs, verbose=False) -> dict:
    return json.dumps(obs, cls=CyborgActionEncoder, indent=3)


def action_dict_to_object(action_dict, verbose=False) -> object:
    return json.loads(action_dict, cls=CyborgActionDecoder)


def action_space_to_dict(obs, verbose=False) -> dict:
    # it needs to be able to parse the responses the the cyborhobsencoder has, and in
    # addition it also needs to to do some conversion for the 'actions fields so that it returns a dictionary of
    # actions name to boolean
    # Handling specific edge case where the keys that were used for the 'subnet', 'ip_address' and 'action fields are objects
    _subnet = obs["subnet"]
    parsed_subnet = [{entry.compressed: _subnet[entry]} for entry in _subnet]

    _ip_address = obs["ip_address"]
    parsed_ip_address = [{ip.compressed: _ip_address[ip]} for ip in _ip_address]

    _action = obs["action"]
    parsed_action = [
        {action_instance.__name__: _action[action_instance]}
        for action_instance in _action
    ]

    obs["subnet"] = parsed_subnet
    obs["ip_address"] = [parsed_ip_address]
    obs["action"] = parsed_action

    return json.dumps(obs)


def no_challenge_obs_to_list(obs):
    return obs.tolist()


def challenge_wrapper_info_to_dict(info) -> dict:
    info["observation"] = no_challenge_obs_to_list(info["observation"])
    info["action"] = info["action"].__class__.__name__
    return info
