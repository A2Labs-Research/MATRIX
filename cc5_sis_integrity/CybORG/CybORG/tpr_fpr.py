from numbers import Number 
import random 
from typing import Union 

from CybORG.Shared.Actions.ConcreteActions import (
    ExploitAction,
    SSHBruteForce, 
    BlueKeep, 
    EternalBlue, 
    BlueKeep, 
    EternalBlue, 
    HTTPRFI, 
    HTTPSRFI, 
    FTPDirectoryTraversal, 
    SQLInjection, 
    HarakaRCE
)
 

EXPLOITS = [
    exploit_class.__name__ 
    for exploit_class in 
    [
        ExploitAction,
        SSHBruteForce, 
        BlueKeep, 
        EternalBlue, 
        BlueKeep, 
        EternalBlue, 
        HTTPRFI, 
        HTTPSRFI, 
        FTPDirectoryTraversal, 
        SQLInjection, 
        HarakaRCE
    ]
]

class HyperParams(): 
    def __init__(self, tpr: Union[Number, dict]=0.95, fpr: Number=0): 
        assert fpr >= 0 and fpr <= 1, "FPR must be between 0-1 inclusive"

        if isinstance(tpr, Number): 
            assert tpr >= 0 and tpr <= 1, "TPR must be between 0-1 inclusive"

            tpr_dict = {
                k: tpr 
                for k in EXPLOITS
            }
            tpr = tpr_dict 
        
        elif isinstance(tpr, dict): 
            for k in EXPLOITS: 
                if (v := tpr.get(k)) is None:
                    v = 0.95
                    tpr[k] = v # Set to default if not specified 
                
                assert v >= 0 and v <= 1, "All keys in TPR dict must be between 0-1 inclusive"
        
        self.tpr = tpr 
        self.fpr = fpr 

    def get_tpr(self): 
        return self.tpr 
    def get_fpr(self):
        return self.fpr 
    
    def set_tpr(self, tpr: Union[Number, dict]): 
        if isinstance(tpr, Number): 
            assert tpr >= 0 and tpr <= 1, "TPR must be between 0-1 inclusive"

            tpr_dict = {
                k: tpr 
                for k in EXPLOITS
            }
            tpr = tpr_dict 
        
        elif isinstance(tpr, dict): 
            for k in EXPLOITS: 
                if (v := tpr.get(k)) is None:
                    v = 0.95
                    tpr[k] = v # Set to default if not specified 
                
                assert v >= 0 and v <= 1, "All keys in TPR dict must be between 0-1 inclusive"
        
        self.tpr = tpr 

    def set_fpr(self, fpr: Number): 
        assert fpr >= 0 and fpr <= 0, "FPR must be between 0-1 inclusive"
        self.fpr = fpr 

HYPERPARAMS = HyperParams()


def generate_fp(src_ip, dst_ip): 
    fp = [
        {
            'PID': random.randint(1_000, 60_000),
            'Connections': [
                {
                    'local_port': random.randint(10_000, 60_000),
                    'remote_port': 4444, 
                    'local_address': src_ip,
                    'remote_address': dst_ip 
                }
            ]
        },
        {
            'Connections': [
                {
                    'local_port': random.choice([80,21,25,139,22,3389,443]),
                    'remote_port': random.randint(10_000, 60_000),
                    'local_address': src_ip, 
                    'remote_address': dst_ip
                }
            ]
        }
    ]

    return fp 