




  """
  #since all stop IDs are unique, just subtract 1000 to get index number???
  start with array of size at least all possible stops
  loop through trip, add stop_time_update.arrival & stop_time_update.route_id to corresponding stop index found with stop_time_update.stop_id 
  find vehicle by matching trip_id, and update the right index stop_id with next bus next stop sequence (optional really)

 OLD CODE FOR FIND_NEXT_BUS
, TransitVehicle(vehicle_on_trip[0], 
																																							   ct_id, 
																																							   vehicle_on_trip[2], 
																																							   vehicle_on_trip[4], 
																																							   vehicle_on_trip[3]))) 
  for t_ent in trip_feed.entity: #exclude header from GTFS dataset from data
	if t_ent.HasField('trip_update'):
	  for st_update in t_ent.trip_update.stop_time_update:
		if st_update.stop_id == str(stop_id_num):
		  print("same stop id!------------------------------------------------!----------")
		  for v_ent in vehicle_feed.entity:
			if v_ent.HasField('vehicle') and v_ent.vehicle.HasField("trip") and (v_ent.vehicle.trip.trip_id == t_ent.trip_update.trip.trip_id):
			  print("found a bus! " + v_ent.vehicle.trip.route_id)
			  return "The next bus is bus #%s arriving at stop #%d in %s" % (v_ent.vehicle.trip.route_id, stop_id_num, time_from_now(int(st_update.arrival.time)))
  return "I couldn't find a bus! There must have been a mistake in the stop number, or there are no more buses arriving :o" #no search results found matching route/stop id
"""
"""
TripUpdate
trip {
  trip_id
  start_time
  start_date
  route_id
}
stop_time_update {
  stop_sequence:
  arrival {
	time
  departure {
	time
  stop_id: "ACTUALLY DISPLAYED ON SIGN AND WEBSITE"
  schedule_relationship: SCHEDULED (usually)
}
delay OPTIONAL {
  
}
STOP_TIME_UPDATE REPEATED





Vehicle
trip {
  trip_id
  start_time
  start_date
  route_id
}
position {
  latitude
  longitude
}
current_stop_sequence: RELATED TO TRIPUPDATE STOP_SEQUENCE
current_status:
vehicle {
  id:
} """

