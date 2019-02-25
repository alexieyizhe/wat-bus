# WATBus

#### NOTE: This project is being actively ported over to JavaScript. Please check out the `develop` branch for the latest version.

### About
WATBus(shouldItake?) is a convenient way to access information about Grand River Transit's bus service (with possible support for ION Rail, if Bombardier delivers the first working train in 50 years).

This Facebook Messenger bot will put helpful info like route times, next bus arrival times, and even reminders to leave and get off at a stop, right into one of the most commonly used apps in the world: Facebook Messenger. You'll no longer have to switch apps and refresh constantly in fear of missing your bus or even catching the wrong one!

It's hosted on Heroku, using Python and a Flask webhook to allow users to message it for information about bus routes, closest stops, using natural language processing and more - all inside the popular Messenger app.

### DOCUMENTATION:
https://developers.facebook.com/docs/messenger-platform/introduction
https://developers.facebook.com/docs/graph-api/webhooks/
http://www.grt.ca/en/about-grt/open-data.aspx
https://developers.google.com/transit/gtfs-realtime/

### RESOURCES (that I found helpful):
https://ains.co/blog/things-which-arent-magic-flask-part-1.html
https://github.com/google/transitfeed/wiki/TransitFeed
