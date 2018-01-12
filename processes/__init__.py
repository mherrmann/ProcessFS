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
			pids = self._get_children(path)
		else:
			pids = self._get_processes_cached()
		return [str(pid) for pid in pids]
	def resolve(self, path):
		result = self.scheme
		if path:
			result += str(_path_to_pid(path))
		return result
	def is_dir(self, path):
		return not path or bool(self._get_children(path))
	def delete(self, path):
		_call_on_process(path, 'terminate')
	def get_name(self, path):
		pid = _path_to_pid(path)
		try:
			return self._get_processes_cached()[pid]['name']
		except KeyError:
			return _call_on_process(path, 'name')
	def _get_children(self, path):
		if path:
			pid = _path_to_pid(path)
			all_processes = self._get_processes_cached()
			return all_processes.get(pid, {}).get('children', [])
		return list(self._get_processes_cached())
	def _get_processes_cached(self):
		return query(self.scheme, '_get_processes')
	def _get_processes(self, path):
		assert not path, "%r != ''" % path
		process_list = list(process_iter(attrs=('pid', 'ppid', 'name')))
		result = {
			p.pid: {
				'name': p.name(),
				'children': []
			}
			for p in process_list
		}
		for p in process_list:
			try:
				result[p.ppid()]['children'].append(p.pid)
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