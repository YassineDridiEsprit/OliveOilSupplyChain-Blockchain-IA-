from deep_sort_realtime.deepsort_tracker import DeepSort
from ultralytics import YOLO
import cv2
import os 


#####################################

          # Visualizations

#####################################

def get_bbox(path):
  bb_locations = []

  with open(path ,'r') as labels :
    lines = labels.readlines()

    for line in lines :
      cols = line.split()

      cols=list(map(float ,cols))
      bb_locations.append(cols[1:])

  return bb_locations

def drw_bbox(img_pth ,label_pth ,color=(0,255,0) ,thikness=3):
  bb_locations = get_bbox(label_pth)
  np_img = cv2.imread(img_pth)
  np_img = cv2.cvtColor(np_img ,cv2.COLOR_BGR2RGB)

  IMG_H = np_img.shape[0]
  IMG_W = np_img.shape[1]

  for bb_location in bb_locations :
    x,y,w,h = bb_location
    xc = int(x*IMG_W)
    yc = int(y*IMG_H)
    w = int(w*IMG_W)
    h = int(h*IMG_H)
    x ,y = (xc - w//2) ,(yc - h//2)

    cv2.rectangle(np_img ,(x,y) ,(x+w ,y+h) ,color ,thikness)

  return np_img

##########################################

                # Tracking and Detections

##########################################

class Detector :

  def __init__(self ,model_path ,confidence):

    self.model = YOLO(model_path)
    self.classList = ['olive' ,]
    self.confidence = confidence

  def detect(self ,image) :
    results = self.model(image ,conf=self.confidence)
    result = results[0]
    detections = self.make_detections(result)
    return detections

  def make_detections(self, result):
    boxes = result.boxes
    detections = []

    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    clss = boxes.cls.cpu().numpy()
    
    for (x1, y1, x2, y2), conf, cls in zip(xyxy, confs, clss):
        cls_number = int(cls)
        if result.names[cls_number] not in self.classList:
            continue

        w, h = x2 - x1, y2 - y1
        detections.append(([x1, y1, w, h], cls_number, conf))

    return detections

  

class Tracker :

  def __init__(self ,max_age=256):
    self.object_tracker = DeepSort(max_age=max_age)

  def track(self ,detections ,frame):
    tracks = self.object_tracker.update_tracks(detections ,frame=frame)

    tracking_ids = set()
    boxes = []
    for track in tracks :
      if not track.is_confirmed() :
        continue
      tracking_ids.add(track.track_id)
      ltrb = track.to_ltrb()
      boxes.append(ltrb)

    return tracking_ids ,boxes





