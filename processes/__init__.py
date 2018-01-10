from fman import DirectoryPaneCommand
from fman.fs import FileSystem, Column
from fman.url import splitscheme
from os import strerror
from psutil import process_iter, Process, NoSuchProcess

import errno
import psutil

class ShowProcesses(DirectoryPaneCommand):
	def __call__(self):
		self.pane.set_path('process://')

class ProcessesFileSystem(FileSystem):

	scheme = 'process://'

	def get_default_columns(self, path):
		return 'ProcessName', 'PID'
	def iterdir(self, path):
		if path:
			children = _call_on_process(path, 'children')
			pids = [child.pid for child in children]
		else:
			pids = psutil.pids()
		return [str(pid) for pid in pids]
	def resolve(self, path):
		if not path:
			# Showing all processes:
			return self.scheme
		pid = _path_to_pid(path)
		return self.scheme + str(pid)
	def is_dir(self, path):
		if not path:
			return True
		return bool(_call_on_process(path, 'children'))
	def delete(self, path):
		_call_on_process(path, 'terminate')

class ProcessName(Column):

	display_name = 'Name'

	def get_str(self, url):
		return _call_on_process(_get_path(url), 'name')

class PID(Column):
	def get_str(self, url):
		return str(self.get_sort_value(url))
	def get_sort_value(self, url, is_ascending=True):
		return _path_to_pid(_get_path(url))

def _call_on_process(path, method_name):
	pid = _path_to_pid(path)
	try:
		return getattr(Process(pid), method_name)()
	except NoSuchProcess:
		raise _filenotfounderror('proces://' + path)

def _path_to_pid(path):
	try:
		return int(path.split('/')[-1])
	except ValueError:
		raise _filenotfounderror(self.scheme + path)

def _get_path(url):
	scheme, path = splitscheme(url)
	if scheme != 'process://':
		raise ValueError('Unsupported URL: %r' % url)
	return path

def _filenotfounderror(url):
	return FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT), url)