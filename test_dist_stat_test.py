import pytest

import dist_stat_test

import subprocess

from unittest.mock import patch
from unittest.mock import Mock

import pathlib

python = "/usr/bin/python3"

'''
NOTE
As we have no way in the program of stopping execution to test individual components
we use exceptions to stop execution between shell calls in the script
This allows for testing individual components
'''

import types
seen_call_args = []
stop_after_num_calls = 1
return_codes = [0]
def mock_stdout_decode(): pass
def mock_stderr_decode(): pass
class Mock_Exception(Exception): pass
def mock_subprocess_run(*args, **kwargs):
	'''
	This function is used to mock subprocess.run in dist_stat_test
	it will accept n calls before throwing an exception
	The exception is used to terminate execution of dist_stat_test.main()
	The exception thrown is Mock_Exception, so as to ensure no spurious exceptions are
	thrown
	This function accepts the args and kwargs passed to subprocess.run in dist_stat_test.main()
	But depends on other external variables:
	seen_call_args; which stores the arguments passed to the mock function
	stop_after_num_calls; which indicates how many calls to observe before throwing the mock exception
	return_codes; a list of values to use as return codes from mock shell calls
	mock_stdout_decode; mocks the function call: res.stdout.decode()
	mock_stderr_decode; mocks the function call: res.stderr.decode()
	'''
	seen_call_args.append(args)
	
	#check to see if we want to stop execution by throwing Mock_Exception
	call_index = len(seen_call_args)
	if call_index == (stop_after_num_calls+1):
		raise Mock_Exception()
	
	#otherwise return a namespace object to mimic a return object from subprocess.run
	#but whose return code is set from `return_codes`
	res = types.SimpleNamespace()
	res.returncode = return_codes[call_index-1]

	res.stdout = types.SimpleNamespace()
	res.stdout.decode = mock_stdout_decode
	
	res.stderr = types.SimpleNamespace()
	res.stderr.decode = mock_stderr_decode
	
	return res
	
@pytest.fixture
def setup_mock_subprocess_run():
	global seen_call_args
	seen_call_args = []
	
	global stop_after_num_calls
	stop_after_num_calls = None
	
	global return_codes
	return_codes = []
	
class Test_dist_stat_test:
	'''
	NOTE
	As sys.exit is called inside the script, we need to capture that event for testing
	thus the construction:

	```
	with pytest.raises(SystemExit) as pytest_wrapped_e:
	```

	see:
	https://medium.com/python-pandemonium/testing-sys-exit-with-pytest-10c6e5f7726f
	'''
	
	'''
	NOTE
	since we output to stdout and stderr, we need to capture that output and test against
	so we use the fixture capsys
	
	see:
	https://docs.pytest.org/en/6.2.x/capture.html#accessing-captured-output-from-a-test-function
	'''
	def test_nvdimm_check(self, capsys):
		dist_stat_test.DISK = "pmem"
		
		with pytest.raises(SystemExit) as pytest_wrapped_e:
			dist_stat_test.main()
	
		assert pytest_wrapped_e.type == SystemExit
		assert dist_stat_test.STATUS == 0
		assert pytest_wrapped_e.value.code == dist_stat_test.STATUS
		
		captured_stdout = capsys.readouterr().out
		captured_stderr = capsys.readouterr().err
		
		assert "NVDIMM" in captured_stdout
	
	'''
	NOTE
	Here we found that stderr messages were not being properly captured by capsys
	so instead check_return_code() was mocked and its arguments and calls were inspected directly
	'''
	def test_proc_partitions_check_ok(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		Check /proc/partitions, exit with fail if disk isn't found
		
		returned without issue
		so no output or errors, and STATUS should be 0
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 1

		global return_codes
		return_codes = [0]
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with pytest.raises(Mock_Exception) as pytest_wrapped_e:
					dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
				
				assert mock_check_return.call_count == 1
								
				#get the arguments for the first call to `check_return_code()`
				return_code = mock_check_return.call_args_list[0][0][0]
				check_return_code_message = mock_check_return.call_args_list[0][0][1]
								
				assert return_code == 0
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_proc_partitions_check_error(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		Check /proc/partitions, exit with fail if disk isn't found
		
		returned with error
		should see an error message, and STATUS is 1
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 1

		global return_codes
		return_codes = [1]
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with pytest.raises(Mock_Exception) as pytest_wrapped_e:
					dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 1
				
				#get the arguments for the first call to `check_return_code()`
				return_code = mock_check_return.call_args_list[0][0][0]
				check_return_code_message = mock_check_return.call_args_list[0][0][1]
								
				assert return_code == 1
				assert "not found in /proc/partitions" in check_return_code_message
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_proc_diskstats_check_ok(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Next, check /proc/diskstats
		
		returns without error
		should see return code 0, and no error messages
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 2

		global return_codes
		return_codes = [0, 0]
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with pytest.raises(Mock_Exception) as pytest_wrapped_e:
					dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 2
				
				#get the arguments for the last call to `check_return_code()`
				return_code = mock_check_return.call_args[0][0]
				check_return_code_message = mock_check_return.call_args[0][1]
								
				assert return_code == 0
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_proc_diskstats_check_error(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Next, check /proc/diskstats
		
		return with an error
		should see return code 1, and an error message
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 2

		global return_codes
		return_codes = [0, 1]
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with pytest.raises(Mock_Exception) as pytest_wrapped_e:
					dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 2
				
				#get the arguments for the last call to `check_return_code()`
				return_code = mock_check_return.call_args[0][0]
				check_return_code_message = mock_check_return.call_args[0][1]
								
				assert return_code == 1
				assert "not found in /proc/diskstats" in check_return_code_message
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_sys_block_check_ok(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Verify the disk shows up in /sys/block/
		
		return without error
		should see return code 0, and no error message
		
		Note for this test execution continues until the block marked:
		#Get some baseline stats for use later
		and so we get extra calls to check_return_code()
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 3

		global return_codes
		return_codes = [0, 0, 0]
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with pytest.raises(Mock_Exception) as pytest_wrapped_e:
					dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 4
				
				#get the arguments for next to the last call, since this executes more than we want for this test
				return_code = mock_check_return.call_args_list[len(mock_check_return.call_args_list)-2][0][0]
				check_return_code_message = mock_check_return.call_args_list[len(mock_check_return.call_args_list)-2][0][1]
								
				assert return_code == 0
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_sys_block_check_error(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Verify the disk shows up in /sys/block/
		
		return without error
		should see return code 1, and should have error message
		
		Note for this test execution continues until the block marked:
		#Get some baseline stats for use later
		and so we get extra calls to check_return_code()
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 3

		global return_codes
		return_codes = [0, 0, 1]
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with pytest.raises(Mock_Exception) as pytest_wrapped_e:
					dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 4
				
				#get the arguments for next to the last call, since this executes more than we want for this test
				return_code = mock_check_return.call_args_list[len(mock_check_return.call_args_list)-2][0][0]
				check_return_code_message = mock_check_return.call_args_list[len(mock_check_return.call_args_list)-2][0][1]
								
				assert return_code == 1
				assert "not found in /sys/block" in check_return_code_message
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_stats_in_sys_block_exists_false_stat_0(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Verify there are stats in /sys/block/$DISK/stat
		
		here we test this branch:
		if not ( disk_stat.exists() and (disk_stat.stat().st_size > 0) ):
		
		so we mock pathlib.Path.exists() and pathlib.Path.stat()
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 3

		global return_codes
		return_codes = [0, 0, 0]
		
		def mock_exists(*args, **kwargs): return False
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 0
			return res
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with pytest.raises(Mock_Exception) as pytest_wrapped_e:
							dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 4
				
				#get the arguments for the last call to check_return_code()
				return_code = mock_check_return.call_args[0][0]
				check_return_code_message = mock_check_return.call_args[0][1]
								
				assert return_code == 1
				assert "stat is either empty or nonexistant in" in check_return_code_message
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_stats_in_sys_block_exists_true_stat_0(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Verify there are stats in /sys/block/$DISK/stat
		
		here we test this branch:
		if not ( disk_stat.exists() and (disk_stat.stat().st_size > 0) ):
		
		so we mock pathlib.Path.exists() and pathlib.Path.stat()
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 3

		global return_codes
		return_codes = [0, 0, 0]
		
		def mock_exists(*args, **kwargs): return True
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 0
			return res
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with pytest.raises(Mock_Exception) as pytest_wrapped_e:
							dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 4
				
				#get the arguments for the last call to check_return_code()
				return_code = mock_check_return.call_args[0][0]
				check_return_code_message = mock_check_return.call_args[0][1]
								
				assert return_code == 1
				assert "stat is either empty or nonexistant in" in check_return_code_message
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_stats_in_sys_block_exists_false_stat_1(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Verify there are stats in /sys/block/$DISK/stat
		
		here we test this branch:
		if not ( disk_stat.exists() and (disk_stat.stat().st_size > 0) ):
		
		so we mock pathlib.Path.exists() and pathlib.Path.stat()
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 3

		global return_codes
		return_codes = [0, 0, 0]
		
		def mock_exists(*args, **kwargs): return False
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 1
			return res
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with pytest.raises(Mock_Exception) as pytest_wrapped_e:
							dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				assert mock_check_return.call_count == 4
				
				#get the arguments for the last call to check_return_code()
				return_code = mock_check_return.call_args[0][0]
				check_return_code_message = mock_check_return.call_args[0][1]
								
				assert return_code == 1
				assert "stat is either empty or nonexistant in" in check_return_code_message
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_stats_in_sys_block_exists_true_stat_1(self, capsys, setup_mock_subprocess_run):
		'''
		testing call:
		#Verify there are stats in /sys/block/$DISK/stat
		
		here we test this branch:
		if not ( disk_stat.exists() and (disk_stat.stat().st_size > 0) ):
		
		so we mock pathlib.Path.exists() and pathlib.Path.stat()
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 3

		global return_codes
		return_codes = [0, 0, 0]
		
		def mock_exists(*args, **kwargs): return True
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 1
			return res
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with pytest.raises(Mock_Exception) as pytest_wrapped_e:
							dist_stat_test.main()
					
				assert pytest_wrapped_e.type == Mock_Exception
					
				#here we have one less call to check_return_code() than previous tests as there is no call in the path:
				#if not ( disk_stat.exists() and (disk_stat.stat().st_size > 0) ):
				#	check_return_code(1, f"stat is either empty or nonexistant in /sys/block/{DISK}/")
				assert mock_check_return.call_count == 3
				
				#get the arguments for the last call to check_return_code()
				return_code = mock_check_return.call_args[0][0]
				check_return_code_message = mock_check_return.call_args[0][1]
								
				assert return_code == 0
							
				captured_stdout = capsys.readouterr().out
				
				assert len(captured_stdout) == 0
				
	def test_hadparm_failed_error(self, capsys, setup_mock_subprocess_run):
		'''
		testing branch:
		#giving up, as the test is compromised
		
		here we test if hdparm had failed; perhaps due to a permission issue
		this causes the script to fail and exit() with a non-zero return code
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 6

		global return_codes
		return_codes = [0, 0, 0, 0, 0, 1]
		
		def mock_exists(*args, **kwargs): return True
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 1
			return res
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with pytest.raises(SystemExit) as pytest_wrapped_e:
							dist_stat_test.main()
	
						assert pytest_wrapped_e.type == SystemExit
						
						assert mock_check_return.call_count == 4
						
						#get the arguments for the last call to check_return_code()
						return_code = mock_check_return.call_args[0][0]
						check_return_code_message = mock_check_return.call_args[0][1]
										
						assert return_code == 1
						assert "Error with hdparm" in check_return_code_message
									
						captured_stdout = capsys.readouterr().out
						
						assert len(captured_stdout) == 0
						
	def test_proc_stat_equal(self, capsys, setup_mock_subprocess_run):
		'''
		testing branch:
		if (PROC_STAT_BEGIN == PROC_STAT_END):
		
		where PROC_STAT_BEGIN equal PROC_STAT_END, producing an error
		and SYS_STAT_BEGIN does not equal SYS_STAT_END
		the script ends at `sys.exit(STATUS)` in this case, rather than an exception from subprocess.run
		and so STATUS is set manually, as it is not set in mock_check_return
		to avoid unexpected statements to stdout
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 8

		global return_codes
		return_codes = [0, 0, 0, 0, 0, 0, 0, 0]
		
		def mock_exists(*args, **kwargs): return True
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 1
			return res
		
		#here we setup a mock function for res.stdout.decode()
		#this mock function will return a sequence of values, one for each call in the script
		#see: https://stackoverflow.com/questions/24897145/python-mock-multiple-return-values
		stdout_decode = Mock()
		return_values = [
			#first call
			#PROC_STAT_BEGIN = res.stdout.decode()
			"PROC_STAT1",
			#second call
			#SYS_STAT_BEGIN = res.stdout.decode()
			"SYS_STAT1",
			#third call
			#PROC_STAT_END = res.stdout.decode()
			"PROC_STAT1",
			#fourth call
			#SYS_STAT_END = res.stdout.decode()
			"SYS_STAT2",
		]
		stdout_decode.side_effect = return_values
		
		global mock_stdout_decode
		mock_stdout_decode = stdout_decode
		
		def mock_sleep(*args, **kwargs): pass
		
		dist_stat_test.STATUS = 1
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with patch("dist_stat_test.time.sleep", new=mock_sleep): #mock time.sleep so we don't have to wait for each test
							with pytest.raises(SystemExit) as pytest_wrapped_e:
								dist_stat_test.main()
	
						assert pytest_wrapped_e.type == SystemExit
						
						assert mock_check_return.call_count == 5
						
						#get the arguments for the last call to check_return_code()
						return_code = mock_check_return.call_args[0][0]
						check_return_code_message = mock_check_return.call_args[0][1]
										
						assert return_code == 1
						assert "Stats in /proc/diskstats did not change" in check_return_code_message
									
						captured_stdout = capsys.readouterr().out
						
						assert len(captured_stdout) == 0
						
	def test_sys_stat_equal(self, capsys, setup_mock_subprocess_run):
		'''
		testing branch:
		if (SYS_STAT_BEGIN == SYS_STAT_END):
		
		where PROC_STAT_BEGIN does not equal PROC_STAT_END
		and SYS_STAT_BEGIN equals SYS_STAT_END, producing an error
		the script ends at `sys.exit(STATUS)` in this case, rather than an exception from subprocess.run
		and so STATUS is set manually, as it is not set in mock_check_return
		to avoid unexpected statements to stdout
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 8

		global return_codes
		return_codes = [0, 0, 0, 0, 0, 0, 0, 0]
		
		def mock_exists(*args, **kwargs): return True
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 1
			return res
		
		#here we setup a mock function for res.stdout.decode()
		#this mock function will return a sequence of values, one for each call in the script
		#see: https://stackoverflow.com/questions/24897145/python-mock-multiple-return-values
		stdout_decode = Mock()
		return_values = [
			#first call
			#PROC_STAT_BEGIN = res.stdout.decode()
			"PROC_STAT1",
			#second call
			#SYS_STAT_BEGIN = res.stdout.decode()
			"SYS_STAT1",
			#third call
			#PROC_STAT_END = res.stdout.decode()
			"PROC_STAT2",
			#fourth call
			#SYS_STAT_END = res.stdout.decode()
			"SYS_STAT1",
		]
		stdout_decode.side_effect = return_values
		
		global mock_stdout_decode
		mock_stdout_decode = stdout_decode
		
		def mock_sleep(*args, **kwargs): pass
		
		dist_stat_test.STATUS = 1
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with patch("dist_stat_test.time.sleep", new=mock_sleep): #mock time.sleep so we don't have to wait for each test
							with pytest.raises(SystemExit) as pytest_wrapped_e:
								dist_stat_test.main()
	
						assert pytest_wrapped_e.type == SystemExit
						
						assert mock_check_return.call_count == 5
						
						#get the arguments for the last call to check_return_code()
						return_code = mock_check_return.call_args[0][0]
						check_return_code_message = mock_check_return.call_args[0][1]
										
						assert return_code == 1
						assert "stat did not change" in check_return_code_message
									
						captured_stdout = capsys.readouterr().out
						
						assert len(captured_stdout) == 0
						
	def test_sys_stat_and_proc_stat_equal(self, capsys, setup_mock_subprocess_run):
		'''
		testing branch:
		if (PROC_STAT_BEGIN == PROC_STAT_END):
		if (SYS_STAT_BEGIN == SYS_STAT_END):
		
		where PROC_STAT_BEGIN equals PROC_STAT_END, producing an error
		and SYS_STAT_BEGIN equals SYS_STAT_END, producing an error
		the script ends at `sys.exit(STATUS)` in this case, rather than an exception from subprocess.run
		and so STATUS is set manually, as it is not set in mock_check_return
		to avoid unexpected statements to stdout
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 8

		global return_codes
		return_codes = [0, 0, 0, 0, 0, 0, 0, 0]
		
		def mock_exists(*args, **kwargs): return True
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 1
			return res
		
		#here we setup a mock function for res.stdout.decode()
		#this mock function will return a sequence of values, one for each call in the script
		#see: https://stackoverflow.com/questions/24897145/python-mock-multiple-return-values
		stdout_decode = Mock()
		return_values = [
			#first call
			#PROC_STAT_BEGIN = res.stdout.decode()
			"PROC_STAT1",
			#second call
			#SYS_STAT_BEGIN = res.stdout.decode()
			"SYS_STAT1",
			#third call
			#PROC_STAT_END = res.stdout.decode()
			"PROC_STAT1",
			#fourth call
			#SYS_STAT_END = res.stdout.decode()
			"SYS_STAT1",
		]
		stdout_decode.side_effect = return_values
		
		global mock_stdout_decode
		mock_stdout_decode = stdout_decode
		
		def mock_sleep(*args, **kwargs): pass
		
		dist_stat_test.STATUS = 1
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with patch("dist_stat_test.time.sleep", new=mock_sleep): #mock time.sleep so we don't have to wait for each test
							with pytest.raises(SystemExit) as pytest_wrapped_e:
								dist_stat_test.main()
	
						assert pytest_wrapped_e.type == SystemExit
						
						assert mock_check_return.call_count == 6
						
						#check the n-1 call to check_return_code, for the branch: `if (PROC_STAT_BEGIN == PROC_STAT_END):`
						return_code1 = mock_check_return.call_args_list[len(mock_check_return.call_args_list)-2][0][0]
						check_return_code_message1 = mock_check_return.call_args_list[len(mock_check_return.call_args_list)-2][0][1]
						
						assert return_code1 == 1
						assert "Stats in /proc/diskstats did not change" in check_return_code_message1
						
						#check the n call to check_return_code, for the branch: `if (SYS_STAT_BEGIN == SYS_STAT_END):`
						return_code2 = mock_check_return.call_args[0][0]
						check_return_code_message2 = mock_check_return.call_args[0][1]
						
						assert return_code2 == 1
						assert "stat did not change" in check_return_code_message2
							
						captured_stdout = capsys.readouterr().out
						
						assert len(captured_stdout) == 0
						
	def test_all_ok(self, capsys, setup_mock_subprocess_run):
		'''
		testing branch:
		if STATUS == 0:
		
		here we emulate as if all calls were successful
		
		the script ends at `sys.exit(STATUS)` in this case, rather than an exception from subprocess.run
		and so STATUS is set manually, as it is not set in mock_check_return
		to avoid unexpected statements to stdout
		'''
		dist_stat_test.DISK = "some test arg"

		global stop_after_num_calls
		stop_after_num_calls = 8

		global return_codes
		return_codes = [0, 0, 0, 0, 0, 0, 0, 0]
		
		def mock_exists(*args, **kwargs): return True
		def mock_stat(*args, **kwargs):
			res = types.SimpleNamespace()
			res.st_size = 1
			return res
		
		#here we setup a mock function for res.stdout.decode()
		#this mock function will return a sequence of values, one for each call in the script
		#see: https://stackoverflow.com/questions/24897145/python-mock-multiple-return-values
		stdout_decode = Mock()
		return_values = [
			#first call
			#PROC_STAT_BEGIN = res.stdout.decode()
			"PROC_STAT1",
			#second call
			#SYS_STAT_BEGIN = res.stdout.decode()
			"SYS_STAT1",
			#third call
			#PROC_STAT_END = res.stdout.decode()
			"PROC_STAT2",
			#fourth call
			#SYS_STAT_END = res.stdout.decode()
			"SYS_STAT2",
		]
		stdout_decode.side_effect = return_values
		
		global mock_stdout_decode
		mock_stdout_decode = stdout_decode
		
		def mock_sleep(*args, **kwargs): pass
		
		dist_stat_test.STATUS = 0
		
		with patch("dist_stat_test.subprocess.run", new=mock_subprocess_run) as mock_run:
			with patch("dist_stat_test.check_return_code") as mock_check_return:
				with patch.object(pathlib.Path, 'exists', mock_exists): #mock pathlib.Path.exists
					with patch.object(pathlib.Path, 'stat', mock_stat): #mock pathlib.Path.stat
						with patch("dist_stat_test.time.sleep", new=mock_sleep): #mock time.sleep so we don't have to wait for each test
							with pytest.raises(SystemExit) as pytest_wrapped_e:
								dist_stat_test.main()
	
						assert pytest_wrapped_e.type == SystemExit
							
						captured_stdout = capsys.readouterr().out
						
						assert len(captured_stdout) != 0
						
						assert "PASS" in captured_stdout
