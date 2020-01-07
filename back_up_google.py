"""
backs up input file(s) to google drive account
-dir flag creates a path for files to live 
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
logger = logging.getLogger('gdrive')
def full_path(name, parent_id):
	"""returns the full path of file/directory given a id"""
	# if parent is not none, get the next parent name
	path = ''
	if parent_id:
		res = service.files().get(fileId=parent_id, fields="parents,name").execute()
		path = full_path(res['name'], res.get('parents', (None,))[0])
	return os.path.join(path, name)

def list_files(query_param, query_fields):
	"""returns a list of files fields"""
	results = []
	page_token = None
	while True:
		response = service.files().list(q=query_param,spaces='drive',fields=query_fields,pageToken=page_token).execute()
		results += response.get('files', [])
		page_token = response.get('nextPageToken')
		if not page_token:
			break
	return results

def list_dir(dir_name, service, file_only=False, dir_only=False):
	"""lists all the files/dirs in a google drive directory"""
	if not file_only or not dir_only:
		# defining query
		dir_id = get_folder_id(dir_name, service)
		query_str = "'{}' in parents".format(dir_id) 
		if file_only:
			query_str = "mimeType != 'application/vnd.google-apps.folder' and '{}' in parents".format(dir_id)
		elif dir_only:
			query_str = "mimeType = 'application/vnd.google-apps.folder' and '{}' in parents".format(dir_id)		
		results = list_files(query_str, "files(name,mimeType)")
		if len(results) < 1:
			print("No results found in directory \"{}\"".format(dir_name))
		else:
			# seperating dirs and files for readability
			dirs = []
			files = []
			for r in results:
				if r['mimeType'] == 'application/vnd.google-apps.folder':
					dirs.append(r['name'])
				else:
					files.append(r['name'])
			if len(dirs) > 0:
				print("Directoires found:")
				for d in dirs:
					print(d)
				print()
			if len(files) > 0:
				print('Files found:')
				for f in files:
					print(f)
			
	else:
		logger.error('please only select either file_only or dir_only, not both')

def prompt_user(results, dir_file_name):
	"""
	prompts user to select a certian file or dir if multiple results are found
	function also creates full path to those file/dir
	"""
	result_to_pick = 0 
	parent_name = {}
	for f in range(len(results)):
		name = full_path(results[f]['name'] ,results[f].get('parents')[0])
		# used to elimate results if a full path is specified
		if dir_file_name in name:
			parent_name[f] = name
		else:
			logger.debug('full path "{}" doesn\'t match dir "{}", skipping'.format(name, dir))
			del results[f]
	# if results where filter based on full path, skip user prompt	
	if len(parent_name.keys()) > 1:
		print('There seems to be more than one directory with that name, please specify (by typing the number next to the parent directory name) which directory to use')
		count = 0
		for name in [f['name'] for f in results]:
			print('{}. {}'.format(count, parent_name[count]))
			count += 1
		input_recived = False
		# gettng user input
		while not input_recived:
			num = input()
			try:
				num = int(num)
				if num < len(results):
					result_to_pick = num
					input_recived = True
				else:
					print('The number specified "{}" is greater than amount of options'.format(num))
			except ValueError:
				print('unable to understand "{}"'.format(num))
	return result_to_pick

def get_file_id(dir_id, file_name, service):
	"""
	returns the file id of a file in a certian directory
	retunrs none if file not found
	"""
	page_token = None
	results = list_files("'{}' in parents and mimeType != 'application/vnd.google-apps.folder'".format(dir_id), "files(name, id)")
	for f in results:
		if f['name'] == file_name:
			file_id = f['id']
			logger.debug('file was found, returning file id, "{}"'.format(file_id))
			return file_id
	logger.debug('file was not found, to create new file')
	return None

def get_folder_id(dir, service):
	"""
	gets the id of the folder specified in the dir variable
	will prompt user for input if multiple results are specified
	"""
	logger.debug('getting folder id for folder to place file')
	page_token = None
	result_to_pick = 0
	base_dir = None
	if '/' in dir:
		base_dir = os.path.basename(dir)
		logger.debug('found "/" in directory, will search based on name "{}"'.format(base_dir))
	# finding all directories with the name in either dir or base_dir
	results = list_files("mimeType='application/vnd.google-apps.folder' and name='{}'".format(dir if not base_dir else base_dir), "files(parents, name, id)")
	
	# if more than one result found prompt user to see which directory to use
	folder_id = None
	if len(results) > 1:
		logger.debug('more than one results where found, attempting to limit results')
		result_to_pick = prompt_user(results, dir if not base_dir else base_dir)
	elif len(results) < 1:
		logger.error('dir "{}" was not found in google drive account'.format(dir))
		exit(1)
	folder_id  = results[result_to_pick]['id'] 
	logger.debug('folder_directory picked was "{}"'.format(results[result_to_pick]['name']))
	logger.debug('folder_id found was "{}"'.format(folder_id))
	return folder_id 


def add_file(file, dir, service):
	"""
	adds a file to google drive mydrive
	dir is directory where file should be placed
	"""
	if os.path.isfile(file):
		folder_id = None
		if dir is not None:
			folder_id = get_folder_id(dir, service)
		# check if file already exists
		file_name = os.path.basename(file)
		# root is used if directory is not specified
		file_id = get_file_id(folder_id if folder_id else 'root', file_name, service) 
		media = MediaFileUpload(file)
		# if file was not found, create it
		if not file_id:
			file_metadata = {'name': file_name}
			# specify folder
			if folder_id:
				file_metadata['parents'] = [folder_id]
			file_id = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
			print('file "{}" was created and uploaded under directory "{}"'.format(file, dir if dir else 'MyDrive'))
		else:
			service.files().update(fileId=file_id, media_body=media).execute()
			print('file "{}" under directory "{}" was updated'.format(file, dir if dir else 'MyDrive'))
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
		logger.debug('token file was found')
		with open(token_path, 'rb') as token:
           		cred = pickle.load(token)
	if not cred or not cred.valid:
		if cred and cred.expired and cred.refresh_token:
			logger.debug('cred is not valid')
			cred.refresh(Request())
		else:
			logger.debug('no cred found, asking for permission')
			if os.path.isfile(os.path.join(file_dir, 'credentials.json')):
				flow = InstalledAppFlow.from_client_secrets_file(os.path.join(file_dir, 'credentials.json'), SCOPES)
				cred = flow.run_local_server(port=0)
			else:
				logger.error('couldn\'t find "credentials.json", this is needed in order to authenticate users google drive. Please obtain this file and place it in the same directory as this script')

				exit(1)
		with open(token_path, 'wb') as token:
			pickle.dump(cred, token)
	return  build('drive', 'v3', credentials=cred)
		
def parseargs():
	parser = argparse.ArgumentParser(description='given a list of files, backs them up into my google drive')
	parser.add_argument('-v', '--verbose', dest='debug', action='store_true', help='extra debug information')
	parser.add_argument('-d', '--directory', dest='google_path_or_name', action='store', help='name of or path to directory in user\'s google account that the file will be stored at')
	parser.add_argument('-l' '--list', dest='google_path_or_name_list', action='store', help='list files in for a name of or path to directory in user\'s google account')
	parser.add_argument('--fileonly', dest='fileonly', action='store_true', help='lists only files, to be used with -l/--list command')
	parser.add_argument('--directoryonly', dest='dironly', action='store_true', help='lists only directoies, to be used with -l/--list command')
	parser.add_argument('file_names', metavar='FILE_PATH', nargs='*', help='path of file(s) to be backed up')
	parsed_args = parser.parse_args()
	# need to specify either file_names or list command
	if not parsed_args.google_path_or_name_list and not parsed_args.file_names:
		parser.error('must define either files to back up or directory to list using -l, see --help for more info')
	return parsed_args



if __name__ == "__main__":
	results=parseargs()
	files = results.file_names
	path = results.google_path_or_name
	# get rid of google warning messages
	logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
	if results.debug:
		logging.basicConfig(level=logging.DEBUG)
		logger.debug('debug is active')
	service = authenticate()
	if files:
		# loop through every file specified
		for file in files:
			add_file(file, path, service)
	if results.google_path_or_name_list:
		list_dir(results.google_path_or_name_list, service, file_only=results.fileonly, dir_only=results.dironly)
	
	
	

