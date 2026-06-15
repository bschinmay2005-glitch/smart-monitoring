import cv2
import os
import numpy as np
from PIL import Image

path = "dataset"

recognizer = cv2.face.LBPHFaceRecognizer_create()

def getImagesAndLabels(path):
    imagePaths = [os.path.join(path,f) for f in os.listdir(path)]
    faceSamples=[]
    ids=[]

    for imagePath in imagePaths:

        PIL_img = Image.open(imagePath).convert('L')
        img_numpy = np.array(PIL_img,'uint8')

        id = int(os.path.split(imagePath)[-1].split(".")[1])

        faceSamples.append(img_numpy)
        ids.append(id)

    return faceSamples,ids


print("Training faces...")

faces,ids = getImagesAndLabels(path)

recognizer.train(faces, np.array(ids))

recognizer.write('trainer.yml')

print("Training complete! trainer.yml created")