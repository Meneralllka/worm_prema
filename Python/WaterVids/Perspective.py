"""import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog


def main():
    # 1. Initialize Tkinter and hide the root window
    root = tk.Tk()
    root.withdraw()

    # 2. Open file dialog to select the video
    video_path = filedialog.askopenfilename(
        title="Select Video to Transform",
        filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")]
    )

    if not video_path:
        print("No video selected. Exiting.")
        return

    # 3. Open the video and read properties
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Read the first frame for point selection
    ret, first_frame = cap.read()
    if not ret:
        print("Error: Could not read the first frame.")
        return

    # 4. Interactive point selection
    points = []

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) < 4:
                points.append((x, y))
                cv2.circle(display_frame, (x, y), 5, (0, 255, 0), -1)

                # Draw lines between points
                if len(points) > 1:
                    cv2.line(display_frame, points[-2], points[-1], (0, 255, 0), 2)
                # Close the polygon on the 4th click
                if len(points) == 4:
                    cv2.line(display_frame, points[-1], points[0], (0, 255, 0), 2)
                    print("\n4 points selected. Press any key to start processing.")

                cv2.imshow("Select 4 Points", display_frame)

    display_frame = first_frame.copy()
    cv2.namedWindow("Select 4 Points", cv2.WINDOW_NORMAL)
    cv2.imshow("Select 4 Points", display_frame)
    cv2.setMouseCallback("Select 4 Points", mouse_callback)

    print("Please click 4 points on the video frame.")
    print("IMPORTANT: Click in this exact order -> Top-Left, Top-Right, Bottom-Right, Bottom-Left.")

    # Wait until 4 points are selected and a key is pressed
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    if len(points) != 4:
        print("Error: You must select exactly 4 points. Exiting.")
        return

    # 5. Calculate Perspective Transformation Matrix
    src_pts = np.float32(points)
    # Map the selected polygon to the full frame resolution
    dst_pts = np.float32([[0, 0], [0, height], [width, height], [width, 0]] )

    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # 6. Set up output paths
    dir_name = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]

    out_video_path = os.path.join(dir_name, f"{base_name}_warped.mp4")
    out_matrix_path = os.path.join(dir_name, f"{base_name}_matrix.npy")

    # 7. Initialize VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_video_path, fourcc, fps, (width, height))

    # Reset video capture to the first frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    print("\nProcessing video... This may take a moment.")

    frame_count = 0
    #while True:
    for x in range(100):
        ret, frame = cap.read()
        if not ret:
            break

        # Apply the transformation matrix to the current frame
        warped_frame = cv2.warpPerspective(frame, matrix, (width, height))
        out.write(warped_frame)

        frame_count += 1
        if frame_count % 100 == 0:
            print(f"Processed {frame_count}/{total_frames} frames...")

    # 8. Clean up and save the matrix
    cap.release()
    out.release()

    np.save(out_matrix_path, matrix)

    print("\n--- Processing Complete ---")
    print(f"Saved warped video to: {out_video_path}")
    print(f"Saved transformation matrix to: {out_matrix_path}")


if __name__ == "__main__":
    main()
"""
import pandas as pd
import numpy as np
import cv2
import os
import glob
import tkinter as tk
from tkinter import filedialog

def main():
    # 1. Initialize Tkinter and hide the root window
    root = tk.Tk()
    root.withdraw()

    # 2. Select the Folder containing the CSV files
    print("Please select the folder containing your CSV data files...")
    folder_path = filedialog.askdirectory(
        title="Select Folder Containing CSV Files"
    )
    if not folder_path:
        print("No folder selected. Exiting.")
        return

    # 3. Select the Matrix file
    print("Please select your Transformation Matrix (.npy)...")
    matrix_path = filedialog.askopenfilename(
        title="Select the Transformation Matrix (.npy)",
        filetypes=[("Numpy Files", "*.npy"), ("All Files", "*.*")]
    )
    if not matrix_path:
        print("No matrix file selected. Exiting.")
        return

    print("\nLoading matrix...")
    try:
        matrix = np.load(matrix_path)
    except Exception as e:
        print(f"Error reading matrix: {e}")
        return

    # 4. Find all CSV files in the folder
    # We ignore files that already end in "_warped.csv" to prevent double-processing
    search_pattern = os.path.join(folder_path, "*.csv")
    csv_files = glob.glob(search_pattern)
    csv_files = [f for f in csv_files if not f.endswith("_warped.csv")]

    if not csv_files:
        print("No valid CSV files found in the selected folder to process.")
        return

    print(f"\nFound {len(csv_files)} CSV files. Processing data...")

    # 5. Loop through and process each CSV file
    for csv_path in csv_files:
        file_name = os.path.basename(csv_path)
        print(f"Processing: {file_name}")

        try:
            df = pd.read_csv(csv_path, sep=';', decimal=',')
        except Exception as e:
            print(f"  -> Error reading {file_name}: {e}")
            continue

        # Ensure X and Y columns exist
        if 'Trajectory 1/0/X' not in df.columns or 'Trajectory 1/0/Y' not in df.columns:
            print(f"  -> Error: {file_name} does not contain 'X' and 'Y' columns. Skipping.")
            continue

        # Format points for OpenCV
        points = df[['Trajectory 1/0/X', 'Trajectory 1/0/Y']].values.astype(np.float32)
        points_reshaped = np.array([points])

        # Apply the perspective transformation
        transformed_points = cv2.perspectiveTransform(points_reshaped, matrix)
        transformed_points = transformed_points[0]

        # Update the DataFrame with new coordinates
        df['Transformed_X'] = transformed_points[:, 0]
        df['Transformed_Y'] = transformed_points[:, 1]

        # 6. Save the resulting data
        base_name = os.path.splitext(file_name)[0]
        out_csv_path = os.path.join(folder_path, f"{base_name}_warped.csv")

        # Save matching the original format (semicolon separator, comma decimals)
        df.to_csv(out_csv_path, sep=';', decimal=',', index=False)
        print(f"  -> Saved new data to: {os.path.basename(out_csv_path)}")

    print("\n--- Batch Transformation Complete ---")

if __name__ == "__main__":
    main()