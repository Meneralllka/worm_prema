import cv2
import os


def extract_frames_from_folder():
    # Configuration
    input_folder = "D:\PREMALab\Mass-Shift\Code\Python\MultiTerr\Vids\\tobreak"
    output_base = "D:\PREMALab\Mass-Shift\Code\Python\MultiTerr\Vids\\tobreak\\output_frames"
    valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv')

    # Ensure the input directory exists
    if not os.path.exists(input_folder):
        print(f"Error: The folder '{input_folder}' was not found.")
        return

    # Create the main output directory
    if not os.path.exists(output_base):
        os.makedirs(output_base)

    # Filter for video files inside the 'vids' folder
    video_files = [f for f in os.listdir(input_folder) if f.lower().endswith(valid_extensions)]

    if not video_files:
        print(f"No valid videos found in '{input_folder}'.")
        return

    for video_file in video_files:
        # Full path to the video source
        video_path = os.path.join(input_folder, video_file)

        # Create a subfolder for this specific video
        video_name = os.path.splitext(video_file)[0]
        save_path = os.path.join(output_base, video_name)

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # Start OpenCV capture
        cap = cv2.VideoCapture(video_path)
        frame_count = 0

        print(f"Processing: {video_file}...")

        while True:
            success, frame = cap.read()
            if not success:
                break

            # Construct frame filename (e.g., vids/output_frames/my_video/frame_00001.jpg)
            file_name = f"frame_{frame_count:05d}.png"
            full_frame_path = os.path.join(save_path, file_name)

            # Save the image
            if frame_count % 10 == 0:
                cv2.imwrite(full_frame_path, frame)
            frame_count += 1

        cap.release()
        print(f"Done. Extracted {frame_count} frames to: {save_path}")

    print("\nAll videos processed successfully.")


if __name__ == "__main__":
    extract_frames_from_folder()