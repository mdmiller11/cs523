import picamera.array
import logging
import numpy as np
import signal
from picamera import PiCamera
from time import sleep
import datetime
from pusher import Pusher

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("capture_motion")

pusher_app_id = '568536'
pusher_key = '3fd4f1d2359eef671c1c'
pusher_secret = 'a34d43be28b5322a7d9d'
#Replace hostname each time program is run.
hostname =  'https://45dce350.ngrok.io'

camera = PiCamera()

pusher = Pusher(pusher_app_id, pusher_key, pusher_secret)

def signal_term_handler(signal, frame):
  LOG.info('shutting down ...')
  sys.exit(0)
  
signal.signal(signal.SIGTERM, signal_term_handler)

minimum_still_interval = 5
motion_detected = False
last_still_capture_time = datetime.datetime.now()

class DetectMotion(picamera.array.PiMotionAnalysis):
  def analyse(self, a):
    global minimum_still_interval, motion_detected, last_still_capture_time
    if datetime.datetime.now() > last_still_capture_time + \
        datetime.timedelta(seconds=minimum_still_interval):
      a = np.sqrt(
        np.square(a['x'].astype(np.float)) +
        np.square(a['y'].astype(np.float))
      ).clip(0, 255).astype(np.uint8)
      
      if (a > 75).sum() > 10:
        LOG.info('motion detected at: %s' % datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f'))
        motion_detected = True




with DetectMotion(camera) as output:
    try:
        camera.resolution = (640, 480)
        camera.rotation = 180
        camera.framerate= 10
        camera.start_recording('/dev/null', format='h264', motion_output=output)
        while True:
            while not motion_detected:
                LOG.info('waiting for motion...')
                camera.wait_recording(1)

            LOG.info('stop recording and capture an image...')
            camera.stop_recording()
            motion_detected = False
      
            date = datetime.datetime.now().strftime('%m-%d-%Y-%H:%M:%S')
            camera.annotate_text = date
            filename = '/photos/' + date + '.jpg'
            camera.capture('/var/www/html' + filename)
            url = hostname + filename
            pusher.trigger('photos', 'new_photo', {'url': url}) 
            camera.start_recording('/dev/null', format='h264', motion_output=output)

    except KeyboardInterrupt as e:
        LOG.info("\nreceived KeyboardInterrupt via Ctrl-C")
        pass
    finally:
        camera.close()
        LOG.info("\ncamera turned off!")
        LOG.info("detect motion has ended.\n")

