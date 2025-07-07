from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from tensorflow.keras.preprocessing.image import img_to_array
import numpy as np
import tensorflow as tf
from PIL import Image
import io
from tensorflow.keras.models import load_model
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
   

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

IMG_SIZE = (160, 160)
CLASS_NAMES = ['Cardboard', 'Food','Glass','Metal','Miscellaneous','Paper','Plastic','Textile','Vegetation']

model = load_model('best_resnet101_model.keras')

def preprocessing(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize(IMG_SIZE)
    img_array = img_to_array(image)
    img_array = tf.cast(img_array, tf.float32)
    img_array = tf.expand_dims(img_array, axis=0)
    return img_array


@app.post('/predict')
async def predict(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = preprocessing(contents)
        
        y_hat = model.predict(image)
        predicted_class = np.argmax(y_hat[0])
        confidence = float(np.max(y_hat[0]))
        
        return JSONResponse({
            "filename": file.filename,
            "predicted_class": int(predicted_class),
            "class_name": CLASS_NAMES[predicted_class],
            "confidence": confidence
        })
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
