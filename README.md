# FATN_to_USB
Farnham and Alton Talking News (FATN)  is a volunteer service which provides a service for blind and partially sighted by reading local newspapers and providing the recordings via USB.  Recently they have been unable to send the USBs by post, so they publish the files on their website :https://www.fatntalkingnews.org.uk/
The scripts here are intended to be run on a computer with python3 support - specifically aimed at a Raspberry PI zero, with optional piaudio lineout "hat".  Where mentioned below, the RPi Zero could be any computer.

The aim is to provide a cheep to make solution that can be used by anyone and "Just works".  This assumes the following:

A internet connection is available, with WIFI
The RPi zero configured to connect to users WIFI
A spare USB
OPTIONAL: powered speaker/bluetooth speaker

The expected use case is that the RPi Zero will be able to
1.  Determine when the USB is plugged in
2.  Download the latest FATN zip file when available
3.  Provide indication that a new FATN recording is available
4.  Automatically update the content of the USB with the uncomppressed contents of the FATN zip file
5.  Provide indication that the USB has the new files loaded
6.  Provide indication that the USB can be safely removed.

The first and last could be that the USB is plugged in when the power is applied and it shuts down when complete.

