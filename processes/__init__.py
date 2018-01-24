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
		return 'Name', 'PID'
	def name(self, path):
		load_name = lambda: _call_on_process(path, 'name')
		return self.cache.query(path, 'name', load_name)
	def iterdir(self, path):
		if path:
			pid = _path_to_pid(path)
			def get_children():
				return [str(c.pid) for c in Process(pid).children()]
			return self.cache.query(str(pid), 'children', get_children)
		else:
			process_infos = self._load_process_infos()
			for pid_str, attrs in process_infos.items():
				for attr, value in attrs.items():
					self.cache.put(pid_str, attr, value)
			return list(process_infos)
	def resolve(self, path):
		result = self.scheme
		if path:
			result += str(_path_to_pid(path))
		return result
	def is_dir(self, path):
		return not path or bool(self.iterdir(path))
	def delete(self, path):
		_call_on_process(path, 'terminate')
	def _load_process_infos(self):
		result = {}
		for p in process_iter(attrs=('pid', 'ppid', 'name')):
			info = dict(p.info)
			info['children'] = []
			pid_str = str(info.pop('pid'))
			result[pid_str] = info
		for pid_str, info in result.items():
			try:
				result[str(info['ppid'])]['children'].append(pid_str)
			except KeyError:
				continue
		return result

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