from fman import DirectoryPaneCommand
from fman.fs import FileSystem, Column, query
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
			pid_str = str(_path_to_pid(path))
			def get_children():
				self._get_processes()
				try:
					return self.cache.get(pid_str, 'children')
				except KeyError:
					raise _filenotfounderror(path) from None
			return self.cache.query(pid_str, 'children', get_children)
		return self._get_processes()
	def resolve(self, path):
		result = self.scheme
		if path:
			result += str(_path_to_pid(path))
		return result
	def is_dir(self, path):
		return not path or bool(self.iterdir(path))
	def delete(self, path):
		_call_on_process(path, 'terminate')
	def get_name(self, path):
		get_name = lambda: _call_on_process(path, 'name')
		return self.cache.query(path, 'name', get_name)
	def _get_processes(self):
		def load_processes():
			process_infos = self._load_process_infos()
			for pid_str, attrs in process_infos.items():
				for attr, value in attrs.items():
					self.cache.put(pid_str, attr, value)
			return list(process_infos)
		return self.cache.query('', 'iterdir', load_processes)
	def _load_process_infos(self):
		result = {}
		process_list = list(process_iter(attrs=('pid', 'ppid', 'name')))
		for p in process_list:
			result[str(p.pid)] = {
				'name': p.name(),
				'children': []
			}
		for p in process_list:
			try:
				ppid = p.ppid()
			except ProcessLookupError:
				# Process has died since we queried the list of processes.
				continue
			try:
				result[str(ppid)]['children'].append(str(p.pid))
			except KeyError:
				continue
		return result

class ProcessName(Column):

	display_name = 'Name'

	def get_str(self, url):
		return query(url, 'get_name')

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
		raise _filenotfounderror(path) from None

def _path_to_pid(path):
	try:
		return int(path.split('/')[-1])
	except ValueError:
		raise _filenotfounderror(path) from None

def _get_path(url):
	scheme, path = splitscheme(url)
	if scheme != 'process://':
		raise ValueError('Unsupported URL: %r' % url)
	return path

def _filenotfounderror(path):
	return FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT), 'process://' + path)