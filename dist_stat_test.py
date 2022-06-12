'''
Simple script to gather some data about a disk to verify it's seen by the OS
and is properly represented.  Defaults to sda if not passed a disk at run time
'''
import argparse
import sys
import subprocess
from pathlib import Path
import time

DISK = "sda"
STATUS = 0

def check_return_code(return_code, message, *args):
	if return_code != 0:
		print(f"ERROR: retval {return_code} : {message}", file=sys.stderr)
		
		global STATUS
		if STATUS == 0:
			STATUS = return_code
		
		for item in args:
			print(f'output: {item}')
			
def main():
	nvdimm="pmem"
	if nvdimm in DISK:
		print(f"Disk {DISK} appears to be an NVDIMM, skipping")
		sys.exit(STATUS)
		
	#Check /proc/partitions, exit with fail if disk isn't found
	cmd = ["grep", "-w", "-q", DISK, "/proc/partitions"]
	res = subprocess.run(cmd, capture_output=True)
	
	check_return_code(res.returncode, f"Disk {DISK} not found in /proc/partitions")
	
	#Next, check /proc/diskstats
	cmd = ["grep", "-w", "-q", "-m", "1", DISK, "/proc/diskstats"]
	res = subprocess.run(cmd, capture_output=True)
	
	check_return_code(res.returncode, f"Disk {DISK} not found in /proc/diskstats")
	
	#Verify the disk shows up in /sys/block/
	cmd = ["ls", f'/sys/block/{DISK}']
	res = subprocess.run(cmd, capture_output=True)
	
	check_return_code(res.returncode, f"Disk {DISK} not found in /sys/block")
	
	#Verify there are stats in /sys/block/$DISK/stat
	disk_stat = Path(f"/sys/block/{DISK}/stat")
	if not ( disk_stat.exists() and (disk_stat.stat().st_size > 0) ):
		check_return_code(1, f"stat is either empty or nonexistant in /sys/block/{DISK}/")
	
	#Get some baseline stats for use later
	cmd = ["grep", "-w", "-m", "1", f'{DISK}', "/proc/diskstats"]
	res = subprocess.run(cmd, capture_output=True)

	PROC_STAT_BEGIN = res.stdout.decode()
	
	cmd = ["cat", f"/sys/block/{DISK}/stat"]
	res = subprocess.run(cmd, capture_output=True)

	SYS_STAT_BEGIN = res.stdout.decode()
	
	#Generate some disk activity using hdparm -t
	'''
	BUG
	in the shell script disk_stats_test.sh (https://code.launchpad.net/coding-samples) this command is used to attempt to generate disk
	activity:
	`hdparm -t "/dev/$DISK" 2&> /dev/null`
	However, if this is not run with the proper permissions the error message "/dev/sda: Permission denied" is not captured
	the script then goes on to compare outputs of PROC_STAT_BEGIN and SYS_STAT_BEGIN
	after the attempted hdparm command
	The test will *occasionally* produce an error, due to the failure of hdparm
	but will usually pass due to normal disk activity during the test
	
	The script has been changed from the source to address this eventuality
	'''
	cmd = ["hdparm", "-t", f'/dev/{DISK}']
	res = subprocess.run(cmd, capture_output=True)
	
	check_return_code(res.returncode, f"Error with hdparm: {res.stderr.decode()}")
	
	if res.returncode != 0:
		#giving up, as the test is compromised
		sys.exit(STATUS)
	
	#Sleep 5 to let the stats files catch up
	time.sleep(5)
	
	'''
	ERROR
	In the shell script disk_stats_test.sh (https://code.launchpad.net/coding-samples)
	this command is used to compare PROC_STAT_BEGIN and PROC_STAT_END:
	```[[ "$PROC_STAT_BEGIN" != "$PROC_STAT_END" ]]```
	
	it is then an error if the two are the same
	However, there is no such comparison for $SYS_STAT_BEGIN and $SYS_STAT_END
	even though there is error handling as if a comparison were expected
	This additional comparison is added here, even though it is absent in the original code
	'''

	#Make sure the stats have changed:
	cmd = ["grep", "-w", "-m", "1", f'{DISK}', "/proc/diskstats"]
	res = subprocess.run(cmd, capture_output=True)

	PROC_STAT_END = res.stdout.decode()
	
	cmd = ["cat", f"/sys/block/{DISK}/stat"]
	res = subprocess.run(cmd, capture_output=True)

	SYS_STAT_END = res.stdout.decode()
	
	if (PROC_STAT_BEGIN == PROC_STAT_END):
		check_return_code(1, "Stats in /proc/diskstats did not change", PROC_STAT_BEGIN, PROC_STAT_END)
		
	if (SYS_STAT_BEGIN == SYS_STAT_END):
		check_return_code(1, f"Stats in /sys/block/{DISK}/stat did not change", SYS_STAT_BEGIN, SYS_STAT_END)
	
	if STATUS == 0:
		print(f"PASS: Finished testing stats for {DISK}")
	
	sys.exit(STATUS)
	
if __name__ == "__main__":
	desc = "An implementation of `disk_stats_test.sh` from https://code.launchpad.net/coding-samples"
	parser = argparse.ArgumentParser(description=desc)

	#accept a single argument, which specifies which disk to test
	parser.add_argument('disk', type=str, nargs='?', help='The name of which disk to test; For example: `sda`')
	args = parser.parse_args()
	
	if not args.disk is None:
		DISK = str(args.disk)
		
	main()
