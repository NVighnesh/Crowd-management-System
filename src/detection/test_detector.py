import cv2

from src.detection.ultralytics_detector import UltralyticsPersonDetector


detector = UltralyticsPersonDetector(
    model_path="yolo26n.pt",
    confidence=0.35,
    image_size=640,
    device="auto",
)

cap = cv2.VideoCapture("videos/crowd.mp4")

if not cap.isOpened():
    print("Could not open video.")
    raise SystemExit

ret, frame = cap.read()

if not ret:
    print("Could not read frame.")
    cap.release()
    raise SystemExit

detections = detector.infer(frame)

print(f"People detected: {len(detections)}")

for detection in detections:
    print(detection)

cap.release()