"""WATBus(shoulditake?) is a Facebook Messenger Bot hosted on Heroku that uses Python and a Flask webhook to allow users to message it for
	   information about bus routes, closest stops, using natural language processing and more - all inside the popular Messenger app.

	All code implemented and written by Alex Yizhe Xie 2018
	Website: http://alexieyizhe.me/
	Github: https://github.com/alexieyizhe

	DOCUMENTATION:
	https://developers.facebook.com/docs/messenger-platform/introduction
	https://developers.facebook.com/docs/graph-api/webhooks/
	http://www.grt.ca/en/about-grt/open-data.aspx
	https://developers.google.com/transit/gtfs-realtime/

	RESOURCES (that I found helpful):
	https://ains.co/blog/things-which-arent-magic-flask-part-1.html
	https://github.com/google/transitfeed/wiki/TransitFeed
	"""

from flask import Flask, request
from google.transit import gtfs_realtime_pb2
from geopy.distance import vincenty
from geopy.geocoders import Nominatim
import json
import requests
import time

#------------------------------------------------------------VARIABLE DECLARATIONS ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
app = Flask(__name__)
geolocator = Nominatim(scheme = "http") #Nominatim allows translation of address strings into location objects
PAT = 'EAAbZBzJtVokYBAEgDPK1pYhGkYyHxIOSAZA1pBWQrWyklrWqF5KdNUnyQzZAnT0ZBygkGR3RcNrENbYnSZBM7g52TZBdYfeEwRx4vKR9Ga2L9ef6OBDmc5UGqfThHEDLYHG6Ju170RU2CvHMTtKCDwAXmSTmGX9D4eGIZBXou7qwZAOFZBhFOaQsD' #facebook page authorization token
all_stops =dict()
all_vehicles = dict()
test_reminder_time = 5 #for testing reminder timing 

#------------------------------------------------------------CLASS DECLARATIONS FOR TRANSIT OBJECTS----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""a TransitStop class has information about a certain bus stop in the GRT system
    CONTAINS: stop_id: String | stop_name: String | location: [Float, Float] | route_services: [TransitRoutes,...]
    FUNCTIONS: add_route: inserts a TransitRoute into sorted chronological order (first in list arriving soonest)
    		   find_next_transit: finds the next TransitRoute either arriving soonest or matching a specific route_id, will return None if none are found
    		   update_transitstop: removes any TransitRoutes that have already departed the TransitStop"""
class TransitStop():
	def __init__(self, stop_id, stop_name, latitude, longitude):
		self.stop_id = stop_id 
		self.stop_name = stop_name
		self.location = [latitude, longitude]
		self.route_services = [] #route services contains all current TransitRoutes that pass through this stop

	def add_route(self, new_route): 
		nr_arrival_time = new_route.stop_arrival_time
		num_routes = len(self.route_services)
		ins_indx = 0 #where to insert new route
		#does python not have a do while loop? probably useful here
		#maybe implement a linkedlist so inserting it into the list is more efficient? just change previous node's pointer to new route and take the prev node's pointer to be this node's pointer
		while ins_indx <  num_routes and self.route_services[ins_indx].stop_arrival_time < nr_arrival_time:
			ins_indx += 1
		self.route_services.insert(ins_indx, new_route) #inserts new route into correct position based on chronological order

	def find_next_transit(self, route_id): #will return TransitRoute or None, always returns bus  arriving soonest since route_services is sorted
		if len(self.route_services) != 0: #stop has routes running through it
			if route_id:
				for indiv_route in self.route_services:
					print(indiv_route.route_id)
					print(route_id)
					if str(indiv_route.route_id) == str(route_id):
						return indiv_route
				return None
			return self.route_services[0]
		else:
			return None

	def update_transitstop(self):
		for indiv_route in self.route_services:
			if indiv_route.next_depart_time() < time.time() or indiv_route.a_vehicle.status != "SCHEDULED":
				self.route_services = [route for route in self.route_services if not indiv_route] #remove element from list without causing errors while iterating

"""a TransitRoute class has information about routes operating in the GRT bus system
    CONTAINS: route_id: String | stop_arrival_time: Int | stop_depart_time: Int"""
class TransitRoute(): # a TransitRoute has a route_id, the arrival time at the stop, and departing time from the stop
	def __init__(self, route_id, stop_arrival_time, stop_depart_time):
		self.route_id = route_id
		self.stop_arrival_time = stop_arrival_time
		self.stop_depart_time = stop_depart_time

"""a TransitRoute class has information about individual vehicles operating routes in the GRT bus system
    CONTAINS: vehicle_id: String | trip_id: String | cur_stop_seq: Int | position: [Float, Float] | status: String
    FUNCTIONS: update_status: updates the status of the current vehicle
    		   update_pos: updates the position of the current vehicle
    		   update_next_stop: changes the sequence (route) of the current vehicle """
class TransitVehicle():
	def __init__(self, vehicle_id, trip_id, cur_stop_seq, position, status):
		self.vehicle_id = vehicle_id
		self.trip_id = trip_id
		self.cur_stop_seq = cur_stop_seq
		self.position = position #2 elem list [latitude, longitude]
		self.status = status

	def update_status(self, new_status):
		self.status = new_status

	def update_pos(self, new_pos):
		self.position = new_pos

	def update_next_stop(self, new_seq):
		self.cur_stop_seq = new_seq


#------------------------------------------------------------INTERACTIONS WITH FB/FLASK WEBHOOK CODE--------------------------------------------------------------------------------------------------------------
@app.route('/', methods = ['GET']) #flask default path with GET method to request verification code from the FB servers
def handle_verification():
	print("Handling Verification...")
	if request.args.get('hub.verify_token', '') == 'verify_or_(bus)t': #hub,verify_token is sent by FB and generated when we created the webhook
		print("Verification successful!")
		return request.args.get('hub.challenge', '') #return hub.challenge value to FB to verify response 
	else:
		print("Verification failed!")
		return 'Error, wrong validation token'


@app.route('/', methods = ['POST'])
def handle_messages():
	
	print("Creating Database...")
	
	create_transitstops() #this is inefficient; look into creating TransitStops once every day and just updating the existing TransitStop database instead of overwriting it
	parse_vehicle_trip_data() 
	populate_transitstops()

	print("Handling Messages")
	payload = request.get_data()
	print(payload) #for console troubleshooting/logging
	for sender, message in messaging_events(payload):
		print("Incoming from %s: %s" % (sender, message))
		send_message(PAT, sender, message)
	return "ok" #return HTTP 200 OK response to complete request update

def messaging_events(payload):
	data = json.loads(payload)
	messaging_events = data["entry"][0]["messaging"]
	response_text = "I don't understand that. Maybe try again with slightly different wording?" #default response if nothing of value can be interpreted from user's messages
	user_actions = {"find_next_bus()": find_next_bus, "set_reminder()": set_reminder, "find_transit_info_geo()":find_transit_info_geo} #all possible commands for the bot

	for event in messaging_events:
		sender_id = event["sender"]["id"]
		print("Event message: %s" % str(event))
		if "message" in event:
			message_contents = event["message"]
			if "nlp" in message_contents and len(message_contents["nlp"]["entities"]) != 0:
				nlp_data = message_contents["nlp"]["entities"]
				print(nlp_data)
				if "intent" in nlp_data:
					user_stop_id = nlp_data["stop_id"][0]["value"] if "stop_id" in nlp_data else None
					user_route_id = nlp_data["bus_route_id"][0]["value"] if "bus_route_id" in nlp_data else  None
					print(user_route_id)
					print(user_stop_id)
					user_remind_time = int(nlp_data["reminder_time"][0]["value"]) if "reminder_time" in nlp_data else None
					user_location = (find_user_loc(nlp_data["user_loc_str"][0]["value"]) if "user_loc_str" in nlp_data else None or find_user_loc(nlp_data["location"][0]["value"]) if "location" in nlp_data else None)
					response_text = user_actions[nlp_data["intent"][0]["value"]](str(user_stop_id), user_route_id, user_location, user_remind_time) #all strings
				if "thanks" in nlp_data:
					response_text = "You're welcome! Is there anything else I can help you with?"

			elif "attachments" in message_contents:
				for indiv_attach in message_contents["attachments"]:
					if "payload" in indiv_attach and "coordinates" in indiv_attach["payload"]:
						user_loc = indiv_attach["payload"]["coordinates"]
						print("Latitude: %3.5f \nLongitude: %3.5f" % (user_loc["lat"], user_loc["long"]))
						response_text = find_transit_info_geo(None, None, [user_loc["lat"], user_loc["long"]])
						#truncating to 5 decimal places gives accuracy of location up to error of 1.1m, according to https://en.wikipedia.org/wiki/Decimal_degrees

		yield sender_id, response_text.encode("unicode_escape") #encode contents to prevent incorrect/mistranslated responses


"""elif "text" in message_contents:
				if "next bus" in message_contents["text"]:
					print("User requested bus information")
					response_text = find_next_bus(filter_int(message_contents["text"]))
					print(response_text)
				elif "remind" in message_contents["text"]:
					print("User requested reminder")
					response_text = Got it! I'll message you %d minutes before the bus arrives to remind you not to miss it! 
							        NOTE: FEATURE STILL UNDER CONSTRUCTION % filter_int(message_contents["text"])"""
"""Send the message text to recipient with id recipient.
  """
def send_message(token, recipient, text):
	r = requests.post("https://graph.facebook.com/v2.6/me/messages", 
		params = {"access_token": token}, 
		data = json.dumps({"recipient": {"id": recipient}, "message": {"text": text.decode('unicode_escape')}}),
		headers = {'Content-type': 'application/json'})
	if r.status_code != requests.codes.ok:
		print(r.text)



#------------------------------------------------------------GRT API/FEATURE CODE------------------------------------------------------------------------------------------------------------------
""" filter_int() parses a string containing any type of character into an integer
     FILTER_INT: String --> Integer """
def filter_int(msg_str):
	return int(''.join(list(filter(str.isdigit, msg_str))))

"""find_user_loc() converts an address_str into the best interpretation of latitude & longitude coordinates according to Geopy's Nominatim object
     FIND_USER_LOC: String --> anyof([Float, Float], None)
     Requires: address_str is a valid address (otherwise it returns None)"""
def find_user_loc(address_str):
	cur_location = geolocator.geocode(address_str)
	try:
		lat_long = [cur_location.latitude, cur_location.longitude]
		return lat_long
	except (TypeError, AttributeError) as e:
		print("No valid latitude/longitude was found!")
		return None

"""closest_stop() finds the closest GRT TransitStop and its distance from the user_loc(ation)
    CLOSEST_STOP: [Float, Float] -> [TransitStop, Float]
    Requires: ideally user should be located in or near Waterloo (otherwise you get some wild results)"""
def closest_stop(user_loc):
	stop_lst = list(all_stops.values())
	closest = stop_lst[0]
	closest_dist = vincenty(user_loc, closest.location).meters
	for tstop in stop_lst:
		cur_dist = vincenty(user_loc, tstop.location).meters
		print(cur_dist)
		print("Closest so far: " + str(closest.stop_id))
		if cur_dist < closest_dist:
			closest_dist = cur_dist
			closest = tstop
	return  [closest, closest_dist]
	

"""time_from_now() returns the difference in time in HH:MM::SS format between any unix_time and the current time 
     TIME_FROM_NOW: Int -> {String:Int, String:Int. String:Int}
     Requires: unix_time >= current time (otherwise it returns 0)"""
def time_from_now(unix_time): 
	cur_time = time.time() #current epoch time 
	if unix_time - cur_time < 0:
		print("current time: %d arrival_time %d negative time: %d" % (cur_time, unix_time, unix_time - cur_time)) #for testing purposes
	time_diff = max(0, unix_time - cur_time) #time difference in seconds, prevents negative time
	hours = time_diff // 3600
	minutes = time_diff // 60 % 60
	seconds = time_diff % 60

	return {"hrs":hours, "mins":minutes, "secs":seconds}

"""generate_next_bus_string() creates a formatted string of user requested transit information that can be displayed to the user
    GENERATE_NEXT_BUS_STRING: String TransitRoute Bool --> String
    Requires: stop_id exists inside all_stops"""
def generate_next_bus_string(stop_id, next_bus, required_specific_route):
	eta = time_from_now(int(next_bus.stop_arrival_time))
	start_phrase = (("The next bus #%s will arrive at stop #%s (%s) in " % (next_bus.route_id, stop_id, all_stops[stop_id].stop_name)) if required_specific_route else "The next bus at stop #%s (%s) is bus #%s arriving in " % (stop_id, all_stops[stop_id].stop_name, next_bus.route_id))
	#highest delay should be hours, otherwise bus system has completely and catastrophically failed 
	hour_phrase = ("%d hour%s%s" % (eta["hrs"], ("s" if eta["hrs"] > 1 else ""), (" and " if (eta["mins"] or eta["secs"]) else ".")))
	min_phrase = ("%d minute%s%s" % (eta["mins"], ("s" if eta["mins"] > 1 else ""), (" and " if eta["secs"] else ".")))
	sec_phrase = ("%d second%s." % (eta["secs"], ("s" if eta["secs"] > 1 else "")))
	complete_time = ("""%s%s%s%s%s""" % (start_phrase, (hour_phrase if eta["hrs"] else ""), (min_phrase if eta["mins"] else ""), (sec_phrase if eta["secs"] else ""), (" Better hurry up!" if eta["mins"] <= 1 else "")))
	
	if eta["hrs"] or eta["mins"] or eta["secs"]:
		return complete_time 
	return "The bus should be arriving right now! Look out for it!" #time is 0 seconds or less till arrival
	

# FIND_NEXT_BUS: String String [Float, Float] Int --> String
def find_next_bus(stop_id, specific_route = None, user_loc = None, time_prior = None):
	try:
		corres_stop = all_stops.get(stop_id)
		print("Getting stop #" + str(corres_stop.stop_id))
		print(corres_stop.route_services)
		corres_route = corres_stop.find_next_transit(specific_route)
		if corres_route == None:
			raise TypeError("No bus found")
		return generate_next_bus_string(stop_id, corres_route, (True if specific_route else False))
	except (TypeError, AttributeError) as e:
		print("Error searching for bus: %s" % (str(e))) #for testing
		return "I couldn't find a bus for that stop! There must have been a mistake in the stop number, the route number, or there are no more buses running :o" #no search results found matching route/stop id 

# FIND_NEXT_BUS: String String [Float, Float] Int --> String
def find_transit_info_geo(stop_id_num, specific_route, user_loc, time_prior = None):
	if user_loc == None:
		return "Something went wrong! It's probably an invalid address, or I'm out of it today. You should try again with different wording or a different address!"

	closest_transitstop = closest_stop(user_loc)
	stop_info = "Your closest bus stop is stop #%s (%s), about %d meters away." % (closest_transitstop[0].stop_id, closest_transitstop[0].stop_name, closest_transitstop[1])
	bus_at_stop_info = find_next_bus(closest_transitstop[0].stop_id, specific_route)
	return "%s\n%s" % (stop_info, bus_at_stop_info)

"""set_reminder() allows the user to set a reminder to be alerted time_prior minutes before a specific_route arrives at stop #stop_id_num
     SET_REMINDER: String String [Float, Float] Int --> String"""
def set_reminder(stop_id_num, specific_route = None, user_loc = None, time_prior = test_reminder_time):
	return ("""Got it! I'll message you %s minutes before bus #%s arrives at stop #%s to remind you not to miss it! 
		   NOTE: This feature is still under construction. Reminders may or may not be sent as of Feb 17, 2018.""" % time_prior, specific_route, stop_id_num)			


"""create_transitstops() creates a dictionary of all operating bus stops to populate with information later on
     CREATE_TRANSITSTOPS: Void -> Void
     Effects: creates TransitStops in all_stops dictionary
     Requires: valid stops.txt static data file inside directory"""
def create_transitstops():
	with open("GRT_static_info/stops.txt") as all_stops_file:
		all_stops_file.readline() #discards first line, which contains index references
		stop_info = all_stops_file.readline().split(",")
		while stop_info[0].isdigit(): #only populates stops that have stop_ids, working to implement landmark transit stop population
			if (int(stop_info[0]) % 100) == 0: #FOR TESTING
				print("Creating TransitStop ... %d%% complete ..." % (int(stop_info[0]) // 100))
			all_stops[stop_info[0]] = TransitStop(stop_info[0], stop_info[2], stop_info[4], stop_info[5])
			stop_info = all_stops_file.readline().split(",")
	all_stops_file.close()
	print("The number of stops found is " + str(len(all_stops))) #TESTING 

"""parse_vehicle_trip_data() interprets all the relevant infomation of vehicles moving in the transit system
     PARSE_VEHICLE_TRIP_DATA: Void -> Void
     Effects: fills all_vehicle dictionary
     Requires: valid GTFS ProtoBuf data read in from the GET request """
def parse_vehicle_trip_data():
	try:
		vehicle_feed = gtfs_realtime_pb2.FeedMessage()
		vehicle_server_response = requests.get('http://192.237.29.212:8080/gtfsrealtime/VehiclePositions')
		vehicle_feed.ParseFromString(vehicle_server_response.content)
	except AttributeError as ae:
		print("Error parsing vehicle data: %s" % ae)
		return None

	#O(n) efficiency for populationg dictionaries, O(1) efficiency during lookup!
	for v_ent in vehicle_feed.entity: #strip header from data
		if v_ent.HasField("vehicle"):
			cur_vehicle = v_ent.vehicle
			all_vehicles[cur_vehicle.trip.trip_id] = [cur_vehicle.vehicle.id, 
								   cur_vehicle.trip.route_id, 
								   cur_vehicle.current_stop_sequence, 
								   cur_vehicle.current_status, 
								   cur_vehicle.position]

"""populate_transitstops() adds all the relevant information a user might need to the right TransitStop inside all_stops
    POPULATE_TRANSITSTOPS: Void -> Void
    Effects: fills all_stops dictionary
    Requires: a corresponding transit stop ID exists inside all_stops
                     valid GTFS ProtoBuf data read in from the GET request   """
def populate_transitstops():
	try:
		trip_feed = gtfs_realtime_pb2.FeedMessage()
		trip_server_response = requests.get('http://192.237.29.212:8080/gtfsrealtime/TripUpdates')
		trip_feed.ParseFromString(trip_server_response.content)
	except AttributeError as ae:
		print("Error parsing trip data: %s" % ae)
		return None

	#O(n) efficiency for updating TransitStops with realtime data
	for t_ent in trip_feed.entity: #
		if t_ent.HasField("trip_update"):
			cur_trip = t_ent.trip_update
			ct_id = cur_trip.trip.trip_id
			cur_route_id = cur_trip.trip.route_id
			
			#vehicle_on_trip = vehicle_dict[ct_id] #vehicle currently progressing through this unique trip ID (PROBLEM: NOT ALL TRIPS HAVE VEHICLES WITH SAME TRIP IDs)
			for st_update in cur_trip.stop_time_update:
				if  not st_update.schedule_relationship: #0 means trip is SCHEDULED, only scheduled trips occur
					if (int(st_update.stop_id) % 500) == 0: #FOR TESTING
						print("Populating TransitStop %s ..." % st_update.stop_id)
					new_corres_route = TransitRoute(cur_route_id, st_update.arrival.time, st_update.departure.time)
					try:
						all_stops[st_update.stop_id].add_route(new_corres_route)
					except KeyError:
						print("Whoops! Stop #%s wasn't found in the database." % (st_update.stop_id))




#------------------------------------------------------------EXECUTION CODE-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
  app.run()