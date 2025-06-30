import cv2
import logging
from pypylon import pylon
from ultralytics import YOLO
from plc import Plc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VisionSystem:
    def __init__(self, model_path: str = '../data/models/best-v3.pt'):
        self.model = YOLO(model_path)
        self.colors = {
            'OK': (0, 255, 0),  # Verde
            'NOK': (0, 0, 255),  # Vermelho
            'PEDRA': (255, 0, 0),  # Azul
        }
        self.class_priority = {'PEDRA': 3, 'NOK': 2, 'OK': 1} #Priority map
        self.class_values = {'OK': 0, 'NOK': 1, 'PEDRA': 2} #plc values
        self.window_name = 'Vision System'
        self.resolution = (1280, 768)
        self.plc = Plc()
        self.camera = None
        self.converter = None

    def init_camera(self) -> bool:
        """Initializes the camera"""
        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.camera.Open()
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self.converter = pylon.ImageFormatConverter()
            self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.window_name, *self.resolution)
            return True
        except Exception as e:
            print(e)
            return False

    def process_frame(self) -> None:
        """Processes the frame with YOLO and write results to PLC"""
        if not self.plc.init_plc():
            return

        while self.camera.IsGrabbing():
            try:
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                if not grab_result.GrabSucceeded():
                    logger.warning('Failed to grab frame')
                    continue

                image = self.converter.Convert(grab_result)
                frame = image.GetArray()
                grab_result.Release()

                results = self.model(frame, conf=0.5)

                highest_priority_class = None
                highest_priority = 0

                for result in results:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    classes = result.boxes.cls.cpu().numpy()
                    scores = result.boxes.conf.cpu().numpy()

                    for box, cls, score in zip(boxes, classes, scores):
                        x1, y1, x2, y2 = map(int, box)
                        label = self.model.names[int(cls)]
                        color = self.colors.get(label, (0, 255, 0))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, f'{label}: {score:.2f}', (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                        # Track highest-priority class
                        priority = self.class_priority.get(label, 0)
                        if priority > highest_priority:
                            highest_priority = priority
                            highest_priority_class = label

                if highest_priority_class:
                    try:
                        plc_data = self.class_values[highest_priority_class]
                        self.plc.write_db(plc_data)
                        logger.info(f"Wrote class {highest_priority_class} (value {plc_data}) to PLC")
                    except Exception as e:
                        logger.error(f"Failed to write: {e}")

                cv2.imshow(self.window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            except Exception as e:
                logger.error(f"Failed to write: {e}")
                continue

    def cleanup(self) -> None:
        """Clean up camera, PLC, and OpenCV resources."""
        try:
            if self.camera and self.camera.IsGrabbing():
                self.camera.StopGrabbing()
            if self.camera:
                self.camera.Close()
            cv2.destroyAllWindows()
            logger.info("Resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Support context manager for automatic initialization."""
        self.init_camera()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support context manager for automatic cleanup."""
        self.cleanup()

def main():
    """Main function to run the vision system."""
    vision_system = VisionSystem()
    with vision_system:
        vision_system.process_frame()

if __name__ == "__main__":
    main()