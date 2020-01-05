"""
backs up input file(s) to google drive account
all files are backed up under "senior_year" dir
-dir flag creates a path for files to live within "senior_year dir
@Author Stelios Papoutsakis
@date 12/29/19
""" 
import sys
import argparse
import os
import pickle
import logging
from apiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
def get_folder_id(dir, service):
	"""
	gets the id of the folder specified in the dir variable
	"""
	logging.debug('getting folder id for folder to place file')
	page_token = None
	results = []
	base_dir = None
	if '/' in dir:
		base_dir = os.path.basename(dir)
		logging.debug('found "/" in directory, will search based on name "{}"'.format(base_dir))
	# finding all directories with the name in either dir or base_dir
	while True:
		response=service.files().list(q="mimeType='application/vnd.google-apps.folder' and name='{}'".format(dir if not base_dir else base_dir),spaces='drive',
			fields="files(parents, name, id)",  pageToken=page_token).execute()
		results += response.get('files', [])
		page_token = response.get('nextPageToken', None)
		if page_token is None:
			break
	# if more than one result found prompt user to see which directory to use
	folder_id = None
	if len(results) > 1:
		logging.debug('more than one results where found, attempting to limit results')
		parent_name = {}
		for f in range(len(results)):
			name = '/'+results[f]['name'] 
			parent = results[f].get('parents')[0]
			# build full path for each entry in results
			while parent:
				res = service.files().get(fileId=parent, fields="*").execute()
				name = '/' + res['name'] + name 
				parent = res.get('parents', (None,))[0]
			# used to elimate results if a full path is specified
			if dir in name:
				parent_name[f] = name
			else:
				logging.debug('full path "{}" doesn\'t match dir "{}", skipping'.format(name, dir))
				del results[f]
		# if results where filter based on full path, skip user prompt	
		if len(parent_name.keys()) > 1:
			print('There seems to be more than one directory with that name, please specify (by typing the number next to the parent directory name) which directory to use')
			count = 0
			for name in [f['name'] for f in results]:
				print('{}. {}'.format(count, parent_name[count]))
				count += 1
		else:
			folder_id = results[0].get('id')
	elif len(results) > 0:
		folder_id = results[0].get('id')
	else:
		logging.error('dir "{}" was not found in google drive account'.format(dir))
		exit(1)
	print(folder_id)	
	exit()
def add_file(file, dir, service):
	"""
	adds a file to google drive mydrive
	dir is directory where file should be placed
	"""
	if dir is not None:
		get_folder_id(dir, service)
	if os.path.isfile(file):
		file_metadata = {'name': os.path.basename(os.path.realpath(file))}
		media = MediaFileUpload(file)
		file_id = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
		print('file "{}" was uploaded under file id "{}"'.format(file, file_id['id']))

	else:
		print('specified file name "{}" is not a file'.format(file))

def authenticate():
	"""
	authenticate connection to google drive based on SCOPE varibale
	returns a serice object that is ready for exicution
	"""
	cred = None
	SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets.readonly']
	file_dir = os.path.dirname(os.path.realpath(__file__))
	token_path = os.path.join(file_dir, 'token.pickle')
	if os.path.isfile(token_path):
		logging.debug('token file was found')
		with open(token_path, 'rb') as token:
           		cred = pickle.load(token)
	if not cred or not cred.valid:
		if cred and cred.expired and cred.refresh_token:
			logging.debug('cred is not valid')
			cred.refresh(Request())
		else:
			logging.debug('no cred found, asking for permission')
			if os.path.isfile(os.path.join(file_dir, 'credentials.json')):
				flow = InstalledAppFlow.from_client_secrets_file(os.path.join(file_dir, 'credentials.json'), SCOPES)
				cred = flow.run_local_server(port=0)
			else:
				logging.error('couldn\'t find "credentials.json", this is needed in order to authenticate users google drive. Please obtain this file and place it in the same directory as this script')

				exit(1)
		with open(token_path, 'wb') as token:
			pickle.dump(cred, token)
	return  build('drive', 'v3', credentials=cred)
		
def parseargs():
	parser = argparse.ArgumentParser(description='given a list of files, backs them up into my google drive')
	parser.add_argument('-v', '--verbose', dest='debug', action='store_true', help='extra debug information')
	parser.add_argument('-d', '--directory', dest='google_path', action='store', help='name of directory that file will be stored at')
	parser.add_argument('file_names', metavar='FILE_PATH', nargs='+', help='path of file(s) to be backed up')
	return parser.parse_args()


if __name__ == "__main__":
	results=parseargs()
	path = None
	files = results.file_names
	path = results.google_path
	# get rid of google warning messages
	logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
	if results.debug:
		logging.basicConfig(level=logging.DEBUG)
		logging.debug('debug is active')
	service = authenticate()
	# loop through every file specified
	for file in files:
		add_file(file, path, service)
	
	

