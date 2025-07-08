import os
import cv2
import logging
import asyncio
import time
from pypylon import pylon
from ultralytics import YOLO
from plc import Plc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VisionSystem:
    def __init__(self, model_path: str = '../data/models/best_float32_edgetpu.tflite'):
        self.model = YOLO(model_path)
        self.colors = {
            'OK': (0, 255, 0),  # Verde
            'NOK': (0, 0, 255),  # Vermelho
            'PEDRA': (255, 0, 0),  # Azul
        }
        self.class_priority = {'PEDRA': 3, 'NOK': 2, 'OK': 1}  # Priority map
        self.class_values = {'OK': 0, 'NOK': 1, 'PEDRA': 2}  # PLC values
        self.window_name = 'Vision System'
        self.resolution = (1280, 768)
        self.plc = Plc()
        self.camera = None
        self.converter = None
        self.last_screenshot_time = 0

    def init_camera(self) -> bool:
        """Initializes the camera"""
        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.camera.Open()
            logging.info("Câmera encontrada e aberta com sucesso.")

            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self.converter = pylon.ImageFormatConverter()
            self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar camera: {e}")
            logger.error("Nenhuma câmera Pylon encontrada. Verifique a conexão USB e as permissões do Docker.")
            return False

    async def process_frame(self) -> None:
        """Processes the frame with YOLO, displays all objects, and writes highest-priority class to PLC"""
        if not self.plc.init_plc():
            logger.error("Failed to initialize PLC")
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

                small_frame = cv2.resize(frame, (640, 480))
                results = self.model(small_frame, conf=0.5)

                highest_priority_class = None
                highest_priority = 0

                # Process all detections for display
                for result in results:
                    if not result.boxes:  # Skip if no detections
                        continue
                    boxes = result.boxes.xyxy
                    classes = result.boxes.cls
                    scores = result.boxes.conf

                    for box, cls, score in zip(boxes, classes, scores):
                        x1, y1, x2, y2 = map(int, box)
                        label = self.model.names[int(cls)]
                        color = self.colors.get(label, (0, 255, 0))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, f'{label}: {score:.2f}', (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                        # Track highest-priority class for PLC
                        priority = self.class_priority.get(label, 0)
                        if priority > highest_priority:
                            highest_priority = priority
                            highest_priority_class = label

                # Write the highest-priority class to PLC
                if highest_priority_class:
                    try:
                        plc_data = self.class_values[highest_priority_class]
                        self.plc.write_db(plc_data)
                        logger.info(f"Wrote class {highest_priority_class} (value {plc_data}) to PLC")
                    except Exception as e:
                        logger.error(f"Failed to write to PLC: {e}")
                #Tira print
                current_time = time.time()
                if highest_priority in [2, 3] and (current_time - self.last_screenshot_time) >= 1:
                    self.last_screenshot_time = current_time
                    asyncio.create_task(self.screenshot(frame.copy()))

                cv2.imshow(self.window_name, frame)
                cv2.moveWindow(self.window_name, 0, 0)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                continue

    @staticmethod
    async def screenshot(frame):
        """Take a screenshot and save it"""
        try:
            # Set a screenshot directory or create a new directory
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = os.path.join(screenshot_dir, f"capture_{timestamp}.png")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, cv2.imwrite, filename, frame)
            logger.info(f"Screenshot salvo: {filename}")
        except Exception as e:
            logger.error(f"Erro ao salvar screenshot: {e}")

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

async def run_vision_system():
    """Function to execute a vision system."""
    with VisionSystem() as vision_system:
        if vision_system.camera and vision_system.camera.IsOpen():
            await vision_system.process_frame()
        else:
            print("Saindo do programa pois a câmera não pôde ser inicializada.")

def main():
    """Main function to run the vision system."""
    try:
        asyncio.run(run_vision_system())
    except KeyboardInterrupt:
        print("Programa interrompido pelo usuário.")

if __name__ == "__main__":
    main()