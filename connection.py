# Modules names in alphabetical order
import os,re,select,socket,sys,threading,time

class ConnectionError(Exception):
	def __init__(self,name,code,mesg):
		self.name = name
		self.code = int(code)
		self.mesg = mesg
	def __str__(self):
		return "[Connection Error %d] %s : %s" % (self.code,self.name,self.mesg)
		
class Connection:
	"""
	Written by Kaustubh Karkare.
	The connection class aims to provide an extremely simple way to set up TCP/UDP Servers/Clients.
	Connections are creating using the statement similar to:
		link = connection({ "name":"TCP-Client", "host":"192.168.0.1", "port":12345, "type":"tcp", "role":"client", "handler":somefunction })
	The "name", "host", "port", "type" and "role" key-value pairs are non-optional. Each of these, along with the additional options are described:
		name : The name of the connection which used to identify it during debugging. It is recommended that you provide a unique name to each connection. In case of a server, each accepted connection is named by suffixing the remote host and port addresses to the name of the server connection.
		host : The IP Address or Host Name (which should be DNS resolvable) to which a connection is to be made (in clients) or at which incoming connections/data are/is to be recieved (in servers).
		port : The Port Number to be connected to (in clients) or listened at (in servers).
		type : Type of connection, must be either "tcp" or "udp".
		role : Role of this connection, muct be either "server" or "client".
		handler : A function that will be called whenever new data is recieved, described in more detail later.
		debug : A file-like object to which all debugging messages will be sent, with the connection name suffixed (default value = None).
		family : Type of socket family, must be "ipv4".
		maxconn : The maximum number of connections that a server should handle at a time. The server rejects any additional incoming connections (default value = 10).
		poll : The amount of time between checks for new data, in seconds (default value = 1).
		buffer : The size of the data that is to be read from the stream, in bytes (default value = 1024).
	Handler Functions:
		In case of a TCP-Server, whenever a client tries to set up a connection to it, a new TCP-Client-type connection object is created, and the handler function is passed down.
		In case of a TCP-Client, whenever new data is recieved, the handler function is called with three arguments: data (which was just recieved), info and args (a dictionary that contains additional data to be passed to this function is specified during creation of the connection).
			The info argument contains a dictionary containing useful information about the connection like remote host, port and pointers to functions to send data to the remote host, to terminate the client connection, and to kill the spawning server too.
			Whatever this function returns will be saved in the connection as args, and provided to it during the next function call. If args is a dictionary, and contains a key "binary", whose value is True, logging of recieved TCP data is disabled, until this is changed. This is useful while transferring large amounts of binary data.
			In case the data to be recieved exceeded the buffer-size, it is the responsibility of the handler function to keep records and append the different pieces together.
			The handler function call in case of a TCP-Client is blocking - no new data will be read from the stream till the function returns.
			There are however two exceptional cases where the above rules do not apply: When the connection is initially established, or is being terminated, this function will be called with the data argument set to None. Note however, that the termination call is unreliable.
		In case of UDP-Servers, the handler function is defined the same way is that of the TCP-Client.
			The return value of this function is ignored completely, as it would only create problems due to the multithreaded nature in which is is called.
			However, it is non-blocking - each handler function call has its own thread and therefore, the function must be thread-safe.
		In case of UDP-Clients, the handler function is not required, and may be omitted from the constructor itself.
	The various functions that are available to you for use are (the self argument has been omitted for simplicity's sake in the following list):
		__init__(data): Takes a dictionary type object and calls configure(data), followed by setup()
		configure(data):
			Verifies the values provided in the dictionary type object provided and makes the connection ready for use.
			All Configuration variables MUST be set using the configure() function.
			If the connection was active when you change the Configuration, the original connection will be lost, and a new one will be automatically setup. You may continue to use the same connection object.
		setup(): 
			The setup() function establishes links with the server (if you are setting up a client) or starts listening for connections on the given port.
			In a server, an infinite loop (that can be terminated using the close() function) begins that checks for incoming connections and creates a new client object when they do to interact with them.
			In a client, a similar infinite loop (terminated using close()) keeps checking for data that is recieved from the remote system.
			This function is non-blocking as the above loops are run in a parallel thread.
		info(): Returns a string describing the connection.
		active(): Returns a boolean value that indicates whether or not the connection is active.
		clients(): Returns a boolean value that indicates whether or not this TCP Server has had or still has active connections with clients.
		send(): Sends data over the connection to the remote host, as specified in the Configuration.
		wait(): Suspends execution (in the calling thread) until this connection is terminated.
		close():
			In case of a TCP Server, closing the connection (using close()) would result in the closing of all objects that were created in response to clients that connected to this server.
			This process is blocking - execution is suspended until the termination process is complete.
	Error Codes:
		1 : Missing option required for Configuration.
		2 : Attempt to modify read-only data during Configuration.
		3 : Invalid data provided for options used in Configuration.
		4 : Could not bind to given port as it is already bound to some other connection/socket.
		5 : Could not bind to specified socket.
		6 : Connection terminated by remote host.
	"""
	
	def spawn(self,name,function,arguments=()):
		"Takes another function and a tuple/list/dict object as arguments, and starts it off in a new thread, returning a reference to the Thread object."
		"The functions should have handled all exceptions that might occur, or must not raise any, to ensure proper functioning."
		newthread = threading.Thread(name=name, target=function, args=(arguments if type(arguments) in (tuple,list) else ()), kwargs=(arguments if type(arguments) is dict else {}) )
		newthread.start()
		return newthread
	
	def __init__(self,data,link=None):
		"Takes a dictionary object and uses that information to configure this connection."
		self._config = {"ready":False,"active":False}
		if link is None:
			self.configure(data)
			self.setup()
		else: # In case of connections made to TCP Server, TCP Client objects are created, with socket objects already available.
			self._config = data
			self._config["socket"] = link
			self._config["active"] = True
			self._config["info"] = { "host":self._config["host"], "port":self._config["port"], "send":self.send, "close":self.close_internal, "kill":self._config["parent"].close_internal }
			self._config["args"] = self._config["handler"](None,self._config["info"],self._config["args"])
			self._config["thread"] = self.spawn(self.info(),self.loop)
			self._config["ready"] = True
	
	def __del__(self):
		"Terminates the connection."
		self.close()
	
	def debug(self,data):
		try: self._config["debug"](time.strftime("%d-%b-%Y %H:%M:%S",time.localtime())+" "+self._config["name"]+" : "+data+"\n")
		except: pass
	
	def configure(self,data): # Allows the setting of certain required Configuration variables and the overriding the default values of other predefined ones.
		if self._config["active"]:
			self.close();
			interrupt = True;
		else: interrupt = False
		self._config = { } # A container for all configuration variables to be used.
		self._config["name"] = "Anonymous" # Default connection Name
		self._config["ready"] = False # At this time, the connection is not configured to be ready for operation.
		self._config["active"] = False # Is this connection actively listening (servers) / connected (clients) right now?
		self._config["args"] = None # The arguments to be passed to and returned from the handler function when new data arrives.
		self._config["type"] = "tcp" # Transport Layer Protocol: tcp or udp
		self._config["family"] = "ipv4" # Internet Layer Protocol: ipv4, ipv6
		self._config["maxconn"] = 1 # Maximum number of client connections that take server will take before rejecting additional ones.
		self._config["poll"] = 1 # The time intervals, in seconds, at which new data is checked for.
		self._config["buffer"] = 1024 # The size of the buffer in which the data that arrives if to be read.
		self._config["debug"] = None # The function to which to send debugging information.
		self._config["parent"] = None # In case of spawned TCP Clients, it is a pointer to the source server.
		self._config["link"] = [] # In case of TCP Servers, a list of all Clients spawned in response to connections.
		self._config["clients"] = False # Has this server had any client connections till now?
		if type(data) is not dict: return self # The 
		for key in ("name","host","port","role","type"):
			if key not in data: raise ConnectionError(self._config["name"],1,"Missing option '"+key+"'.")
		for key in data:
			if key in ("ready","active","socket","clients"): raise ConnectionError(self._config["name"],2,"Attempt to modify read-only attribute '"+key+"'.")
			if key in ("port","maxconn","poll","buffer"):
				try: self._config[key]=int(data[key])
				except ValueError: raise ConnectionError(self._config["name"],3,"Invalid value provided for '"+key+"' option.")
			elif key is "role" and data[key] not in ("server","client"): raise ConnectionError(self._config["name"],3,"Invalid value provided for 'role' option.")
			elif key is "type" and data[key] not in ("tcp","udp"): raise ConnectionError(self._config["name"],3,"Invalid value provided for 'type' option.")
			elif key is "family" and data[key] not in ("ipv4"): raise ConnectionError(self._config["name"],3,"Invalid value provided for 'family' option.")
			else: self._config[key] = data[key]
		if self._config["type"] is not "udp" or self._config["role"] is not "client":
			if "handler" not in data: raise ConnectionError(self._config["name"],1,"Missing option '"+handler+"'.")
		self._config["ready"] = True
		self.debug("Configuration completed successfully : "+str(self._config))
		if interrupt: self.setup()
		return self
	
	def initiate(self):
		"Sets up connections with the remote host, and getting them ready for data transfer."
		if not self._config["ready"]: return self
		try:
			family = socket.AF_INET
			if self._config["type"] is "tcp" and self._config["role"] is "server":
				self._config["socket"] = socket.socket(family,socket.SOCK_STREAM)
				self._config["socket"].bind( (self._config["host"],self._config["port"]) )
				self._config["socket"].listen(self._config["maxconn"])
				self.debug("TCP Server set up and listening at "+self._config["host"]+":"+str(self._config["port"])+".")
			elif self._config["type"] is "tcp" and self._config["role"] is "client":
				self._config["socket"] = socket.socket(family,socket.SOCK_STREAM)
				self._config["socket"].connect( (self._config["host"],self._config["port"]) )
				self.debug("TCP Client set up and connected to "+self._config["host"]+":"+str(self._config["port"])+".")
				self._config["info"] = { "host":self._config["host"], "port":self._config["port"], "send":self.send, "close":self.close_internal, "kill":self.close_internal }
				self._config["active"] = True
				self._config["args"] = self._config["handler"]( None, self._config["info"], self._config["args"] )
			elif self._config["type"] is "udp" and self._config["role"] is "server":
				self._config["socket"] = socket.socket(family,socket.SOCK_DGRAM)
				self._config["socket"].bind( (self._config["host"],self._config["port"]) )
				self.debug("UDP Server set up and listening at "+self._config["host"]+":"+str(self._config["port"])+".")
			elif self._config["type"] is "udp" and self._config["role"] is "client":
				self._config["socket"] = socket.socket(family,socket.SOCK_DGRAM)
				self.debug("UDP Client set up to connect to "+self._config["host"]+":"+str(self._config["port"])+".")
			self._config["active"] = True
		except socket.error, e:
			if e.errno==10048: raise ConnectionError(self._config["name"],5,"Could not bind to "+self._config["type"].upper()+" port "+str(self._config["port"])+".")
		return self
	
	def loop(self):
		"An infinite loop that waits for data to be recieved from the remote host, and calls a handler function when it arrives."
		if self._config["type"] is "udp" and self._config["role"] is "client": return self
		try:
			while self._config["active"]: # Verify that no other process has tried to kill this _config
				if self._config["socket"] not in select.select([self._config["socket"]],[],[],1)[0]: # Verify that data is indeed available to read
					time.sleep( self._config["poll"] ); continue; # If not, wait for some time and recheck
				if self._config["type"] is "tcp" and self._config["role"] is "server":
					link,addr = self._config["socket"].accept()
					self.debug("Accepted TCP connection from "+addr[0]+":"+str(addr[1])+" at "+self._config["host"]+":"+str(self._config["port"])+".")
					data = dict( [(x,y) for x,y in self._config.items() if x not in ("ready","active","socket","link")] );
					data["name"]+=" - "+data["host"]+":"+str(data["port"]);
					data["parent"]=self; data["host"]=addr[0]; data["port"]=addr[1]; data["role"]="client";
					self._config["clients"] = True;
					self._config["link"].append( Connection(data,link) )
				elif self._config["type"] is "tcp" and self._config["role"] is "client":
					try: data = self._config["socket"].recv( self._config["buffer"] )
					except socket.error, e:
						if e.errno==10054: raise ConnectionError(self._config["name"],6,"The connection has been terminated by the remote host "+self._config["host"]+":"+str(self._config["port"])+".")
					if not data: break
					if type(self._config["args"]) is dict and ("binary" not in self._config["args"] or self._config["args"]["binary"] is False):
						self.debug("Recieved data from TCP connection "+self._config["host"]+":"+str(self._config["port"])+" : "+data)
					self._config["args"] = self._config["handler"]( data , self._config["info"] , self._config["args"] );
				elif self._config["type"] is "udp" and self._config["role"] is "server":
					data,addr = self._config["socket"].recvfrom( self._config["buffer"] )
					self.debug("Accepted UDP data from "+addr[0]+":"+str(addr[1])+" : "+data)
					self.spawn(self.info()+" Handler", self._config["handler"], ( data , { "host":addr[0], "port":addr[1] } , self._config["args"] ) );
		except ConnectionError, e: pass
		self._config["active"] = False
		self._config["socket"].close()
		if self._config["type"] is "tcp" and self._config["role"] is "client":
			self._config["handler"]( None, self._config["info"], self._config["args"] )
		self.debug("Terminated connection at "+self._config["host"]+":"+str(self._config["port"])+".")
		return self
	
	def setup(self):
		"Initiate the connection and starts listening for data sent by the remote host."
		if self._config["active"]: return self
		self.initiate()
		if self._config["active"]: self._config["thread"] = self.spawn(self.info(),self.loop)
		return self
	
	def close(self): # Terminates the connection.
		if self._config["active"]:
			while("link" in self._config and len(self._config["link"])>0): self._config["link"][0].close() # Terminate all spawned connections.
			self._config["active"] = False # Disable the main loop
			if self._config["thread"].isAlive(): self._config["thread"].join() # Wait till the current main loop cycle ends
			if self._config["parent"] is not None: self._config["parent"]._config["link"].remove(self) # Break link from parent to ensure destruction.
		return self

	def close_internal(self): # Exists so that it is possible to terminate the loop thread from inside itself
		self._config["active"] = False # Terminates main loop at the end of this cycle.
	
	def send(self,data):
		"Sends given data to the remote host."
		if len(data)==0: return
		if self._config["active"]:
			if self._config["role"] is "client":
				if self._config["type"] is "tcp":
					try: self._config["socket"].send(data)
					except socket.error, e:
						if e.errno==10054: raise ConnectionError(self._config["name"],6,"The connection has been terminated by the remote host "+self._config["host"]+":"+str(self._config["port"])+".")
				elif self._config["type"] is "udp": self._config["socket"].sendto(data, (self._config["host"],self._config["port"]) )
				if type(self._config["args"]) is dict and ("binary" not in self._config["args"] or self._config["args"]["binary"] is False):
					self.debug("Sent data to "+self._config["host"]+":"+str(self._config["port"])+" : "+data)
			else: self.debug("Could not send data as this is a Server : "+data)
		else: self.debug("Could not send data to "+self._config["host"]+":"+str(self._config["port"])+" as this connection is no longer active : "+data)
		return self
	
	def wait(self):
		"Suspends execution till the currently established connection terminated."
		self._config["thread"].join()
		return self
	
	def info(self):
		"Returns a string describing the connection."
		return self._config["type"].upper()+"-"+self._config["role"][0].upper()+self._config["role"][1:].lower()+" "+self._config["host"]+":"+str(self._config["port"])+" "+self._config["name"]

	def active(self):
		"Returns a boolean value indicating whether or not the current connection is active."
		return self._config["active"]
	
	def clients(self): # Returns whether or not this TCP server has actively connected clients.
		return self._config["clients"]
	
	def __str__(self):
		return "[Connection %s : %s %s at %s:%s]" % (self._config["name"],self._config["type"],self._config["role"],self._config["host"],self._config["port"])
		
if __name__=="__main__":
	def tcpc(data,info,args):
		if data is not None: print "Recieved Data :", data
	def udps(data,info,args):
		if data is not None: print data
	x = int(raw_input("Enter Connection Type (1=TCPS, 2=TCPC, 3=UDPS, 4=UDPC) : "))
	if x>0 and x<5:
		port = raw_input("Enter the source/client port number : ")
	else:
		#port1 = raw_input("Enter server port number : ")
		#port2 = raw_input("Enter client port number : ")
		port1,port2 = 81,80
	debug = sys.stdout
	try:
		if x==1:
			c = Connection({"name":"TCPS","host":"localhost","port":port,"role":"server","type":"tcp","handler":tcpc,"debug":debug}).wait()
		elif x==2:
			c = Connection({"name":"TCPC","host":"localhost","port":port,"role":"client","type":"tcp","handler":tcpc,"debug":debug})
			while c.active():
				print "Send Data :",
				c.send(raw_input()+"\n")
		elif x==3:
			c = Connection({"name":"UDPS","host":"localhost","port":port,"role":"server","handler":udps,"type":"udp"}).wait()
		elif x==4:
			c = Connection({"name":"UDPC","host":"localhost","port":port,"role":"client","type":"udp"})
			while c.active(): c.send(raw_input())
	except KeyboardInterrupt: c.close()
