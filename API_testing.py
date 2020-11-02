import requests
import os
import json
from fnmatch import fnmatch
import re
import time
import base64

class Iseek:

	def __init__(self):
		self.server_name = "http://127.0.0.1"
		self.params = {}
		self.headers = {'user-agent': 'my-app/0.0.1', 'Cadseek-Key': '181ed793a55341669132e3797bc1bff7f13cd29bd004440e809d2bfe782a3f1b'}
		self.manifest_entries = []



	def get_manifest_id (self, file_name):
		"""Determines the proper manifest type for a given file. Right now
		we're just going to look at file extensions, but to do this right
		we would have to look at file contents to separate out, for example,
		the different PNG manifest items, or the difference between Creo and
		NX .prt files."""
		
		# so let's get the extension. Watch out for Creo extension version
		# numbers, because they exist in my test set.
		splt = os.path.splitext(file_name)
		ext = splt[1].lower()
		name = splt[0]
		
		# is this an extension version? skip it
		extension_version = ""
		if re.match(r'\.\d+', ext):
			extension_version = ext
			ext = os.path.splitext(name)[1].lower()
		
		match = [m for m in self.manifest_entries if m['extension'] == ext and m['manifest_id'] in range(4000,4999)]
		
		if len(match) == 1:
			#print ("Manifest ID for ", ext, " = ", match[0]['manifest_id'])
			return (match[0]['manifest_id'])
		else:
			#print ("Manifest ID not identified")
			return (-1)

    
    
    
    

	def import_file (self, path, name):

		url = self.server_name + "/api/v1/datasets/" + dataset_name + "/models"
		actual_file_path = os.path.join(path,name)

		# We have to handle Creo-style "extension versions" like "foo.prt.3"
		extension_version = ""
		ext = os.path.splitext(name)[1].lower()
		if re.match(r'\.\d+', ext):
			extension_version = ext
			name = os.path.splitext(name)[0]
			ext = os.path.splitext(name)[1].lower()
		

		#body_template = '{"name":"{name}","metadata":[\{"Key"
		body_data = {
			'name':name,
			'metadata':[ 
				{
					'Key':'Filename_ISEEK',
					'Value':name
				},
				{
					'Key':'Filepath_ISEEK',
					'Value':path
				}
				]
			}
		
		
		
		if extension_version != "":
			body_data['metadata'].append({'Key':'ExtensionVersion_ISEEK','Value':extension_version})
			
		json_body = json.dumps(body_data)
		#print (json_body)
		
		r = requests.post(url=url, data=json_body, params=self.params, headers=self.headers)
		if r.status_code == 201:
			print ("Imported: ", name);
			location = r.headers['Location']
			print ("RETURNED LOCATION:", location)
			#response = r.json()
			#print (response)
			# Next, we can try to commit the file manifest item. Oh, we need a way
			# to map a file to a manifest item ID. Which, as we've seen in 
			# cad2cadseek, is not as easy as it sounds.
			manifest_id = self.get_manifest_id(os.path.join(path,name))
			if manifest_id != -1:
				url2 = "{0}/assets/{1}".format (location, manifest_id)
				print ('   url=', url2)
				print ('   filepath=', actual_file_path)
				f = open(actual_file_path, 'rb')
				
				data = f.read()
				#files = {'file': (name, open(actual_file_path, 'rb'), "multipart/form-data")}
				#files = {'file': (name, "12345", "multipart/form-data")}
				#base64_body = base64.b64encode(s)
				#r2 = requests.post(url=url2, files=files, params=self.params, headers=self.headers)
				headers = self.headers
				headers["content-type"] = "application/octet-stream"
				r2 = requests.post(url=url2, data=data, params=self.params, headers=self.headers)
				if r2.status_code == 201:
					print ('   Committed source file ')
				else:
					print ('   Failed to commit src file, status ', r2.status_code)
		else:
			print ("Failed: ", name, ": ", r.json())



	def import_files (self, dataset_name, files_location):
		""" Run import_file on every file in a folder. """
		patterns = ["*.asm", "*.prt", "*.2"]
		names=[name for name in os.listdir(files_location) for pattern in patterns if fnmatch(name,pattern)]

		print ('import_files: found ', len(names))
			
		for i in range (0, min(10,len(names))): # let's not do the whole folder while testing, just grab 1st 10 files
			self.import_file (files_location, names[i])
			
			




	def initialize (self):
		print('\nGet Datasets:\n')
		url = self.server_name + "/api/v1/datasets"
		r = requests.get(url=url, params=self.params, headers=self.headers)

		print (r.json())

		# fill in manifest object type stuff
		url2 = self.server_name + "/api/v1/serverinfo/manifestobjecttype"
		r2 = requests.get(url=url2, params=self.params, headers=self.headers)

		#print (r2.json())
		print('\nGet ManifestObjectTypes:\n')
		self.manifest_entries = r2.json()['manifestobjecttype']

		print ('status code: ', r2.status_code)
		print ('count: ', len(self.manifest_entries))
		#print (self.manifest_entries)

		for item in self.manifest_entries:
			print ("{0}\t{1}\t\t{2}".format (item['manifest_id'],item['extension'],item['description']))



	def wait_for_task (self, task_url):
		""" Waits for a task to complete. Returns True if we reach 100% or
		False if there's an error."""
		result = False
		done = False
		while not done:
			try:
				r2 = requests.get(url=task_url, params=self.params, headers=self.headers)
				if r2.status_code == 200:
					progress = r2.json()['progress']
					print ("Progress: {0}%".format(progress))
					if progress == 100.0:
						done = True
						result = True
					else:
						time.sleep(2) # time in seconds
				else:
					print ("Error checking task status:", r2.status_code)
					done = True
			except OSError as e:
				print ('Exception in status check:', e)
				done = True
		return result
					
					

	def classify (self, remote_name):
		""" Trigger a new classification. """
		result = False
		print ("Classifying dataset {0}".format(remote_name))
		url = "{0}/api/v1/datasets/{1}/classify".format(self.server_name, remote_name)
		r = requests.post(url=url, params=self.params, headers=self.headers)
		if r.status_code == 200:
			task_url = r.headers['Location']
			print ("  task location: ", task_url)
			result = self.wait_for_task (task_url)
		elif r.status_code in {400, 401, 403}:
			print ("Error:", r.status_code)
			msg = r.json()['error']
			print (msg)
		else:
			print ("Error")
		
		return result
				#print (r2.status_code)
				#print (r2.text)
				#url3 = "{0}/api/v1/tasks".format(self.server_name)
				#r3 = requests.get(url=url3, params=self.params, headers=self.headers)
				#print("Get Tasks:")
				#print(r3.status_code)
				#print(r3.text)
				



	def metadata_search (self):
		#args = [{'Filename_ISEEK',2,'z32983.prt'}]
		view = 'summary'
		#view = 'detail'
		params = {'view':view,'d':'test1','qn0':'Filename_ISEEK','qo0':2,'qv0':'02474_ab.asm','qc':1}
		url = "{0}/api/v1/actions/search".format (self.server_name)
		r = requests.get(url=url, params=params, headers=self.headers)
		print(r.status_code)
		if r.status_code == 200:
			json_result = r.json()
			#print(r.json())
			for dataset in json_result['datasets']:
				print (dataset['name'], ": ", len(dataset['results']), " results")
				for result in dataset['results']:
					print ("  " + result['name'] + ": " + result['id'])
		else:
			if r.status_code == 400:
				print('ERROR: ' + r.json()['error'])
			else:
				print('ERROR')
		


	def upload_target_and_search (self, filename):
		url = "{0}/api/v1/actions/uploadsearchtarget".format(self.server_name)

		"""
		f = open(filename, 'rb')
		data = f.read()
		headers = self.headers
		headers["content-type"] = "application/octet-stream"
		r = requests.post(url=url, data=data, params=self.params, headers=self.headers)
		"""

		# sending data as manually base-64 encoded text.
		params = {'search_target_filename':'test_file.prt'}
		f = open(filename, 'rb')
		data = f.read()
		base64_data = base64.b64encode(data)
		files = {'search_target_content': ('test_file.prt', base64_data, "multipart/form-data")}
		#files = {'search_target_content': ("test_file.prt", open(filename, 'rb'), "application/octet-stream")}#"multipart/form-data")}
		#files = {'file': ("test_file", open(filename, 'rb'), "multipart/form-data")}
		r = requests.post(url=url, files=files, params=params, headers=self.headers)
		#files = {'file': (name, "12345", "multipart/form-data")}
		#base64_body = base64.b64encode(s)
		
		
		if r.status_code == 200:
			print ('   Uploaded search target ')
			print ('  ', r.text)
		else:
			print ('   Failed to upload search target, status ', r.status_code)
			print ('  ', r.text)



""" Test code for the iseek object """       
iseek = Iseek()      
iseek.initialize()

#files_location = "R:\Transfer\CAD Data\Deere Partsearch"
files_location = "test_files"
dataset_name = "test1"

#import files test
#iseek.import_files (dataset_name, files_location)


#classification test
classifier_task = iseek.classify("test1")
print ("classifier task returned", classifier_task)
print ("\n\n")

#test "task not found"
print("Testing 'task not found' error")
iseek.wait_for_task("http://127.0.0.1:80/api/v1/tasks/9722b20d-6680-41c8-8c2d-c2b28efd8284")
print("Done\n\n")


print ("Testing upload search target")
iseek.upload_target_and_search ("test_files\\15h3.prt")


# test metadata search
iseek.metadata_search()
