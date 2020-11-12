import csv
import json
import time
from datetime import datetime

import requests

now_start = datetime.now()
print("Start Time: {}".format(now_start.strftime("%D %H:%M:%S")))

total_start = time.perf_counter()

# http://fdxx90app420.jdnet.deere.com:88/api/v1/actions/search?view=summary&d=*&qc=1&qn0=Name&qo0=2&qv0=m147138.prt
cadseek_hostname = 'http://fdxx90app731.jdnet.deere.com'
cadseek_search_api = cadseek_hostname + '/api/v1/actions/search'
cadseek_dataset = '*'
cadseek_apikey_read = ''

rows_in_file = 0
unqiue_parent_cad_found = 0
cad_found_in_cadseek = 0
unique_similar_cad_found = 0
time_avg = list()
with open('performance_test.csv', mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    # next(csv_reader)
    for row in csv_reader:
        rows_in_file += 1
        cadseek_cadname = row['Part Number'] + '.PRT'
        payload = {'qc': '1',
                   'qn0': 'Name',
                   'qo0': '2',  # 2 is equals
                   'qv0': cadseek_cadname,
                   'd': cadseek_dataset,
                   'view': 'detail'}
        headers = {'Cadseek-Key': cadseek_apikey_read}

        resp = requests.post(cadseek_search_api, data=payload, headers=headers)
        json_resp = json.loads(resp.text)

        # get a cadseek id of canidate CAD
        cadseek_id = None
        cadseek_revision = ''
        cadseek_iteration = ''
        cadseek_obid = ''
        for dataset in json_resp['datasets']:
            for result in dataset['results']:
                cadseek_id = result['id']
                for metadata in result['metadata']:
                    if metadata['Key'] == 'Revision':
                        cadseek_revision = metadata['Value']
                    if metadata['Key'] == 'Iteration':
                        cadseek_iteration = metadata['Value']
                    if metadata['Key'] == 'CadDocumentId':
                        cadseek_obid = metadata['Value']
                break
            if cadseek_id is not None:
                break

        # go to next line in csv file if cad was not found in CADSeek
        if cadseek_id is None:
            continue

        cad_found_in_cadseek += 1

        # all datasets
        payload = {'d': cadseek_dataset,
                   'view': 'detail',
                   'g': cadseek_id}
        # payload = {'d': cadseek_dataset,
        #            'view': 'detail',
        #            'g': cadseek_id,
        #            'maxresults': 100}
        start = time.perf_counter()
        detail_search_resp = requests.post(cadseek_search_api, data=payload, headers=headers)
        finish = time.perf_counter()
        time_avg.append(finish - start)
        detail_search_resp_json = json.loads(detail_search_resp.text)

        unique_child_cad = dict()
        parent_has_similar_cad_found = False
        for result_datasets in detail_search_resp_json['datasets']:
            for result_cad_object in result_datasets['results']:
                # skip if score is not greater than 75% and the child cad name is different than the parent cad name
                target_cad_name = result_cad_object['name']
                target_cad_score = result_cad_object['score']
                target_cad_sizeratio = result_cad_object['sizeRatio']
                if cadseek_cadname.lower() != target_cad_name and target_cad_score > 0.75:
                    parent_has_similar_cad_found = True
                    target_cad_revision = ''
                    target_cad_iteration = ''
                    target_cad_obid = ''
                    for metadata in result_cad_object['metadata']:
                        if metadata['Key'] == 'Revision':
                            target_cad_revision = metadata['Value']
                        if metadata['Key'] == 'Iteration':
                            target_cad_iteration = metadata['Value']
                        if metadata['Key'] == 'CadDocumentId':
                            target_cad_obid = metadata['Value']
                    unique_child_cad[target_cad_name + '_' + target_cad_revision + '_' + target_cad_obid] = \
                        {'name': target_cad_name,
                         'revision': target_cad_revision,
                         'iteration': target_cad_iteration,
                         'obid': target_cad_obid,
                         'score': target_cad_score,
                         'sizeRatio': target_cad_sizeratio}

        if parent_has_similar_cad_found:
            unqiue_parent_cad_found += 1

        for child_cad in unique_child_cad:
            print('{},{},{},{},{},{},{},{},{},{}'.format(cadseek_cadname.lower(), cadseek_revision, cadseek_iteration,
                                                         cadseek_obid,
                                                         unique_child_cad[child_cad]['name'],
                                                         unique_child_cad[child_cad]['revision'],
                                                         unique_child_cad[child_cad]['iteration'],
                                                         unique_child_cad[child_cad]['obid'],
                                                         unique_child_cad[child_cad]['score'],
                                                         unique_child_cad[child_cad]['sizeRatio']))
            unique_similar_cad_found += 1

print()
print("Total number of CAD in file: {}".format(rows_in_file))
print("Total number of CAD found in CADSeek: {}".format(cad_found_in_cadseek))
print("Total number of CAD found in CADSeek wth similar CAD found: {}".format(unqiue_parent_cad_found))
print("Total number of similar CAD found in CADSeek: {}".format(unique_similar_cad_found))

print()
print("Performance of API:")
total_time = 0
for time_value in time_avg:
    total_time += time_value
print("Total Number of Search API Calls: {}".format(len(time_avg)))
print("Total Time Spent for API Calls: {}".format(total_time))
print("Max Time: {}".format(max(time_avg)))
print("Min Time: {}".format(min(time_avg)))
print("Average Time: {}".format(total_time / len(time_avg)))

total_finish = time.perf_counter()
print()
print("Total time: {}".format(total_finish - total_start))

now_finish = datetime.now()
print("Start Time: {}".format(now_start.strftime("%D %H:%M:%S")))
print("Finish Time: {}".format(now_finish.strftime("%D %H:%M:%S")))
