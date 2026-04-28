import os
import inspect
import json
import shutil
import yaml
from CybORG import CybORG
from bs4 import BeautifulSoup


def create_user_pages(db_info, uuid=None):
    user_pages_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + uuid + '/user_pages'
    if not os.path.exists(user_pages_path):
        os.makedirs(user_pages_path)
    for user in db_info['users']:
        html_content = f"""<!DOCTYPE html>
                          <html>
                          <body>
                          <h1>This is your user page!</h1>
                          <p id="para">Welcome to your page</p>
                          <p id="para0">{user['name']}</p>
                          <p id="para1">{user['info']}</p>
                          </body>
                          </html>                    
                       """
        soup = BeautifulSoup(html_content, "html.parser")
        html_content = soup.prettify()
        with open(user_pages_path + '/' + user['name'] + '.html', "w") as file:
            file.write(html_content)

def create_init_db(scenario_path, uuid=None):
    db_initial_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + uuid + '/initial/'
    if not os.path.exists(db_initial_path):
        os.makedirs(db_initial_path)
    db_initial_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + uuid + '/initial/auth.json'
    with open(scenario_path, "r") as file:
        data = yaml.safe_load(file)
    
    data_db = {'users': []}
    counter = 0
    for key in list(data['Hosts'].keys()):
        if "user" in key.lower() or "subnet_0" in key.lower():
            data_db['users'].append({'name': key, 'id': counter, 'info': key})
            counter += 1
    
    with open(db_initial_path, "w") as json_file:
        json.dump(data_db, json_file, indent=4)

    create_user_pages(db_info=data_db, uuid=uuid)


def move_files(hostname=None, uuid=None):
    services_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services'
    if not os.path.exists(services_path + '/' + uuid):
        os.makedirs(services_path + '/' + uuid)
    if hostname == 'front':
        try:
            source_file = os.path.join(services_path, 'initial', 'front.html')
            destination_file = os.path.join(services_path, uuid, 'front.html')
            if os.path.exists(destination_file):
                os.remove(destination_file)
            shutil.copyfile(source_file, destination_file)
        except Exception as e:
            print(e)
    elif hostname == 'auth':
        try:
            source_file = os.path.join(services_path, uuid, 'initial', 'auth.json')
            destination_file = os.path.join(services_path, uuid, 'auth.json')
            if os.path.exists(destination_file):
                os.remove(destination_file)
            shutil.copyfile(source_file, destination_file)
        except Exception as e:
            print(e)
    else:
        try:
            source_file = os.path.join(services_path, 'initial', 'front.html')
            destination_file = os.path.join(services_path, uuid, 'front.html')
            if os.path.exists(destination_file):
                os.remove(destination_file)
            shutil.copyfile(source_file, destination_file)

            source_file = os.path.join(services_path, uuid, 'initial', 'auth.json')
            destination_file = os.path.join(services_path, uuid, 'auth.json')
            if os.path.exists(destination_file):
                os.remove(destination_file)
            shutil.copyfile(source_file, destination_file)
        except Exception as e:
            print(e)

