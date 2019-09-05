import os
import sys
import hashlib
import xxhash
import shutil
import glob
import re
import zipfile

NO_COPY = False
BIG_FILE = 2**26
walk_dir = "/home/mschramm/Documents/PhD"
box_dir = "/home/mschramm/box/DEM Fiberous Particles-PhD"

file_extensions = ('.liggghts', '.vtk','.restart','.bonds','.bond','.stl','.STL','forcechain')

#walk_dir = "/home/mschramm/Programs/Box_Sync/box_sync/test"
#box_dir = "/home/mschramm/Programs/Box_Sync/box_sync/box"

# Print iterations progress
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, bar_length=50):
	"""
	Call in a loop to create terminal progress bar
	@params:
	iteration   - Required  : current iteration (Int)
	total       - Required  : total iterations (Int)
	prefix      - Optional  : prefix string (Str)
	suffix      - Optional  : suffix string (Str)
	decimals    - Optional  : positive number of decimals in percent complete (Int)
	bar_length  - Optional  : character length of bar (Int)
	"""
	str_format = "{0:." + str(decimals) + "f}"
	percents = str_format.format(100 * (iteration / float(total)))
	filled_length = int(round(bar_length * iteration / float(total)))
	bar = '%' * filled_length + '-' * (bar_length - filled_length)

	sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix))

	if iteration == total:
		sys.stdout.write('\n')
	sys.stdout.flush()

def get_hash(filename, block_size=4096, hash_type='md5'):
    print('Getting hash for ' + filename)
    file_size = os.path.getsize(filename)
    if file_size > BIG_FILE:
        PRINT_STATUS = True
        count = 0
        max_count = file_size/block_size + 1
    else:
        PRINT_STATUS = False
    if hash_type == 'md5':
        hash = hashlib.md5()
    elif hash_type == 'xxh64':
        hash = xxhash.xxh64()
    else:
        print('hash type ' + hash_type + ' is not supported')
        print('using md5')
        hash = hashlib.md5()
    curDone = 0.0
    perStep = 5.0
    with open(filename, "rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                if PRINT_STATUS:
                    # if count <= max_count:
                    printProgressBar(max_count, max_count)
                break
            if PRINT_STATUS:
                count += 1
                perDone = 100.0*float(count)/float(max_count)
                if perDone > curDone:
                    curDone += perStep
                    printProgressBar(count, max_count)
            hash.update(data)
    return hash.hexdigest()


# def get_hash(filename, block_size=4096):
# 	print('Getting hash for ' + filename)
# 	file_size = os.path.getsize(filename)
# 	if file_size > BIG_FILE:
# 		PRINT_STATUS = True
# 		count = 0
# 		max_count = file_size/block_size + 1
# 	else:
# 		PRINT_STATUS = False
# 	hash = hashlib.md5()
# 	with open(filename, "rb") as f:
# 		while True:
# 			data = f.read(block_size)
# 			if not data:
# 				if PRINT_STATUS:
# 					if count <= max_count:
# 						printProgressBar(max_count, max_count)
# 				break
# 			if PRINT_STATUS:
# 				count += 1
# 				if count < max_count:
# 					printProgressBar(count, max_count)
# 			hash.update(data)
# 	return hash.hexdigest()

def get_box_path(box_dir,file_path):
	file_sep = file_path.split(os.sep)
	loc_path = os.path.join('', *file_sep[5:])
	box_path = os.path.join(box_dir, loc_path)
	return box_path

def get_last_hash(filename):
	if os.path.isfile(filename):
		with open(filename, 'rb') as f:
			for line in f:
				last = line
				last = last.split(',')
				if len(last) > 1:
					last_hash_file = last[0]
					last_hash_value = last[1]

		print("Last line in hash == " + last_hash_file)
		return last_hash_file, last_hash_value.rstrip('\r\n')
	else:
		return "NaN", "NaN"

def copy2box(src, dst):
	print("Copying " + src)
	print("to " + dst)
	try:
		if not NO_COPY:
			shutil.copy2(src,dst)
	except OSError as e:
		if e.errno == 22:
			print("Cannot copy metadata... Just coping file")
			if not NO_COPY:
				shutil.copyfile(src,dst)
		else:
			raise(e)
	except IOError as e:
		if e.errno == 2:
			print("Destination does not exsist, creating destination and trying again...")
			head,tail = os.path.split(dst)
			os.makedirs(head)
			copy2box(src,dst)
			return
		else:
			raise(e)
	print("Done!\n")

def in_hash_file(file_path):
	with open("box_hash.txt", 'rb') as f:
		for line in f:
			last = line
			last = last.split(',')
			if file_path == last[0]:
				return True, last[1].rstrip('\r\n')
	return False, "NaN"

def has_updated(file_path, old_hash):
	if len(old_hash) > 20:
		new_hash = get_hash(file_path,hash_type='md5')
		converted_hash = get_hash(file_path,hash_type='xxh64')
		needsConverting = True
	else:
		needsConverting = False
		new_hash = get_hash(file_path,hash_type='xxh64')
	if new_hash == old_hash:
		if needsConverting:
			print("Updating hash to xxh64")
			return False, converted_hash
		else:
			return False, new_hash
	else:
		return True, new_hash

def doCompression(root, allfiles, ext):
	str_example = allfiles[0]
	m = re.search("\d", str_example)
	if m:
		short_str = str_example[0:m.start()]
		file_comp = os.path.join(root,short_str + ext + ".zip")
		if not os.path.isfile(file_comp):
			my_zip = zipfile.ZipFile(file_comp,'w', allowZip64=True)
			print('zip file does not exist, creating...')
			numFiles = len(allfiles)
			its = 0
			for _file in allfiles:
				its += 1
				fullfile = os.path.join(root,_file)
				my_zip.write(fullfile, compress_type=zipfile.ZIP_DEFLATED)
				printProgressBar(its, numFiles)
			my_zip.close()
	

def do_update():

	last_hash_file, last_hash_value = get_last_hash('new_box_hash.txt')
	if (last_hash_file == "NaN"):
		new_hash_file = open("new_box_hash.txt", "w+")
		find_last_hash = False
	else:
		new_hash_file = open("new_box_hash.txt", "a+")
		find_last_hash = True

	try:
		for root, subdirs, files in os.walk(walk_dir):
			print('')
			print('Now looking in %s'%root)
			for exten in file_extensions:
				num_files = len(glob.glob1(root, ("*" + exten)))
				print('Number of files with the ending ' + exten + ' = ' + str(num_files))
				if num_files > 3:
					doCompression(root, glob.glob1(root,("*" + exten)),exten)
			for filename in files:
				file_path = os.path.join(root, filename)
				if find_last_hash:
					if file_path == last_hash_file:
						find_last_hash = False
						continue
					else:
						continue
				if filename.lower().endswith(file_extensions):
					if not (filename == 'in.liggghts'):
						continue
				file_not_new, old_hash = in_hash_file(file_path)
				if file_not_new:
					needs_updating, new_hash = has_updated(file_path, old_hash)
					if needs_updating:
						print('Needs Updating')
						box_path = get_box_path(box_dir, file_path)
						new_string = file_path + "," + new_hash
						copy2box(file_path, box_path)
						new_hash_file.write(new_string+"\n")
					else:
						new_string = file_path + "," + new_hash
						new_hash_file.write(new_string+"\n")
				else:
					print('New File!')
					hash_value = get_hash(file_path,hash_type='xxh64')
					box_path = get_box_path(box_dir, file_path)
					new_string = file_path + "," + hash_value
					copy2box(file_path, box_path)
					new_hash_file.write(new_string+"\n")
					
		print('DONE')
		new_hash_file.write("EverythingIsFinished,1\n")
		new_hash_file.close()
		shutil.move("new_box_hash.txt","box_hash.txt")
	except KeyboardInterrupt:
		print("")
		print("Keyboard Interrupt Detected")
		print("Stopping Gracefully")
		new_hash_file.close()

def do_fresh(last_hash_file):
	if (last_hash_file == "NaN"):
		hash_file = open("box_hash.txt", "w+")
		find_last_hash = False
	else:
		hash_file = open("box_hash.txt", "a+")
		find_last_hash = True

	try:
		for root, subdirs, files in os.walk(walk_dir):
			for filename in files:
				file_path = os.path.join(root, filename)
				if find_last_hash:
					if file_path == last_hash_file:
						find_last_hash = False
						continue
					else:
						continue
				if filename.lower().endswith(('.liggghts', '.vtk','.restart','.bonds','.bond','.stl')):
					for exten in file_extensions:
						num_files = len(glob.glob1(file_path, exten))
						print('Number of files with the ending ' + exten + ' = ' + num_files)
					if not (filename == 'in.liggghts'):
						continue
				hash_value = get_hash(file_path,hash_type='xxh64')
				box_path = get_box_path(box_dir, file_path)
				new_string = file_path + "," + hash_value
				copy2box(file_path, box_path)
				hash_file.write(new_string+"\n")

		print('DONE')
		hash_file.write("EverythingIsFinished,1\n")
		hash_file.close()
	except KeyboardInterrupt:
		print("")
		print("Keyboard Interrupt Detected")
		print("Stopping Gracefully")
		hash_file.close()

def main():
	last_hash_file, last_hash_value = get_last_hash("box_hash.txt")
	if last_hash_value == '1':
		print("Updating")
		do_update()
	else:
		print("Syncing for first time")
		do_fresh(last_hash_file)

if __name__ == '__main__':
	main()
