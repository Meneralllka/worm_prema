import cv2
import numpy as np
import math
import csv

# Initialize Webcam / Video
fileName = "Tail"
cap = cv2.VideoCapture("D:\\PREMALab\\Mass-Shift\\Code\\Python\\TankVids\\"+fileName+".mp4")

# HSV bounds
lower_bound = np.array([35, 40, 40])
upper_bound = np.array([60, 238, 212])

# Kernels
open_kernel = np.ones((5, 5), np.uint8)
close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 35))

# --- Window Setup ---
cv2.namedWindow("Tracking Result", cv2.WINDOW_NORMAL)
cv2.namedWindow("Cleaned Mask", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Tracking Result", 1080, 720)
cv2.resizeWindow("Cleaned Mask", 1080, 720)

# --- TRACKING & LOGGING VARIABLES ---
tracked_objects = {}
next_object_id = 0
frame_count = 0

# --- CSV Setup ---
# Open the CSV file in write mode
csv_file = open('TankVids/'+fileName+'.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
# Write the header row
csv_writer.writerow(['Frame', 'ID', 'Center_X', 'Center_Y'])

print("Press 'q' to quit.")

while True:
    success, img = cap.read()
    if not success:
        print("End of video stream.")
        break

    frame_count += 1

    # 1. Image Processing
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    raw_mask = cv2.inRange(imgHSV, lower_bound, upper_bound)
    opened_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, open_kernel)
    clean_mask = cv2.morphologyEx(opened_mask, cv2.MORPH_CLOSE, close_kernel)

    # 2. Find Contours
    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Temporary list to hold data before sorting
    frame_data = []

    for cnt in contours:
        if cv2.contourArea(cnt) > 1000:
            x, y, w, h = cv2.boundingRect(cnt)
            cx = x + (w // 2)
            cy = y + (h // 2)

            frame_data.append({'box': (x, y, w, h), 'center': (cx, cy)})

    # --- SORT LEFT TO RIGHT ---
    # Sort the detected objects based on their X-coordinate (cx)
    frame_data.sort(key=lambda item: item['center'][0])

    # Extract the sorted centers and boxes
    current_frame_centers = [item['center'] for item in frame_data]
    current_frame_boxes = [item['box'] for item in frame_data]

    # 3. CENTROID TRACKING LOGIC
    new_tracked_objects = {}

    unmatched_centers = current_frame_centers.copy()
    unmatched_boxes = current_frame_boxes.copy()

    # Step A: Try to match existing IDs to the new centers
    for obj_id, (prev_cx, prev_cy) in tracked_objects.items():
        matched_index = None
        min_distance = float('inf')

        for i, (cx, cy) in enumerate(unmatched_centers):
            distance = math.hypot(cx - prev_cx, cy - prev_cy)

            if distance < 100 and distance < min_distance:
                min_distance = distance
                matched_index = i

        if matched_index is not None:
            new_cx, new_cy = unmatched_centers[matched_index]
            box = unmatched_boxes[matched_index]

            new_tracked_objects[obj_id] = (new_cx, new_cy)

            cv2.rectangle(img, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 0, 255), 3)
            cv2.circle(img, (new_cx, new_cy), 6, (0, 255, 0), -1)
            cv2.putText(img, f"ID: {obj_id}", (box[0], box[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            unmatched_centers.pop(matched_index)
            unmatched_boxes.pop(matched_index)

    # Step B: Register leftover unmatched centers as brand new objects
    # Because they were sorted left-to-right earlier, ID assignment will happen left-to-right here!
    for i, (cx, cy) in enumerate(unmatched_centers):
        new_tracked_objects[next_object_id] = (cx, cy)
        box = unmatched_boxes[i]

        cv2.rectangle(img, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 0, 255), 3)
        cv2.circle(img, (cx, cy), 6, (0, 255, 0), -1)
        cv2.putText(img, f"ID: {next_object_id}", (box[0], box[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        next_object_id += 1

    # Update our global tracker
    tracked_objects = new_tracked_objects

    # --- RECORD DATA TO CSV ---
    # Log the confirmed positions for this specific frame
    for obj_id, (cx, cy) in tracked_objects.items():
        csv_writer.writerow([frame_count, obj_id, cx, cy])

    # 4. Display the windows
    cv2.imshow("Tracking Result", img)
    cv2.imshow("Cleaned Mask", clean_mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()
csv_file.close()  # Make sure to close the CSV file and save the data
print("Data successfully saved to "+fileName+".csv")