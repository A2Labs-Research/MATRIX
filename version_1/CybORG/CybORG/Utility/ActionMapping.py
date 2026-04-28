from CybORG.Agents.Wrappers import EnumActionWrapper2, TrueTableWrapper
from prettytable import PrettyTable

def action_mapping(env, agent):
    enum_action_wrapper = EnumActionWrapper2(env=env)
    list_of_actions = enum_action_wrapper.get_action_space(agent=agent)
    true_table_wrapper = TrueTableWrapper(env=env)
    true_table = true_table_wrapper.get_agent_state('True')
    true_table_dict = prettytable_to_dict(true_table)
    dict_to_return={"status":"success"}
    for i in range(len(list_of_actions)):
        action_dict = identify_action(list_of_actions[i], true_table_dict,i)
        dict_to_return[i] = action_dict
    return dict_to_return

def prettytable_to_dict(table):
    headers = table.field_names
    table_str = str(table)
    rows = table_str.split('\n')[2:-1]  # Split the table string by newlines and exclude the header and footer
    data = []
    for row in rows:
        row_data = {}
        cells = row.split('|')[1:-1]  # Split the row by pipes and exclude empty cells and separators
        for idx, header in enumerate(headers):
            if idx < len(cells):
                row_data[header.strip()] = cells[idx].strip()  # Strip whitespace from cells and headers
            else:
                row_data[header.strip()] = None
        data.append(row_data)
    return data[1:]

def get_based_on_hostname(hostname, table_dict):
    for dictionary in table_dict:
        if dictionary["Hostname"] == hostname:
            return str(dictionary["IP Address"]), str(dictionary["Subnet"])

def get_based_on_ip_address(ip_address, table_dict):
    for dictionary in table_dict:
        if dictionary["IP Address"] == str(ip_address):
            return dictionary["Hostname"], str(dictionary["Subnet"])
'''def get_based_on_subnet(subnet, table_dict):
    pass'''

def identify_action(action, table_dict, number):
    action_name = action.__class__.__name__
    hostname = ""
    ip_address = ""
    subnet=""
    target_session = ""
    try:
        hostname = action.hostname
        ip_address, subnet = get_based_on_hostname(hostname, table_dict)
    except:
        pass
    if ip_address == "":
        try:
            ip_address = str(action.ip_address)
            hostname, subnet = get_based_on_ip_address(ip_address, table_dict)
        except:
            pass
    if subnet == "":
        try:
            subnet = str(action.subnet)
        except:
            pass
    if target_session =="":
        try:
            target_session = action.target_session
        except:
            pass
    dict_to_return= {
                    "number":number,
                    "name": action_name,
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "subnet": subnet,
                    "target_session":target_session}
    return dict_to_return