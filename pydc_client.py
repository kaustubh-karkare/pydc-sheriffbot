from connection import Connection, ConnectionError
import base64, bz2, copy, ctypes, itertools, math, os, platform, random, re, socket, sys, time, tiger, threading, traceback, xml.dom.minidom

# sys.stderr = open("error.txt","w")
# Nicknames cannot contain spaces

class pydc_client():
	help = """pyDC Client Class Documentation : Written by Kaustubh Karkare.
		The DC Client Class uses the Connection Class to interact with the DC Server.
		You may use the following functions to setup and manage connections with the hub and perform simple operations:
			configure(<dictionary>): Configures the client. The argument must be a dictionary with at least the following keys: "name" (name of the client),"nick" (nickname of the user),"host" (address of the hub to connect to), with valid corresponding string values.
				Besides the aforementioned, there are a larger number of other configuration options also available.
			save(): Saves configuration and certain other variables to files, so that they can be loaded later.
			load(): Loads configuration and certain other variables to files, so that they need not be manually configured again.
			link(<dict>): Takes a dictionary argument with values being functions to which specific data is to be send. Keys other than the following are ignored: "mainchat","debug","pm".
				In case of "mainchat" and "debug", the function need to take 1 argument, which is the data to be sent. If "debug" is not specified, the corresponding data is ignored. If "mainchat" is not specified, it defaults to sys.stdout.
				In case of "pm", you shall need to provide a function that takes 2 arguments, the first being the nickname of the other user, and second being the actual data that he/she sent. If "pm" is not specified, all data is sent to "mainchat".
			step(<function>): Sets a function that is to be periodically called (time interval can be specified in the confuration) during an active connection to the hub.
			connect(): After configuration is complete, this actually connects to the hub, with the details provided.
			disconnect(): If the connection with the hub is still active, disconnects it, and terminates all spawned connections.
			mc_send(<data>): Write <data> to Main Chat for everyone to see.
			pm_send(<nick>,<data>): Send Private Message <data> to user <nick>.
			search(<pattern>,<result>,<options>): Sends a message to the hub to be forwarded to all other clients to search for the <pattern> in their filelist.
				The <result> argument is a function to be called (that takes 1 list argument) for each search result recieved.
					The 1st item of the list passed to the function as an argument is either "File" or "Directory", whichever is appropriate.
					If the result is a "File", the remaining arguments contain the Nick, File Name, File Size, Free Slots, Total Slots, TTH.
					If the result is a "Directory", the remaining arguments contain the Nick, Directory Name, Free Slots, Total Slots, Hub Name.
				The <options> argument is optional, and if present is a dictionary containing the following keys and correspondingly appropriate values: "limit" = "min" or "max", "size" (int), "type" (filetype).
				Filetypes are specified using any one of the following strings: "any", "audio", "compressed", "document", "executable", "image", "video", "folder", "tth".
			download(<tth>):
		The groups feature allows users to classify other users (based on their nicknames) info groups, such that they can share a different filelist with each group, thus having a greater control over whom they share their files with. In order that there be no ambiguity regarding which filelist to download given a nickname, each nickname is allowed to be part of only one group. All those nicknames that have not been explicitly assigned groups are considered part of a default group (general). The following functions are used for group management:
			group_create(<groupname>) : Creates a new group by given name.
			group_rename(<old-groupname>,<new-groupname>) : Renames a group.
			group_delete(<group-name>) : Deletes a existing group by given name.
			group_add(<groupname>,<nickname>) : Adds specified nickname to specified group.
			group_remove(<groupname>,<nickname>) : Remove specified nickname from specified group.
			group_check(<groupname>,<nickname>) : Check if specified nickname belongs to specified group.
			group_find(<nickname>) : Returns which group the specified nickname belongs to.
		The following functions are used to manage filelists, in addition to those mentioned above. Note that the <group> argument is optional, and may be omitted to use the default (general) group.
			filelist_get(<nick>): Download the filelist of the specified user.
			filelist_add(<dir/file-path>,<group>): Add the specified directory or file to the filelist of the specific group.
			filelist_remove(<dir/file-path>,<group>): Remove the specified directory or file from the filelist of the specific group.
			filelist_refresh(): Refresh the filelists for all groups.
		Finally, there exist some miscellaneous functions that might prove useful:
			debug(<msg>): All functions send status, debug or error messages to a debug stream (which may or may not exist), via this function.
			cli(): A function that provides a command line interface (CLI) for the client, for situations when a GUI extension is not available.
				Note, however, that the functionality of this CLI is highly restricted, given that it was primarily designed for testing purposes.
		"""

	################################################## Miscellaneous/Useful Functions ##################################################

	def escape(self,data,type=False): # Converts specific characters that may appear in data into HTML entities, allowing the actual characters to take on a special significance.
		if type==False: return data.replace("&","&amp;").replace("|","&#124;").replace("$","&#36;");
		else:
			data2 = ""
			for char in data: data2 += char if char.isalnum() else "&#"+str(ord(char))+";"
			return data2
	def unescape(self,data): # Used to reobtain characters from the HTML entity form.
		match = re.findall("\&\#([0-9]{1,3})\;",data.replace("&amp;","&#38;"));
		for item in match: data = data.replace("&#"+item+";",chr(int(item)));
		return data
	def escape_filename(self,name):
		newname = ""
		for i in name:
			if i in "\/:*?\"<>|": newname+="&"+ord(i)+";"
			else: newname+=i
		return newname
	def filesize(self,x): # Takes a int/long number of bytes and translates them into human readable form in terms of KB, MB, GB, etc
		try: x = int(x)
		except: return "NA"
		if x<1024: return str(x)+" B"
		prefix = ["KB","MB","GB","TB","PB","EB","ZB","YB"]
		try: x = float(x)/1024 # Convert to KB
		except TypeError: return "NA" # Value too large
		for i in range(len(prefix)-1):
			if x<1024**(i+1): return "%.2f %s" % (x/1024**i,prefix[i])
		return "%.2f %s" % (x/1024**(len(prefix)-1),prefix[-1])
	def unique(self,listitem): # Return non-unique list-items, ordering lost
		return dict([(x,True) for x in listitem]).keys()
	def freespace(self,location): # Return free space in bytes avaialable at specfied location
		# Source: http://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python
		if platform.system() == 'Windows':
			free_bytes = ctypes.c_ulonglong(0)
			ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
			return free_bytes.value
		else: return os.statvfs(folder).f_bfree
	def str_divide(self,list,length): # Split a list into equal sized blocks, returning a list of them
		result = [] 
		for i in range(0,int(math.ceil(float(len(list))/length))): # Calculate how many blocks will be there
			result.append(list[i*length:(i+1)*length]) # Obtain each block using simple slicing
		return result
	def lock2key(self,lock): # Generates response to $Lock challenge from Direct Connect Servers
		# Written by Benjamin Bruheim; http://wiki.gusari.org/index.php?title=LockToKey%28%29
		lock = [ord(c) for c in lock]
		key = [0]
		for n in range(1,len(lock)):
			key.append(lock[n]^lock[n-1])
		key[0] = lock[0] ^ lock[-1] ^ lock[-2] ^ 5
		for n in range(len(lock)):
			key[n] = ((key[n] << 4) | (key[n] >> 4)) & 255
		result = ""
		for c in key:
			if c in [0, 5, 36, 96, 124, 126]:
				result += "/%%DCN%.3i%%/" % c
			else:
				result += chr(c)
		return result
	def spawn(self,name,function,arguments=()): # Takes a name, a function and a tuple/list/dict object as arguments, and starts it off in a new thread, returning a reference to the Thread object.
		newthread = threading.Thread(name=name, target=function, args=(arguments if type(arguments) in (tuple,list) else ()), kwargs=(arguments if type(arguments) is dict else {}) )
		newthread.start(); return newthread
		
	################################################## Connection Initialization/Termination ##################################################

	def __init__(self): # Initializes to default values all configuration variables and other objects required for the functioning of this system.
		self._step = {} # Container for step thread and function
		self._download = {} # Container for download manager thread and status variables
		self._config = {} # This dictionary will store all the configuration variables that will subsequently be used by this client.
		self._dir = {} # Application Directory Locations
		# User Details
		self._config["nick"] = "Anonymous" # User Nickname
		self._config["pass"] = "" # User Password
		self._config["status"] = 1 # User Status
		self._config["desc"] = "" # User Description
		self._config["email"] = "" # User EMail Address
		self._config["sharesize"] = 0 # Total size of data shared by the user in bytes
		self._config["operator"] = False # Whether or not this user is an operator on the hub
		# Client Details
		self._config["client"] = "pyDC" # Client Name
		self._config["version"] = "1" # Client Version
		self._config["connection"] = "100" # Connection Speed Indicator (Mbps)
		self._config["mode"] = True # Whether or not this client can act as a server for peer-to-peer transfers.
		self._config["cid"] = "%10d" % (random.randint(0,10**10-1)) # Client ID : CID needs to be pseudorandomly generated with negligible collision probability
		self._config["localhost"] = socket.gethostbyname(socket.gethostname()) # The IP Address of this system
		self._config["group_base"] = "general" # The name of the default group to which an unclassfied nick belongs to.
		self._config["filelist"] = "files.xml.bz2" # The identifier of filelists in _queue
		self._config["savedata"] = "configuration.dat" # The same of the file in which data will be saved
		self._config["sr_count"] = 10 # Maximum number of search results to return per request
		# Hub Details
		self._config["host"] = "localhost" # The address of the hub to which we want to connect
		self._config["port"] = 411 # The port at which the intended hub is running
		self._config["hubname"] = "" # The name of the hub to which you connect
		self._config["topic"] = "" # The topic of the hub to which you connect
		# Connection Details
		self._config["searchtime_manual"] = 15 # The time in seconds for which a user-initiated search is waiting for more results
		self._config["searchtime_auto"] = 5 # The time in seconds for which an automatic search for TTH alternates is waiting for results
		self._config["retry"] = 3 # Number of times a connection request will be sent to a remote host if it isnt responding
		self._config["wait"] = 5 # Number of seconds to wait between sending repeated connection requests.
		# Negotionation Details
		self._config["lock"] = "Majestic12" # A random string used during authentication
		self._config["key"] = self.lock2key(self._config["lock"]) # Generated using the above lock used during authorization
		self._config["signature"] = "SourceCode" # A random string used during negotiation, conventionally used to indicate client name
		self._config["support"] = "XmlBZList ADCGet TTHF" # The set of protocols that this client supports (space separated). More options: MiniSlots, TTHL, ZLIG
		# Transfer Control
		self._download["upslots"] = 0 # The number of upload slots currently in use
		self._download["maxupslots"] = 2 # The maximum number of upload slots possible
		self._download["downslots"] = 0 # The number of download slots currently in use
		self._download["maxdownslots"] = 5 # The maximum number of download slots possible
		# Step Control
		self._config["step_time"] = 1 # How long the step functions waits before each run
		self._step["active"] = False # Whether or not the step function is running
		self._step["thread"] = None # The thread pointing to the step function
		self._step["function"] = None # The function to be called at every step run
		self._step["args"] = None # Arguments that are provided to and returned by every call of the ste function.
		# Download Manager
		self._config["segment_size"] = 1024*1024*10 # 100MB : Size of blocks to be downloaded from different users
		self._config["download_time"] = 1 # How long the step functions waits before each run
		self._download["active"] = False # Whether the download manager is running
		self._download["thread"] = None # The thread pointing to the download manager function
		self._download["lock"] = threading.Semaphore() # A lock used to ensure that only one download is being inititated at a time.
		self._config["overwrite"] = False # Whether or not to overwrite existing files with the same name after download.
		# Default Streams/Connections
		self._mainchat = sys.stdout # The function to which mainchat messages are sent
		self._pm = None # The function to which mainchat messages are sent
		self._debug = None # The function to which debug information is to be printed to. Do not use unless actually necessary.
		self._socket = None # A connection to the Hub
		# Persistant Data Structires, except _config
		self._queue = [] # A list containing pseudo-objects of the format: {id,part,parts,type,nick,offset,length,priority,name,size,location,active}
		self._userips = {} # Used to keep track of the IP addresses of users, even if they arent available. Given the more persistant nature of this dictionary, it is rather useful in determining the nickname, given the IP.
		self._groups = { self._config["group_base"]:[] } # A dict of lists, key = groupname, list values = members
		self._filelist = { self._config["group_base"]:[] } # A dict containing group->list_of_dirs_to_be_shared entries. Entries here need to be shared yet.
		# Temporary Data Structures
		self._nicklist = {} # A list of all nicknames connected to this hub
		self._search = {} # A dict containing pointers to search pseudo-objects of the format: socket (a connection type object that sets up a UDP server on which to recieve search results), result (the stream to which results are sent upon arrival), mode (manual or auto)
		self._transfer = [] # A list containing pointers to transfer pseudo-objects of the format: {host,port,mode(active/passive),connection}
		self._shared = { self._config["group_base"]: xml.dom.minidom.Document() } # A xml.dom object containing the files and folders currently shared.
		# Constant Data Structures
		self._filetype = {"any":1,"audio":2,"compressed":3,"document":4,"executable":5,"image":6,"video":7,"folder":8,"tth":9} # Mapping of filetypes for search requests.
		self._fileextn = {2:"mp mp wav au rm mid sm", 3:"zip arj rar lzh gz z arc pak", 4:"doc txt wri pdf ps tex", 5:"pm exe bat com", 6:"gif jpg jpeg bmp pcx png wmf psd", 7:"mpg mpeg avi asf mov"} # Allowed extension for specific filetypes in search requests.
		self._save = "self._config,self._filelist,self._groups,self._queue,self._userips".split(",") # Constants based on which data is saved/loaded
		# Data Control
		self._dir["filelist"] = "Filelists"
		self._dir["incomplete"] = "Incomplete"
		self._dir["downloads"] = "Downloads"
		self._dir["settings"] = "Settings"
		# Ensure that all necessary directories exists
		if not os.path.isdir(self._dir["filelist"]): os.mkdir(self._dir["filelist"])
		if not os.path.isdir(self._dir["incomplete"]): os.mkdir(self._dir["incomplete"])
		if not os.path.isdir(self._dir["downloads"]): os.mkdir(self._dir["downloads"])
		if not os.path.isdir(self._dir["settings"]): os.mkdir(self._dir["settings"])
		# SHERIFFBOT : Additional variable to prevent userlist update during deepcopy
		self._nicklock = threading.Semaphore()
		self._config["ready"] = False
	def __del__(self): # Terminates all processes by called close()
		self.disconnect()
	def debug(self,data): # An intermediate used by all functions of this class to print out debugging information when required.
		try: self._debug(time.strftime("%d-%b-%Y %H:%M:%S",time.localtime())+" "+self._config["host"]+":"+str(self._config["port"])+" : "+data+"\n")
		except TypeError: pass
	def active(self): # Returns a boolean value indicating 
		try: return self._socket.active() and self._config["ready"]
		except: return False
	def configure(self,data): # Allows the users to configure the client according to his wishes.
		# Load data provided by user
		if self.active(): self.debug("Cannot configure client while the connection is active.")
		# if os.path.isfile(self._dir["settings"]+os.sep+self._config["savedata"]): self.load() # Load configuration if possible
		if False: pass # Loading configuration causes more problems than it solves.
		else:
			self.debug("Configuration initiated ...")
			for key in ("name","nick","host"):
				if key not in data:
					return self
			for key in self._config.keys():
				if key in data: self._config[key] = data[key]
			self._config["ready"] = True
			self.debug("Configuration completed successfully.")
		return self
	def save(self): # Saves configuration and certain other variables to files, so that they can be loaded later.
		filename = self._dir["settings"]+os.sep
		if not self._config["ready"]: self.debug("Cannot save data while the connection is not ready.")
		if not os.path.exists(filename): self.debug("Settings Directory not longer exists.")
		else:
			f = open(filename+self._config["savedata"],"w")
			f.write(str(dict([(x,eval(x)) for x in self._save])))
			f.close()
			# self.debug("Data saved successfully.") # Disabled due to excessive debug info generation
		return self
	def load(self): # Loads configuration and certain other variables to files, so that they need not be manually configured again.
		if self.active(): self.debug("Cannot load data while the connection is active.")
		else:
			self.debug("Loading data ...")
			f = open(self._dir["settings"]+os.sep+self._config["savedata"],"r")
			data = eval(f.read())
			for key in data: exec key+" = "+str(data[key])
			f.close()
			self.debug("Data loaded successfully.")
			self.debug("Loading Filelist(s) ...")
			for group in self._groups:
				x = self._dir["filelist"]+os.sep+"#"+self.escape_filename(group,True)+".xml"
				if os.path.isfile(x): self._shared[group] = xml.dom.minidom.parse(x) # If the filelist for that group exists, load it
				self.filelist_generate(group) # Update/Generate it if required.
			self.debug("Filelist(s) loaded successfully.")
		return self
	def reset(self): # Deletes all previously saved configuration settings
		for var in self._save: os.remove(self._dir["settings"]+os.sep+var[5:])
		return self
	def link(self,data={}): # Allows the user to specify streams, which are distict from configuration options.
		if type(data) is not dict:
			self.debug("A dictionary of functions needs to be provided to the link function.")
		else:
			self._mainchat = data["mainchat"] if "mainchat" in data else sys.stdout.write
			self._debug = data["debug"] if "debug" in data else None
			self._pm = data["pm"] if "pm" in data else (lambda nick,msg: self._mainchat("Private Message : "+msg+"\n"))
			self.debug("Client links configured.")
		return self
	def step(self,func,args=None): # Can be used to define a function that will be called periodically.
		if self.active(): self.debug("Cannot set step function while the connection is active.")
		else:
			self._step["function"] = func
			self._step["args"] = args
			self.debug("Step function set successfully.")
		return self

	################################################## Connection Management ##################################################

	def connect(self,hubcount): # Connects to the hub.
		self.debug("Attempting to connect to Hub ...")
		if re.match("^[0-9]+/[0-9]+/[0-9]+$",hubcount) is not None:
			self._config["hubcount"] = hubcount
		else:
			self.debug("Invalid Hub Count.")
			return self
		if not self._config["ready"]: return self
		self._socket = Connection({ "name":"DC Hub", "host":self._config["host"], "port":self._config["port"], "type":"tcp", "role":"client", "handler":self.server_handler, "args":{"buffer":""}, "debug":self._debug })
		self.debug("Connected to Hub.")
		self._step["active"] = True
		self._step["thread"] = self.spawn("Step Function",self.step_actual)
		self._download["active"] = True
		self._download["thread"] = self.spawn("Download Manager",self.download_manager)
		return self
	def step_actual(self): # The actual function that waits for a fixed time between cycles and calls step_function.
		while self._step["active"]:
			self.save() # Save data periodically, in case of improper termination
			if self._step["function"] is not None:
				try: self._step["args"] = self._step["function"](self._step["args"])
				except: pass
			time.sleep(self._config["step_time"])
		return self
	def disconnect(self): # Terminate all child threads of this object before disconnecting from the hub.
		self._debug = lambda s: sys.stdout.write(s+"\n") # NOTICE : Debugging purposes
		self.debug("Terminating all searches ...")
		for item in self._search: # Terminate all searches
			if self._search[item]["socket"] is not None and self._search[item]["socket"].active():
				self._search[item]["socket"].close()
		self.debug("Terminating all transfers ...")
		for transfer in self._transfer: # Terminate all transfers spawned
			if transfer["socket"].active():
				transfer["socket"].close()
		self.debug("Terminating download manager thread ...")
		self._download["active"] = False
		if self._download["thread"] is not None:
			self._download["thread"].join()
		self.debug("Terminating step thread ...")	
		self._step["active"] = False
		if self._step["thread"] is not None:
			self._step["thread"].join() # Terminate step thread
		self._step["thread"] = None
		self.debug("Terminating connection to server ...")
		if self._socket is not None:
			self._socket.close() # Terminate connection to server
		self.debug("Disconnected from Hub.")
		return self
	def reconnect():
		self.disconnect()
		self.connect(self._config["hubcount"])
	def server_handler(self,data,info,args): # Interacts with the DC, responding to any commands that are sent by it.
		if data is None:
			if "buffer" not in args: args = {"buffer":""}
			return args
		args["buffer"]+=data
		for iteration in range(args["buffer"].count("|")):
			# Isolate a particular command
			length = args["buffer"].index("|")
			if length==0:
				args["buffer"] = args["buffer"][1:]
				continue
			data = args["buffer"][0:length]
			args["buffer"] = args["buffer"][length+1:]
			if data[0]=="<" and self._mainchat: self._mainchat(data+"\n")
			elif data[0]=="$":
				x = data.split()
				if x[0]=="$Lock": self._socket.send("$Supports UserCommand UserIP2 TTHSearch ZPipe0 GetZBlock |$Key "+self.lock2key(x[1])+"|$ValidateNick "+self._config["nick"]+"|")
				elif x[0]=="$Supports": self._config["hub_supports"] = x[1:]
				elif x[0]=="$HubName":
					self._config["hubname"] = x[-1]
					self._mainchat("Hub Name : "+self._config["hubname"]+"\n")
				elif x[0]=="$GetPass": self._socket.send("$MyPass "+self._config["pass"]+"|")
				elif x[0]=="$BadPass":
					self.disconnect()
				elif x[0]=="$Hello":
					if x[1]==self._config["nick"]:
						self._socket.send("$Version "+self._config["version"]+"|$MyINFO $ALL "+self._config["nick"]+" "+self._config["desc"]+" <"+self._config["client"]+" V:"+str(self._config["version"])+",M:"+("A" if self._config["mode"] else "P")+",H:"+self._config["hubcount"]+",S:"+str(self._download["maxupslots"])+">$ $"+self._config["connection"]+chr(self._config["status"])+"$"+self._config["email"]+"$"+str(self._config["sharesize"])+"$|$GetNickList|")
					else:
						try: self._nicklist[x[1]]
						except: self._nicklist[x[1]] = {"operator":False,"bot":False} # $OpList and $BotList commands will soon follow (if required), so we can make this assumption here.
				elif x[0]=="$LogedIn": self._config["operator"] = True
				elif x[0]=="$HubTopic":
					self._config["topic"] = data[10:]
					self._mainchat("Hub Topic : "+self._config["topic"]+"\n")
				elif x[0]=="$NickList":
					self._nicklock.acquire()
					for nick in data[10:].split("$$"):
						if nick=="": continue
						try: self._nicklist[nick]
						except KeyError: self._nicklist[nick] = {"operator":False,"bot":False}
						try: self._nicklist[nick]["ip"] = self._userips[nick]
						except KeyError: pass
					self._socket.send("$UserIP "+data[9:]+"|")
					self._nicklock.release()
				elif x[0]=="$UserIP":
					for item in data[8:].split("$$"):
						if item=="": continue
						nick,ip = item.split()
						self._userips[nick] = ip
				elif x[0]=="$OpList":
					ops = data[8:].split("$$")
					for nick in self._nicklist:
						if nick=="": continue
						self._nicklist[nick]["operator"] = (True if nick in ops else False)
				elif x[0]=="$BotList":
					bots = data[9:].split("$$")
					for nick in self._nicklist:
						if nick=="": continue
						self._nicklist[nick]["bot"] = (True if nick in bots else False)
				elif x[0]=="$MyINFO":
					nick,desc,conn,flag,email,share = re.findall("^\$MyINFO \$ALL ([^ ]*) ([^\$]*)\$ \$([^\$]*)([^\$])\$([^\$]*)\$([^\$]*)\$$",data)[0]
					try: self._config["nicklist"][nick]
					except KeyError: self._nicklist[nick] = {"operator":False,"bot":False}
					self._nicklist[nick]["desc"] = desc
					self._nicklist[nick]["conn"] = conn
					self._nicklist[nick]["flag"] = flag
					self._nicklist[nick]["email"] = email
					self._nicklist[nick]["share"] = share
				elif x[0]=="$To:":
					info2 = re.findall("^\$To\: ([^ ]*) From: ([^ ]*) \$(.*)$",data)
					if len(info2)==0: continue
					else: info2 = info2[0]
					if self._config["nick"]!=info2[0]: continue
					try: self._pm( info2[1] , time.strftime("%d-%b-%Y %H:%S",time.localtime())+" "+info2[2] )
					except TypeError: pass
				elif x[0]=="$Quit":
					try: del self._nicklist[x[1]]
					except KeyError: pass
				elif x[0]=="$ForceMove":
					if x[1].count(":")==0: addr = (x[1],411)
					elif x[1].count(":")==1: addr = tuple(x.split(":"))
					else:
						self.debug("Invalid Redirection Address")
						continue
					if self._config["host"]==addr[0] and self._config["port"]==addr[1]:
						self.debug("Redirected to the same hub : "+x[1])
						continue
					self._config["host"],self._config["port"] = addr
					self.reconnect()
				elif x[0]=="$Search": self.search_result_generate(data)
				elif x[0]=="$SR": self.search_result_process(data)
				elif x[0]=="$ConnectToMe":
					continue # SHERIFFBOT
					remote = x[2] # This client's mode does not matter here
					d = {"host":remote.split(":")[0], "port":remote.split(":")[1] }
					d["socket"] = Connection({ "name":remote,"host":remote.split(":")[0],"port":remote.split(":")[1],"role":"client","type":"tcp","handler":self.transfer_handler,"args":{"role":"client","transfer":d},"debug":self._debug })
					self._transfer.append(d)
				elif x[0]=="$RevConnectToMe":
					continue # SHERIFFBOT
					self.connect_remote(x[1],False)
				else: self.debug("Unrecognized Command : "+data)
			# end of iteration
		return args

	################################################## Interaction Functions ##################################################

	def mc_send(self,data): # Write to the mainchat for all users to see
		self._socket.send("<"+self._config["nick"]+"> "+self.escape(data)+"|") # Sending a raw command containing another nick here causes the server to reject it.
		return self
	def pm_send(self,nick,data): # Sends a private message to the specified user
		self._socket.send("$To: %s From: %s $<%s> %s|" %(nick,self._config["nick"],self._config["nick"],self.escape(data)))
		return self
	def download_tth(self,tth,name=None,location=None,success_callback=None,success_callback_args=None,failure_callback=None,failure_callback_args=None): # INCOMPLETE : Validate TTH
		self._queue.append({"id":tth,"incomplete":tth,"parts":-1,"type":"tth","nick":[],"priority":3,"name":name,"location":location,"active":False,"considered":False,"success_callback":success_callback,"success_callback_args":success_callback_args,"failure_callback":failure_callback,"failure_callback_args":failure_callback_args})
		return self
	def download_filelist(self,nick,success_callback=None,success_callback_args=None,failure_callback=None,failure_callback_args=None): # Downloads the filelist of a specific user
		flag = True
		for item in self._queue:
			if item["id"]==self._config["filelist"] and item["incomplete"]==self.escape_filename(nick)+".filelist" and item["name"]=="@"+self.escape_filename(nick)+".xml.bz2": flag = False
		if flag:
			self._queue.append({"id":self._config["filelist"],"incomplete":self.escape_filename(nick)+".filelist","part":0,"parts":1,"type":"file","nick":[nick],"offset":"0","length":-1,"priority":5,"name":"@"+self.escape_filename(nick)+".xml.bz2","size":-1,"location":self._dir["filelist"], "active":False,"considered":False,"success_callback":success_callback,"success_callback_args":success_callback_args,"failure_callback":failure_callback,"failure_callback_args":failure_callback_args})
		return self
	def download_manager(self): # An infinite loop that keeps trying to start queued downloads.
		while self._download["active"]: # Keep doing this as long as the client runs
			flag = False; # Initially assume that new search will be performed, so wait for a while before the next cycle
			for item in self._queue: # For each item in queue
				if not self._download["active"]: # Check if the client isnt being shut down
					flag = True; break # Download Manager is being terminated
				# print "Download Queue :", [i["name"]+":"+str(i["part"]) if "part" in i else "-1" for i in self._queue] # NOTICE : DEBUG only
				if self._download["downslots"]==self._download["maxdownslots"]: break # If slots are not available, wait for a while
				if item["active"]==True or item["considered"]==True: continue # If item isnt already being downloaded
				if item["type"]=="file": # Filelist Downloads
					item["considered"] = True
					def fail():
						item["considered"] = False
						self.debug("Removing filelist from queue as "+str(item["nick"])+" is not responding.")
						self._queue.remove(item) # SHERIFFBOT : Delete this item from queue
						if item["failure_callback"]!=None:
							try:
								if item["failure_callback_args"]!=None: item["failure_callback"](item["failure_callback_args"])
								else: item["failure_callback"]()
							except:
								self.debug("Failure Callback Function Error : "+str(args["get"]))
								exc_type, exc_value, exc_traceback = sys.exc_info()
								traceback.print_exception(exc_type, exc_value, exc_traceback, limit=10, file=(sys.stdout))
					self.connect_remote(item["nick"],True,fail) # Connect to the peer. Filelists always have only one part, an assumption made in filelist_get.
				elif item["type"]=="tth": # TTH Downloads
					if item["parts"]==-1: # What to do if no other information about the file is available
						flag = True # No need to wait after one cycle
						result = [] # List to hold search results from sources
						self.search("TTH:"+item["id"],lambda x:result.append(x),{"type":"tth","mode":"auto"}) # Start a search for sources
						time.sleep(self._config["searchtime_auto"]) # Assume that search results will arrive in this much time
						if len(result)==0: continue # No results - cant do anything about that :(
						if item["name"] is None: item["name"] = re.split("/",result[0][2].replace("\\","/") )[-1] # If name isnt provided, use the one from the first search result to arrive.
						item["size"] = int(result[0][3]); # Set total file size, to be used during rebuilding
						item["nick"] = self.unique(item["nick"]+[x[1] for x in result]) # Initialize/Expand source list, without redundancy
						parts = int(math.ceil(float(item["size"])/self._config["segment_size"])) # Calculate number of blocks this file is not be divided into based on preconfigured block size.
						if parts==0: # If the file is empty (size 0), write it now only.
							open(self.transfer_filename(item),"wb").close() # Create and close an empty file.
							continue # We can assume after this point that at least one part is present.
						item["parts"] = parts; item["length"] = self._config["segment_size"] # Setting general infomration applicable to all parts, except last.
						for part in range(parts-1): # Leaving out the last part, given that the length may be different.
							item["part"] = part; item["offset"] = part*self._config["segment_size"]; # Set part-specific information
							self._queue.append(copy.deepcopy(item)) # All parts now have information all necessary information, and may now be treated individually.
						item["part"] = parts-1; item["offset"] = (parts-1)*self._config["segment_size"]; # It is not necessary to append the last block again, as we can transform the current one into that.
						item["length"] = ((item["size"]+self._config["segment_size"]-1)%self._config["segment_size"])+1 # Get the exact length of the last part
						print "added "+str(parts)+" items"
					if not self.transfer_verify(item): # Check whether or not this item has already been downloaded.
						x = [i for i in self._queue if (item["id"]==i["id"] and "part" in i and item["part"]==i["part"])] # Isolate item with matching signature
						if len(x)==1 and x[0] in self._queue: self._queue.remove(x[0]) # Remove item from queue
						self.transfer_rebuild(item); continue # Try rebuilding it, but invariably move on
					connected = list(itertools.chain(*[[transfer[key] for key in transfer if key=="nick"] for transfer in self._transfer])) # Generate list of nicks to which we are already connected.
					nick = filter(lambda n: n not in connected and n in self._nicklist.keys(),item["nick"]) # Select only those to which we arent connected and are online. The original list isnt touched because 
					if len(nick)==0: continue # No one left :(
					print "Actually being considered ...",item["part"]
					item["considered"] = True
					def fail(): item["considered"] = False
					nick=random.choice(nick); # Randomly select a nickname
					# INCOMPLETE (possible) : Failure callbacks before file removal
					self.spawn("RemoteConnection:"+nick,self.connect_remote,(nick,True,fail)) # Connect to the nick. transfer_next deals with determining which file to download from the peer.
			if not flag: time.sleep(self._config["download_time"]) # If no searches have been performed, wait for a while before starting next cycle
		return self # Allows more functions to be chained in the same line

	################################################## Transfer Functions ##################################################

	def connect_remote(self,nick,rev=True,failure=None): # Sets up a connection with nick
		if type(nick) is list:
			if len(nick)==0: return self
			else: nick=nick[0]
		if self._config["mode"]: # Nothing can be done if both are passive
			port = random.randint(1000,2**16-1) # Randomly select +ve integer for a part number in the given range
			d = { "nick":nick } # This is the prototype for the transfer object, created so that the connection object it will contain will have a reference to it.
			self.debug("Sending connection request to "+nick+" ...")
			while True: # Keeping trying to bind to different port numbers
				try:
					d["socket"] = Connection({"name":nick,"host":self._config["localhost"],"port":port,"role":"server","type":"tcp","handler":self.transfer_handler,"args":{"role":"server","transfer":d,"failure":failure,"nick":nick},"debug":self._debug})
					break # Terminate loop only after binding to a specific port. Those Connections objects that could not bind have lost their 
				except ConnectionError: port = random.randint(0,2**16-1) # If this particular port is occupied,try another one randomly
			self._transfer.append(d)
			for retry in range(self._config["retry"]):
				self._socket.send("$ConnectToMe "+nick+" "+self._config["localhost"]+":"+str(port)+"|")
				time.sleep(self._config["wait"])
				if d["socket"].clients(): return self # Connection Successful
				self.debug("No response from "+nick+" after waiting for "+str(self._config["wait"])+" seconds.")
			self.debug("Connection to "+nick+" failed - timeout.")
			d["socket"].close() # Terminate the server
			if failure!=None: failure()
			return self
		elif rev:
			self._socket.send("$RevConnectToMe "+self._config["nick"]+" "+nick+"|")
			return self
	def transfer_verify(self,get): # Checks whether or not it is safe to download this file
		tempname = self._dir["incomplete"]+os.sep+self.escape_filename(get["incomplete"])+".part"+str(get["part"]) # Generate the name of the temporary file in which to store data before joining and transferring it to the target.
		if not get["active"] and (not os.path.exists(tempname) or os.path.getsize(tempname)<get["length"]): return True # If the file doesnt exist, or if the size hasent reached the target, start this download.
		x = [item for item in self._queue if item["id"]==get["id"] and item["incomplete"]==get["incomplete"] and "part" in item and item["part"]==get["part"]] # Locate items in the queue with the same signature as the current one.
		if len(x)==1 and x[0] in self._queue: self._queue.remove(x[0]) # As the file is already available completely, we can remove the corresponding item from the queue.
		return False # This object has not been verified for download, which means that it has already beeen downloaded, and rebuilding should be attempted.
	def transfer_next(self,args,info): # Check if we need to download something from this peer
		self._download["lock"].acquire() # Ensure that no other process is performing this procedure simultaneously. Thus, an inactive item selected will not become active unless it is done by this thread itself.
		get = [item[1] for item in sorted([ (item["priority"],item) for item in self._queue if item["active"]==False and args["nick"] in item["nick"] ])] # Select inactive items which this peer can provide, decreasing priority
		rebuild = []; # A list of items that have already been downloaded, and must be rebuilt.
		while len(get)>0: # For each item in the list, check to see if it is viable for download
			if self.transfer_verify(get[0]): # Return true if we can start the download.
				# get[0]["active"] = True;
				break # Activate this download, break out of the loop.
			rebuild.append(get[0]); get = get[1:] # Move this item out of the download queue, into the rebuild queue.
		self._download["lock"].release() # Release the lock ASAP, so that rebuilding doesnt block other threads.
		for item in rebuild: self.transfer_rebuild(item) # Try to rebuild each file that is found to be completely downloaded.
		self.debug("Checking for items that can be downloaded from "+args["nick"]+" : "+str(get))
		if len(get)>0:
			get = get[0]
			get["active"] = True
			self._download["downslots"]+=1
		else: get = None
		return get # The above loop will break when there are no items to download, or if an item has been selected.
	def transfer_filename(self,item): # Calculates the filename & location for a queue item; INCOMPLETE : Verify permissions
		location = (self._dir["downloads"] if (item["location"] is None or not os.path.isdir(item["location"])) else item["location"]) # Calculate location based to availability and accessibility
		if item["name"].count(".")>0: # Count the number of dots to determine if there is an extension for this file.
			extn = "."+item["name"].split(".")[-1]; item["name"] = ".".join(item["name"].split(".")[:-1]); # Isolate the extension which is available after the last dot
		else: extn = "" # No extension for a file with no dots
		suffix=0; filename = location+os.sep+item["name"]+extn; # Initializing the suffix and starting with a base filename
		if self._config["overwrite"]:
			while os.path.isfile(filename): # Repeat until a free filename is obtained
				suffix+= 1; filename = location+os.sep+item["name"]+" ("+str(suffix)+")"+extn; # Add the incremented suffix to the base filename
		# NOTICE : In Linux, also need to ensure that we have the required permissions in the target location.
		return filename # This file is guaranteed to be accessible and writable.
	def transfer_rebuild(self,get): # Called when all parts of a file are downloaded, to join them and make a whole file
		more = False # Do more parts of the file exist in the download queue?
		for item in self._queue: # For each item in the download queue, check the ID and the Name attr to identify other parts
			if item["incomplete"]==get["incomplete"] and item["name"]==get["name"]: more = True # Found another part
		all = True # Have all parts been downloaded and are complete in size?
		tempname = self._dir["incomplete"]+os.sep+get["incomplete"]; # Generate the temporary name to be used multiple times later
		if not more: # If there arent more parts to be downloaded
			residue = ((get["size"]+self._config["segment_size"]-1)%self._config["segment_size"]+1) # Calculate the size of the last block
			for i in range(get["parts"]):
				filesize = os.path.getsize(tempname+".part"+str(i)) if os.path.isfile(tempname+".part"+str(i)) else -1
				if get["type"]=="file":
					pass # Leave filelists alone as they are always assumed to be one block.
				elif filesize==-1:
					all = False
					redownload = copy.deepcopy(get); redownload["part"] = i; redownload["offset"] = i*self._config["segment_size"];
					redownload["length"] = self._config["segment_size"] if i<get["parts"]-1 else residue; self._queue.append(redownload);
				elif i<get["parts"]-1 and filesize!=self._config["segment_size"]:
					all = False;
					if filesize>self._config["segment_size"]:
						os.remove(tempname+".part"+str(i)); filesize = 0;
					redownload = copy.deepcopy(get); redownload["part"] = i; redownload["offset"] = i*self._config["segment_size"]+filesize;
					redownload["length"] = self._config["segment_size"]-filesize; self._queue.append(redownload);
				elif i==get["parts"]-1 and filesize!=residue:
					all = False;
					if filesize>residue:
						os.remove(tempname+".part"+str(i)); filesize = 0;
					redownload = copy.deepcopy(get); redownload["part"] = i; redownload["offset"] = i*self._config["segment_size"]+filesize;
					redownload["length"] = residue-filesize; self._queue.append(redownload);
		if not more and all: # If no more parts are to be downloaded, and all parts are available.
			filename = self.transfer_filename(get) # Obtain the destination file name
			get["filename"] = filename
			handle_dest = open(filename,"wb") # Create file at new location, and manual transfer data from the temp location to that.
			for i in range(get["parts"]):
				handle_src = open(tempname+".part"+str(i),"rb")
				blocksize = 1024*1024 # 1 MB blocks
				while True: # Transfer data from source to destination
					datablock = handle_src.read(blocksize) 
					if datablock=="": break
					handle_dest.write(datablock)
				handle_src.close()
			handle_dest.close()
			for i in range(get["parts"]): # Delete all source parts
				while True:
					try:
						os.remove(tempname+".part"+str(i))
						break
					except WindowsError: time.sleep(1)
			filesize = os.path.getsize(filename)
			self.debug("Download complete : "+filename+" (FileSize: "+self.filesize(filesize)+")")	
			if get["location"]==self._dir["filelist"] and get["id"]==self._config["filelist"]: # Identify Filelists
				if self.bz2_compress(filename,False): os.remove(filename) # Decompress filelists
	def transfer_request(self,args,info): # Make the actual download request
		self.debug("Requesting "+str(args["get"])+" from "+args["nick"]+" ("+info["host"]+":"+str(info["port"])+") ...")
		tempname = self._dir["incomplete"]+os.sep+self.escape_filename(args["get"]["incomplete"])+".part"+str(args["get"]["part"])
		try: # If the part file already exists as the result of an interrupted download, resume, instead of restarting.
			if os.path.isfile(tempname):
				filesize = os.path.getsize(tempname)
				args["get"]["offset"] += filesize
				args["get"]["length"] -= filesize
		except: pass
		return "$ADCGET "+("file" if args["get"]["type"]=="tth" else args["get"]["type"])+" "+("TTH/" if args["get"]["id"]!=self._config["filelist"] else "")+args["get"]["id"]+" "+str(args["get"]["offset"])+" "+str(args["get"]["length"])+(" ZL1" if "ZLIG" in args["support"] else "")+"|"
	def transfer_download(self,args,info): # Read the connection buffer for new binary data, and save it.
		length = min(len(args["buffer"]),args["more"])
		args["handle"].write(args["buffer"][:length])
		args["handle"].flush()
		args["buffer"] = args["buffer"][length:]
		args["more"]-=length
		if args["more"]==0:
			self.debug("Download complete : "+str(args["get"])+" from "+info["host"]+":"+str(info["port"])+".")
			args["binary"] = False; args["handle"].close(); # Free up one download slot, enable writing to debug stream again and close file
			x = [item for item in self._queue if (item["id"]==args["get"]["id"] and item["incomplete"]==args["get"]["incomplete"] and item["part"]==args["get"]["part"])] # Isolate item with matching signature
			if len(x)==1 and x[0] in self._queue: self._queue.remove(x[0]) # Remove item from queue
			self.transfer_rebuild(args["get"]) # Try rebuilding
			if args["get"]["success_callback"]!=None:
				try:
					if args["get"]["success_callback_args"]!=None: args["get"]["success_callback"](args["get"]["filename"], args["get"]["success_callback_args"])
					else: args["get"]["success_callback"](args["get"]["filename"])
				except:
					self.debug("Success Callback Function Error : "+str(args["get"]))
					exc_type, exc_value, exc_traceback = sys.exc_info()
					traceback.print_exception(exc_type, exc_value, exc_traceback, limit=10, file=(sys.stdout))
			del args["get"] # Destroy the last reference to that queue item
			args["get"] = self.transfer_next(args,info) # Try and select the next item to download
			if args["get"] is not None: info["send"](self.transfer_request(args,info) ) # If there is such an item, start the download
			else:
				self._download["downslots"]-=1 # Return the allotted download slot for general use again
				info["close"]() # Or else, terminate connection.
		return args, info
	def transfer_upload(self,args,info,x): # Response to an ADCGET Request;
		if self._download["upslots"]==self._download["maxupslots"]:
			info["send"]("$Error All download slots already taken.|")
			return args,info
		group = self.group_find(args["nick"]) # Calculate the group
		if x[1]=="file" and x[2]==self._config["filelist"]: # If its a filelist
			target = self._dir["filelist"]+os.sep+"#"+self.escape_filename(group,True)+".xml.bz2" # Select the appropriate on
		elif x[1]=="file" and x[2].startswith("TTH/"): # If its a TTH specified file download
			filelist = self._shared[group].getElementsByTagName("FileListing")[0] # Select the appropriate filelist
			result = self.search_result_recursive(filelist,(None,None,"F","F",0,9,x[2][4:]),os.sep) # <ip>/<hub>, <port>/<nick>, isSizeRestricted, isMaxSize, size, fileType, searchTerm
			if len(result)==0: # No Results
				info["send"]("$Error File not found.|"); return args,info
			else: # TTH Results were found.
				target = result[0][0] # File Name relative to the paths added to the filelist
				for path in self._filelist[group]:
					if os.path.isdir(path): # If the path is a directory
						if path.endswith(os.sep): path = path[:-1] # Remove the trailing slash
						z = os.sep.join(path.split(os.sep)[:-1])+os.sep+target # Remove the folder name from the base path, as it appears in the final path too.
						if os.path.isfile(z): # Verify that the file indeed exists
							target = z; break # Target it and break out of the loop
					elif os.path.isfile(path) and path.endswith(target): # If the file was directly shared,
						target = path; break # Target and break out
		else:
			info["send"]("$Error Unsupported Request|")
			return args,info
		try: filesize = os.path.getsize(target)
		except WindowsError as w:
			print w
			info["send"]("$Error File Access Error : "+target) #.split(os.sep)[-1]+"|")
			return args,info
		x[4] = str(filesize)
		info["send"]("$ADCSND "+" ".join(x[1:])+"|")
		self._download["upslots"]+=1
		handle = open(target,"rb")
		args["binary"] = True
		for i in range(int( math.ceil(float(filesize)/self._config["segment_size"]) )):
			info["send"](handle.read(self._config["segment_size"]))
		args["binary"] = False
		handle.close()
		self._download["upslots"]-=1
		return args,info
	def transfer_handler(self,data,info,args): # Client-to-Client Handshake: Responds to data from remote host
		if data is None:
			if "host" not in args["transfer"]: args["transfer"]["host"]=info["host"]
			if "port" not in args["transfer"]: args["transfer"]["port"]=info["port"]
			if "buffer" not in args: # Initializations to be done when a TCP connection has just been set up.
				if args["role"]=="client": info["send"]("$MyNick "+self.escape(self._config["nick"])+"|")
				args = {"buffer":"", "binary":False, "support":[], "role":args["role"], "transfer":args["transfer"], "get":None, "error":False }
			else: # Destructor
				if args["get"] is not None and not args["error"]:
					self.spawn("RemoteConnection:"+args["nick"],self.connect_remote,(args["nick"],True))
				info["kill"]() # Release slots and kill server
			return args
		args["buffer"]+=data
		if args["binary"]: # Binary Data Transfer Mode, placed before command interpretation because they may arrive immediately after transfers
			args,info = self.transfer_download(args,info)
		while not args["binary"]: # Exchange of commands
			restart = False
			for iteration in range(args["buffer"].count("|")):
				length = args["buffer"].index("|")
				if length==0:
					args["buffer"] = args["buffer"][1:]
					continue
				data = args["buffer"][0:length]
				args["buffer"] = args["buffer"][length+1:]
				x = data.split()
				if x[0]=="$MyNick":
					args["nick"] = x[1]
					self._userips[args["nick"]] = info["host"]
					args["transfer"]["nick"] = x[1] # Save the nick in the transfer object for direct access
					if args["role"]=="server":
						info["send"]("$MyNick "+self.escape(self._config["nick"])+"|$Lock "+self._config["lock"]+" Pk="+self._config["signature"]+"|")
				elif x[0]=="$Lock":
					args["lock"] = x[1]
					if args["role"]=="client": info["send"]("$Lock "+self._config["lock"]+" Pk="+self._config["signature"]+"|")
					elif args["role"]=="server":
						args["get"] = self.transfer_next(args,info)
						args["rand1"] = 32766 # random.randint(0,32767)
						info["send"]("$Supports "+self._config["support"]+"|$Direction "+("Download" if args["get"] is not None else "Upload")+" "+str(args["rand1"])+"|$Key "+self.lock2key(args["lock"])+"|")
				elif x[0]=="$Supports":
					args["support"] = x[1:]
				elif x[0]=="$Direction":
					args["dir"] = x[1]
					args["rand2"] = int(x[2])
				elif x[0]=="$Key":
					args["key"] = " ".join(x[1:])
					if self._config["key"]!=args["key"]:
						info["close"](); continue;
					while args["role"]=="client":
						args["rand1"] = random.randint(0,32767)
						if args["rand1"]!=args["rand2"]: break
					if args["role"] =="client":
						args["get"] = self.transfer_next(args,info)
						info["send"]("$Supports "+self._config["support"]+"|$Direction "+("Download" if args["get"] is not None else "Upload")+" "+str(args["rand1"])+"|$Key "+self.lock2key(args["lock"])+"|")
					if args["get"] is not None and (args["dir"]=="Upload" or args["rand1"]>args["rand2"]): # If peer doest want to download, or if its random number is smaller, we can download
						info["send"](self.transfer_request(args,info))
					if args["get"] is not None and args["dir"]=="Upload": info["kill"]() # Neither side wants to download, so break the connection
				elif x[0]=="$ADCGET":
					# args,info = self.transfer_upload(args,info,x) # All uploads currently disabled.
					info["send"]("$Error You do not have the Access Level to download anything from SheriffBot.|") # SHERIFFBOT
					# SHERIFFBOT : If you cant download immediately, give up.
					args["get"]["active"] = False
					self._download["downslots"]-=1
					if args["get"]["failure_callback"]!=None:
						try:
							if args["get"]["failure_callback_args"]!=None: args["get"]["failure_callback"](args["get"]["failure_callback_args"])
							else: args["get"]["failure_callback"]()
						except:
							self.debug("Failure Callback Function Error : "+str(args["get"]))
							exc_type, exc_value, exc_traceback = sys.exc_info()
							traceback.print_exception(exc_type, exc_value, exc_traceback, limit=10, file=(sys.stdout))
				elif x[0]=="$ADCSND":
					args["more"] = int(x[4])
					if args["get"]["size"]==-1: args["get"]["size"] = int(x[4])
					args["binary"] = True
					args["handle"] = open( self._dir["incomplete"]+os.sep+args["get"]["incomplete"]+".part"+str(args["get"]["part"]),"ab")
					self.debug("Starting download : "+str(args["get"])+" from "+info["host"]+":"+str(info["port"])+".")
					args,info = self.transfer_download(args,info)
					if args["more"]==0: restart = True
					break
				elif x[0]=="$Error" or x[0]=="$MaxedOut": # Failed Downloads
					self.debug("Error downloading file : "+str(args["get"])+" : "+(data[7:] if x[0][1]=="E" else "No slots available."))
					# SHERIFFBOT : If you cant download immediately, give up.
					args["error"] = True
					args["get"]["active"] = False
					self._download["downslots"]-=1
					if args["get"]["failure_callback"]!=None:
						try:
							if args["get"]["failure_callback_args"]!=None: args["get"]["failure_callback"](args["get"]["failure_callback_args"])
							else: args["get"]["failure_callback"]()
						except:
							self.debug("Failure Callback Function Error : "+str(args["get"]))
							exc_type, exc_value, exc_traceback = sys.exc_info()
							traceback.print_exception(exc_type, exc_value, exc_traceback, limit=10, file=(sys.stdout))
				else: self.debug("Unrecognized Command : "+data)
				# END OF FOR LOOP
			if restart: continue
			else: break # Buffer Empty / Incomplete Data / File Segment Recieved
			# END OF WHILE LOOP
		return args

	################################################## Search Functions ##################################################

	def search(self,pattern,result,options={}): # Used to search for a pattern in other users' filelists; result is a function here
		if len(pattern)==0: return # Empty searches not allowed.
		ss = ["F","F","0","1",self.escape(pattern).replace(" ","$")] # isSizeRestricted, isMaxSize, size, fileType, searchTerm
		mode = "manual" # Default mode; "auto" is used when looking for sources for downloads, and has a much smaller wait time.
		if type(options) is dict:
			for key in options:
				if key=="limit": # Size Limit
					ss[0]="T" # There is a limit of the size of the file, default being Lower Limit
					if options[key]=="max": ss[1]="T" # Upper Limit on Size
				if key=="size": ss[2]=str(options[key]) # Actual value of Size Limit
				if key=="type" and options[key] in self._filetype: ss[3]=str(self._filetype[options[key]]) # File Type
				if key=="mode" and options[key] in ("manual","auto"): mode = options[key] # Search Mode
		if "display" not in options: options["display"] = None # Assuming the results are not to be sent to a stream.
		ss = "?".join(ss) # Combining all parameters into a search pattern
		self._search[ss] = { "mode":mode, "result":result } # Creating a search pseudo object, so that we can keep track of associated information
		if self._config["mode"]: # Active Mode
			port = random.randint(0,2**16-1) # Choose a random
			while True: # Keep trying till a free port is found
				try: # Connection constructor might raise an exception
					c = Connection({"name":ss,"host":self._config["localhost"],"port":port,"role":"server","type":"udp","handler":self.search_result_process,"args":{"ss":ss,"buffer":""},"debug":self._debug}) # Create a UDP server to listen for Search Results
					break # Stop only when the server has been setup
				except ConnectionError: port = random.randint(0,2**16-1) # Try another random port
			self._search[ss]["socket"] = c # Save the connection into the search object
			self._socket.send("$Search %s:%d %s|" % (self._config["localhost"],port,ss)) # Send a search command to the hub that will be echoed to all other clients
			self.spawn("SearchTimeout:"+ss,lambda:( time.sleep(self._config[ "searchtime_"+mode ]), c.close() )) # Stop listening for search results after specific amount of time
		else: # Passive Mode
			self._socket.send("$Search Hub:%s %s|" % (self._config["nick"],ss)) # Send a search command to the hub to be echoed to all peers.
			self._search[ss]["socket"] = None # Given passive connections, a limited number of results will be sent back via the hub only, so no dedicated connection is required.
		return self
	def search_result_generate(self,request):
		info = None # Represents that the search pattern is as of now, unrecognized
		if info is None: # Active Mode Search
			info = re.findall("^\$Search ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\:([0-9]{1,5}) ([TF])\?([TF])\?([0-9]*)\?([0-9])\?(.*)$",request)
			if len(info)==0: info = None # No matches, so list will be empty
			else: mode = True # Active
		if info is None: # Passive Mode Search
			info = re.findall("^\$Search (Hub):([^ ]*) ([TF])\?([TF])\?([0-9]*)\?([0-9])\?(.*)$",request)
			if len(info)==0: info = None
			else: mode = False # Passive
		if info is None: # Unrecognized command
			self.debug("Unrecognized search request - ignored : "+request)
			return self
		# Prepare the information available for easy access
		info = list(info[0]); # As there will always be only one match, so only one list item
		info[5] = int(info[5]); # Size Limit
		if info[5]==9: info[6]=info[6][4:] # Remove the initial "TTH/" tag.
		else: info[6] = self.unescape(info[6].replace("$"," ")) # Convert $ back to spaces
		if mode: # Active Mode : Try and estimate the nick based on IP
			group = self._config["group_base"] # Initially assume unknown user
			hits = 0 # Number of possible candidates based on IP
			for nick in self._nicklist: # Try for all nicknames
				if nick in self._userips and self._userips[nick]==info[0]: # See if the known IP for that nick matches this
					group = self.group_find(nick) # Candidate found
					hits+=1 # Keep track of number of candidates
			if hits>1: group = self._config["group_base"] # Multiple nicks with same IP, ambiguous situation
		else: group = self.group_find(info[1]) # Passive Case, nick provided
		try: filelist = self._shared[group].getElementsByTagName("FileListing")[0] # Based on the user, select the appropriate filelist
		except: return self # XXX 20120316 : IndexError list index out of range error
		result = self.search_result_recursive(filelist,info,os.sep) # Search though it; returns a list of results, in tuple form
		if len(result)==0: return self # If there arent any result, give up and die.
		random.shuffle(result); result = result[:self._config["sr_count"]] # Randomly select a small number of results
		for i in range(len(result)): # Appropriately format the results
			if len(result[i])==3: result[i] = "$SR "+self._config["nick"]+" "+result[i][0]+chr(5)+str(result[i][1])+" "+str(self._download["upslots"])+"/"+str(self._download["maxupslots"])+chr(5)+"TTH:"+result[i][2]+" ("+self._config["host"]+":"+str(self._config["port"])+")"+(chr(5)+info[1] if not mode else "")+"|" # File Result
			elif len(result[i])==1: result[i] = "$SR "+self._config["nick"]+" "+result[i][0]+" "+str(self._download["upslots"])+"/"+str(self._download["maxupslots"])+chr(5)+self._config["hubname"]+" ("+self._config["host"]+":"+str(self._config["port"])+")"+(chr(5)+info[1] if not mode else "")+"|" # Directory Result
		if mode: # Active Mode
			target = Connection({"name":"SearchResult","host":info[0],"port":info[1],"role":"client","type":"udp","debug":self._debug}) # Link to send the results
			for line in result: target.send(line) # Sequentially, send the results
		else: # Passive Mode
			for line in result: self._socket.send(line) # Send results to the hub
		return self
	def search_result_recursive(self,current,info,path):
		result = [] # The list to be returned
		# The info variable is a list of data in the format: <ip>/<hub>, <port>/<nick>, isSizeRestricted, isMaxSize, size, fileType, searchTerm
		for node in current.childNodes: # Loop through all items of the current directory
			if info[5]!=8 and str(node.nodeName)=="File": # Select only filenames
				nextloop = False # A flag for when the outer loop is to be controlled by an inner loop
				name = node.getAttribute("Name"); size = int(node.getAttribute("Size")); tth = node.getAttribute("TTH"); limit = int(info[4]); # These variables will be used later on
				if info[5]==9 and tth!=info[6]: continue # TTH Search and mismatch
				if info[5]!=9: # Non-TTH Searches
					name2 = name.lower() # Make patterns case insensitive
					for word in info[6].lower().split(): # For each word in the search term
						try:
							if name2.count(word)==0: # Check if this filename contains it
								nextloop = True; break # If yes, break out
						except UnicodeDecodeError: pass # DEBUG : Only ASCII allowed.
				if nextloop: continue # If there were no matches, move on to the next file
				if info[2]=="T": # There is a size limit
					if info[3]=="T" and size>limit: continue# Maximum Size Limit
					elif size<limit: continue # Minimum Size Limit
				if info[5]>1 and info[5]<8: # If a specific file type was requested
					for ext in self._fileextn[info[5]].split(): # For each extension in that file type group
						if name.endswith("."+ext): # Check if it is at the end of the filename
							nextloop = True; break # If yes, no need to check more
				else: nextloop = True; # This criterion does not applu
				if not nextloop: continue # If no, move on.
				result+=[(path[1:]+name,size,tth)] # All has gone well till now, so add it to the results.
			elif str(node.nodeName)=="Directory": # Select only directories
				nextloop = False # Flag
				name = node.getAttribute("Name") # Accesses multiple times later
				result+=self.search_result_recursive(node,info,path+name+os.sep) # Search through the directory itself
				if info[5] not in (1,8): continue # Folders dont have TTH or types
				name2 = name.lower() # case insensitive
				for word in info[6].lower().split(): # for each word in search term
					if name2.count(word)==0: # see if directory name has it
						nextloop = True; break # if yes, stop searching
				if nextloop: continue # if no, move on
				result+=[(path[1:]+name)] # directory match, add to results
		return result
	def search_result_process(self,data,info=None,args=None):
		# if self._search[ss]["result"] is not None: print >>self._search[ss]["result"],"Search Result [%s] : %s" % (pattern,data)
		if data is None: return args
		if args is None: # Passive
			for ss in self._search:
				self.search_result_forward(ss,str(data),True)
		else: # Active
			args["buffer"]+=data
			for iteration in range(data.count("|")):
				length = args["buffer"].index("|")
				data = args["buffer"][:length]
				args["buffer"] = args["buffer"][length+1:]
				self.search_result_forward(args["ss"],data,False)
		return args
	def search_result_forward(self,pattern,data,validate):
		try: ss = re.findall("^([TF])\?([TF])\?([0-9]*)\?([0-9])\?(.*)$",pattern)[0]
		except: return
		result = re.findall("^\$SR ([^ ]+) (.*)"+chr(5)+"([0-9]+) ([0-9]+)/([0-9]+)"+chr(5)+"([^ ]+) \("+re.escape(self._config["host"])+"\:"+re.escape(str(self._config["port"]))+"\)$",data)
		if len(result)==0: result = re.findall("^\$SR ([^ ]+) (.*) ([0-9]+)/([0-9]+)"+chr(5)+"([^ ]+) \("+re.escape(self._config["host"])+"\:"+re.escape(str(self._config["port"]))+"\)$",data)
		if len(result)==0: return
		result = list(result[0])
		if validate:
			name = result[1].lower()
			size = int(ss[2])
			type = int(ss[3])
			for word in self.unescape(ss[4].replace("$"," ")).lower().split():
				if name.count(word)==0: return 1 # All words should be present
			if len(result)==6:
				filesize = int(result[2]);
				if ss[0]=="T": # Size limit
					if ss[1]=="T" and filesize>size: return 2 # Maximum Size Limit
					elif ss[1]=="F" and filesize<size: return 3 # Minimum Size Limit
				if type in self._fileextn:
					match = False
					for extn in self._fileextn[type].split():
						if name.endswith("."+extn): match=True # Check extension
					if not match: return 4 # Extension mismatch
				elif type==9:
					result[5]
			if len(result)==5:
				if type in [2,3,4,5,6,7,9]: return 5 # File Types only
		if len(result)==6: # File Result
			result[3] = int(result[3]); result[4] = int(result[4])
			try: self._search[pattern]["result"](["File"]+result)
			except: self._mainchat("Search Result for \"%s\" from %s: %s (FileSize: %s) %s (Slots: %d/%d)\n" % (ss[4],result[0],result[1],self.filesize(result[2]),result[5].replace("TTH:","TTH: "),result[3],result[4]))
		if len(result)==5: # Directory Result
			result[2] = int(result[2]); result[3] = int(result[3])
			try: self._search[pattern]["result"](["Folder"]+result)
			except: self._mainchat("Search Result for \"%s\" from %s: %s (Directory) %s (Slots: %d/%d)\n" % (ss[4],result[0],result[1],result[4],result[2],result[3]))
		return 0 # Success

	################################################## Group Functions ##################################################

	def group_create(self,group): # Create a new group with the specified name.
		if group not in self._groups:
			self._groups[group] = []
			self.debug("Successfully created new group : "+group)
			self._filelist[group] = []
			self._shared[group] = None
		else: self.debug("A group by this name already exists : "+group)
		return self
	def group_add(self,group,nick): # Add a nick to the specified group, removing it from all others
		if group not in self._groups:
			self.debug("A group by this name does not exist : "+group)
		else:
			for key in self._groups: self._groups[key] = [other for other in self._groups[key] if other!=group] # Remove nick from all other groups, to ensure one group per nick
			self._groups[group].append(nick)
			self.debug("The user "+nick+" was successfully added to the group "+group)
		return self
	def group_remove(self,group,nick): # Remove a nick from a specified group.
		if group not in self._groups:
			self.debug("A group by this name does not exist : "+group)
		else:
			self._groups.remove(group)
			self.debug("The user "+nick+" was successfully removed from the group : "+group)
		return self
	def group_check(self,group,nick): # Check if the specified nick is part of the given group.
		if group not in self._groups: return False
		elif nick not in self._groups[group]: return False
		return True
	def group_find(self,nick): # Return the group to which the specified nick belongs
		for name in self._groups:
			if nick in self._groups[name]: return name
		return self._config["group_base"]
	def group_rename(self,group,newname): # Renames a group, by deleting the old one, and creating a new one.
		if group not in self._groups:
			self.debug("A group by this name does not exist : "+group)
		elif newname in self._groups:
			self.debug("A group by this name already exists : "+newname)
		else:
			self._group[newname] = self._group[group]
			self._filelist[newname] = self._filelist[group]
			self._shared[newname] = self._shared[group]
			self._groups.pop(group,None)
			self._filelist.pop(group,None)
			self._shared.pop(group,None)
		return self
	def group_delete(self,group): # Delete a group, causing all its memebers to fall back to the default group.
		if group==self._config["group_base"]:
			self.debug("This group is the default one and cannot be deleted : "+group)
		else:
			self._groups.pop(group,None)
			self._filelist.pop(group,None)
			self._shared.pop(group,None)
			self.debug("Successfully deleted group : "+group)
		return self

	################################################## Filelist Functions ##################################################

	def filelist_add(self,dir,group=None): # Add a directory to the filelist belonging to specified group.
		if group is None: group = self._config["group_base"]
		if not os.path.exists(dir):
			self.debug("Invalid directory specified for sharing.")
			return self
		if group in self._filelist:
			if dir not in self._filelist[group]: self._filelist[group].append(dir)
			self.debug("Directory/File successfully added to the filelist of group : "+group)
		return self
	def filelist_remove(self,dir,group=None): # Remove a directory from the filelist belonging to specified group.
		if group is None: group = self._config["group_base"]
		try:
			self._filelist[group].remove(dir)
			self.debug("Directory/File successfully removed from the filelist of group :"+group)
		except: pass
		return self
	def filelist_generate(self,group=None): # Based on current entires, generate a filelist belonging to specified group.
		if group is None: group = self._config["group_base"]
		self.debug("Attempting to generate filelist for group : "+group)
		if group not in self._filelist:
			self.debug("Invalid group specified for which filelist is to be generated.")
			return self
		if group not in self._shared or len(self._shared[group].getElementsByTagName("FileListing"))==0:
			self._shared[group] = xml.dom.minidom.Document()
			fl = self._shared[group].createElement("FileListing") # <FileListing Version="1" CID="_____" Base="/" Generator="_____">
			fl.setAttribute("Version","1"); fl.setAttribute("CID",self._config["cid"]); fl.setAttribute("Base","/"); fl.setAttribute("Generator",self._config["signature"])
		elif len(self._shared[group].getElementsByTagName("FileListing"))>0:
			fl = self._shared[group].getElementsByTagName("FileListing")[0]
		else: return # NOTICE : Error
		list = sorted(self._filelist[group])
		for item in list:
			self.filelist_generate_recursive(self._shared[group],fl,item)
		self._shared[group].appendChild(fl)
		target = self._dir["filelist"]+os.sep+"#"+self.escape_filename(group,True)+".xml"
		print >>open(target,"w"), self._shared[group].toprettyxml(indent="\t").replace('<?xml version="1.0" ?>','<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
		self.debug("Successfully generated filelist for group : "+group)
		self.bz2_compress(target)
		return self
	def filelist_generate_recursive(self,base,current,item): # Used by the filelist_generate method due to unknown recursion lengths.
		# "base" is the xml.dom.minidom.Document() object from which all elemnts are to be created, "current" is the name of the directory that contains the current item, "item" is the path and name of the current item
		if os.path.isdir(item): # <Directory Name="_____">
			if item[-1]==os.sep: item=item[:-1]
			dirname = item.split(os.sep)[-1]
			dirs = filter( lambda x: x.getAttribute("Name")==dirname , current.getElementsByTagName("Directory") )
			if len(dirs)==0: # Add this directory again only if it hasent been added yet.
				dir = base.createElement("Directory")
				dir.setAttribute("Name",dirname)
				current.appendChild(dir)
			else: dir = dirs[0]
			list = sorted(os.listdir(item)) # Separate object is created to ensure that it doesnt change during the following loop
			for file in list: self.filelist_generate_recursive(base,dir,item+os.sep+file)
		elif os.path.isfile(item): # <File Name="_____" Size="_____" TTH="_____"/>
			filename = item.split(os.sep)[-1]
			try: filesize = str(os.path.getsize(item))
			except: filesize = 0
			# If the name and the size of the file havent changed, assume that it has already been hashed.
			if len(filter( lambda x: x.getAttribute("Name")==filename and x.getAttribute("Size")==filesize , current.getElementsByTagName("File") ))==0:
				f = base.createElement("File")
				f.setAttribute("Name",filename)
				f.setAttribute("Size",filesize)
				f.setAttribute("TTH", self.tth_generate(item) )
				current.appendChild(f)
		else: return # Ignore files/directories that were accessible once, but not now. This will allow external harddisks to be disconnected and reconnected without the problem of rehashing.
	def filelist_refresh(self,group=None): pass # INCOMPLETE : Update the filelist belonging to specified group.
	def tiger_hash(self,data): # Generates the Tiger Hash for a given string
		result = tiger.hash(data) # From the aformentioned tiger-hash-python script, 48-char hex digest
		result = "".join([ "".join(self.str_divide(result[i:i+16],2)[::-1]) for i in range(0,48,16) ]) # Representation Transform
		result = "".join([chr(int(c,16)) for c in self.str_divide(result,2)]) # Converting every 2 hex characters into 1 normal
		return result
	def tth_generate(self,file): # Generates the Tiger Tree Hash (Merkle Tree) for a given file
		# During the hashing of the raw data from the file, the leaf hash function uses the marker 0x00 prepended to the data before tiger hashing it. Similarly, the marker 0x01 is prepended in case of internal nodes.
		blocksize = 1024 # Standard Block Size
		filesize = os.path.getsize(file) # Get filesize for subsequent calculations
		if filesize==0: return [[self.tiger_hash(chr(0))]] # On failure of getsize or if file is empty, return hash for empty file.
		try: handle = open(file,"rb") # Open file for reading in binary mode
		except: return None # If it doesnt exist or is inaccessible, dont bother.
		level = [[]] # List of Levels, Level 0 Empty
		for i in range(int(math.ceil(float(filesize)/blocksize))):
			block = handle.read(blocksize) # Read part of the file
			level[0].append(self.tiger_hash(chr(0)+block)) # Hash that part only, and put it in Level 0
		handle.close() # Close file
		current = 0 # Starting from level 0
		while len(level[0])>1: # If whole file hasent been hashed yet
			level.append([]) # Create new level
			for i in range(len(level[current])/2): # For all hash pairs
				level[1].append( self.tiger_hash(chr(1)+level[0][2*i]+level[0][2*i+1]) ) # Combine two hashes to get a binary tree like structure.
			if len(level[0])%2==1: level[1].append(level[0][-1]) # If last item cannot be paired, promote it untouched.
			del level[0] # Discard lower level hashes, as they are no longer necessary
		return base64.b32encode(level[0][0])[:-1] # Result will be 40 characters; discarding the trailing '=' makes it 39
	def bz2_compress(self,file,type=True): # Compress/Decompress files into/from the bz2 format. compress if type else decompess
		if not os.path.exists(file) or os.path.isdir(file): return False
		try: filesize = os.path.getsize(file)
		except: return False
		if not type and not file.endswith(".bz2"): return False
		blocksize = 102400
		if type: compressor = bz2.BZ2Compressor()
		else: decompressor = bz2.BZ2Decompressor()
		handle1 = open(file,"rb")
		handle2 = open(file+".bz2","wb") if type else open(file[:-4],"wb")
		for i in range(int(math.ceil(float(filesize)/blocksize))):
			if type: handle2.write(compressor.compress(handle1.read(blocksize)))
			else: handle2.write(decompressor.decompress(handle1.read(blocksize)))
		if type: handle2.write(compressor.flush())
		handle1.close(); handle2.close()
		self.debug("Successfully "+("" if type else "de")+"compressed file : "+file)
		return True
		
	################################################## Client Behaviour Functions ##################################################

	def cli(self): # Provide a Command Line Interface for testing purposes before the GUI can be built
		"Provides a Command Line Interface for the Direct Connect Client."
		print "Command Line Interface"
		while True:
			try:
				x = raw_input()
				if x=="!configure":
					print "Enter the Client Name              : ",; name = raw_input()
					print "Enter the Hub Address              : ",; host = raw_input()
					print "Enter the Nickname you wish to use : ",; nick = raw_input()
					print "Enter the Password you wish to use : ",; _pass = raw_input()
					self._configure({"name":name, "host":host, "nick":nick, "pass":_pass});
				if x=="!connect": self.connect()
				if x=="!disconnect": self.disconnect()
				if x=="!status": print "Connection Status : "+("mode" if self.active() else "Inactive")
				if x=="!nicklist":
					for nick in self._config["nicklist"]: print nick, self._config["nicklist"][nick]
				if x=="!exit":
					self.disconnect()
					break
				if len(x)>0 and x[0]=="?": self.search(x[1:],{"display":sys.stdout})
				if len(x)>0 and x[0]==":": self.mc_send(x[1:])
				if len(x)>0 and x[0]=="@": self.pm_send(x[1:].split()[0]," ".join(x.split()[1:]) )
				if len(x)>0 and x[0]=="~": exec (x[1:])
				if len(x)>0 and x[0]=="$": self._socket.send(x[1:])
				if len(x)>0 and x[0]=="^": self.download_tth("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
				if len(x)>0 and x[0]=="&": print [item["part"] for item in self._queue]
				if len(x)>0 and x[0]=="*":
					for t in sorted([t.name for t in threading.enumerate()]): print "THREAD :: "+t
			except KeyboardInterrupt: break
			except Exception as e: print e
		return self
		
if __name__=="__main__":
	data = { "mode":True, "name":"pyDC", "host":"127.0.0.1","nick":"SourceCode","pass":"password","desc":"","email":"","sharesize":1073741824,"localhost":"127.0.0.1","overwrite":True}
	def debug(debug_mode): return None if debug_mode==0 else open("debug.txt","w").write if debug_mode==1 else sys.stdout.write if debug_mode==2 else None
	x = pydc_client().configure(data).link({"mainchat":sys.stdout.write,"debug":debug(1) }).connect("0/1/0");
	x.cli();